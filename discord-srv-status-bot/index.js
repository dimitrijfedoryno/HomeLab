import { Client, GatewayIntentBits } from 'discord.js';
import { config } from 'dotenv';
import { readFile } from 'fs/promises';
import { NodeSSH } from 'node-ssh'; 
import os from 'os';
// Moduly pro spuštění systémových příkazů na lokálním OS
import { exec } from 'child_process';
import { promisify } from 'util';
const execPromisified = promisify(exec); 

// Načtení proměnných prostředí ze souboru .env
config();

// Perzistentní uložení ID zprávy
let statusMessageId = null; 

// Discord klient
const client = new Client({ intents: [GatewayIntentBits.Guilds] });

//----------------------------------------------------------------------
// POMOCNÉ FUNKCE
//----------------------------------------------------------------------

/**
 * Převede sekundy na lidsky čitelný formát.
 */
function formatUptime(seconds) {
    const totalSeconds = Math.floor(seconds);
    const days = Math.floor(totalSeconds / (3600 * 24));
    const hours = Math.floor((totalSeconds % (3600 * 24)) / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);

    return `${days.toString().padStart(2, '0')}d ${hours.toString().padStart(2, '0')}h ${minutes.toString().padStart(2, '0')}m`;
}

/**
 * Převede bajty na formát "XX TB, YY GB, ZZ MB" (Podpora TB, GB, MB).
 */
function formatDiskSpace(bytes) {
    if (typeof bytes !== 'number' || bytes < 0 || isNaN(bytes)) {
        return 'N/A';
    }

    const T = 1024 * 1024 * 1024 * 1024;
    const G = 1024 * 1024 * 1024;
    const M = 1024 * 1024;
    
    let remainingBytes = bytes;
    let parts = [];

    // Terabytes
    const tb = Math.floor(remainingBytes / T);
    if (tb > 0) {
        parts.push(`${tb} TB`);
        remainingBytes %= T;
    }

    // Gigabytes
    const gb = Math.floor(remainingBytes / G);
    // Zobrazí GB, pokud jsou > 0, nebo pokud už byl zobrazen TB
    if (gb > 0 || (parts.length > 0 && bytes >= G)) { 
        parts.push(`${gb} GB`);
        remainingBytes %= G;
    }
    
    // Megabytes
    const mb = Math.floor(remainingBytes / M);
    // Zobrazí MB, pokud jsou > 0, nebo pokud je to jediná jednotka
    if (mb > 0 || parts.length === 0) { 
        parts.push(`${mb} MB`);
    }

    return parts.length > 0 ? parts.join(', ') : '0 MB';
}

/**
 * Parsuje výstup příkazu df (mountpoint a volné bajty) a strukturu dat.
 * Vrací totalFreeBytes, systemDisk a mountedDisks.
 */
function parseDiskOutput(rawDiskOutput) {
    const lines = rawDiskOutput.trim().split('\n').filter(line => line.trim() !== '');
    let totalFreeBytes = 0;
    let systemDisk = null;
    let mountedDisks = [];

    for (const line of lines) {
        const parts = line.split(/\s+/);
        // Očekáváme přesně 2 části: mountpoint a volné bajty
        if (parts.length === 2) {
            const mountPoint = parts[0];
            const bytes = parseInt(parts[1].trim());

            if (!isNaN(bytes) && mountPoint) {
                totalFreeBytes += bytes;

                if (mountPoint === '/') {
                    systemDisk = { mountPoint: mountPoint, freeBytes: bytes };
                } else {
                    mountedDisks.push({ mountPoint: mountPoint, freeBytes: bytes });
                }
            }
        }
    }
    
    // Pokud '/' nebyl nalezen (některé systémy používají jiné mount pointy), 
    // a existuje alespoň jeden disk, vezmeme ho jako systémový disk.
    if (!systemDisk && (mountedDisks.length > 0)) {
        // Použijeme první detekovaný disk jako "systémový" pro zobrazení
        systemDisk = mountedDisks.shift(); 
    }

    return { totalFreeBytes, systemDisk, mountedDisks };
}


/**
 * Získá stav, uptime a volné místo na disku pro lokální server (Pi-Hole).
 */
async function getLocalServerStatus() {
    const uptime = os.uptime(); 
    let diskData = { status: '🟢 Online', uptime: formatUptime(uptime), totalFreeBytes: 0, systemDisk: null, mountedDisks: [] };

    // df -B1 --local | awk 'NR>1 {print $6, $4}' vrací mountpoint a volné bajty pro lokální filesystémy
    const command = 'df -B1 --local | awk \'NR>1 {print $6, $4}\'';
    
    try {
        const { stdout } = await execPromisified(command);
        diskData = { ...diskData, ...parseDiskOutput(stdout) };

    } catch (e) {
        console.error("Chyba při získávání volného místa na lokálním disku:", e.message);
    }

    return diskData;
}


/**
 * Získá stav, uptime a volné místo na disku pro vzdálený server přes SSH.
 */
async function getRemoteServerStatus(host, username, password) {
    const ssh = new NodeSSH();
    const result = {
        status: '🟢 Online', 
        uptime: 'N/A (SSH fail)',
        totalFreeBytes: 0, 
        systemDisk: null, 
        mountedDisks: [] 
    };

    try {
        await ssh.connect({
            host: host,
            username: username,
            password: password
        });

        // 1. Získání Uptime
        const { stdout: uptimeSecs } = await ssh.execCommand('cat /proc/uptime | awk \'{print $1}\'');
        const seconds = parseFloat(uptimeSecs.trim());
        
        // 2. Získání volného místa na disku (DETAILNÍ VÝPIS)
        // df -B1 --local | awk 'NR>1 {print $6, $4}'
        const { stdout: freeDiskOutput } = await ssh.execCommand('df -B1 --local | awk \'NR>1 {print $6, $4}\'');
        
        const parsedDiskData = parseDiskOutput(freeDiskOutput);

        result.status = '🟢 Online';
        result.uptime = formatUptime(seconds);
        result.totalFreeBytes = parsedDiskData.totalFreeBytes;
        result.systemDisk = parsedDiskData.systemDisk;
        result.mountedDisks = parsedDiskData.mountedDisks;
        
    } catch (error) {
        console.error(`Chyba SSH pro ${host}: ${error.message}`);
        // Při selhání SSH zůstane result ve výchozím stavu
    } finally {
        if (ssh.isConnected()) {
            ssh.dispose(); 
        }
    }

    return result;
}

//----------------------------------------------------------------------
// GENERÁTOR ZPRÁVY
//----------------------------------------------------------------------

/**
 * Zkonstruuje novou zprávu v požadovaném formátu.
 * @returns {Promise<string>} Nový obsah zprávy.
 */
async function generateNewStatusMessage() {
    let message = '📡 **Status zařízení**\n\n'; 
    
    // Formátování času YYYY-MM-DD HH:mm:ss
    const currentTime = new Date();
    const formattedTime = currentTime.getFullYear().toString() + '-' 
                        + (currentTime.getMonth() + 1).toString().padStart(2, '0') + '-' 
                        + currentTime.getDate().toString().padStart(2, '0') + ' ' 
                        + currentTime.getHours().toString().padStart(2, '0') + ':' 
                        + currentTime.getMinutes().toString().padStart(2, '0') + ':' 
                        + currentTime.getSeconds().toString().padStart(2, '0');

    // Čas obalený zpětnými apostrofy
    message += `Poslední update: \`${formattedTime}\`\n\n`; 
    
    // Načtení konfigurace serverů
    const serversConfig = JSON.parse(await readFile('./servers.json', 'utf-8'));

    for (const server of serversConfig) {
        let statusData;
        
        if (server.current === true) {
            statusData = await getLocalServerStatus(); 
        } else {
            const envPrefix = server.env_prefix;
            const host = process.env[`${envPrefix}_SSH_HOST`];
            const user = process.env[`${envPrefix}_SSH_USER`];
            const pass = process.env[`${envPrefix}_SSH_PASS`];
            
            if (!host || !user || !pass) {
                // Přidání defaultních hodnot pro chybu konfigurace
                statusData = { status: '🟡 Konf. chyba', uptime: 'N/A', totalFreeBytes: 0, systemDisk: null, mountedDisks: [] };
            } else {
                statusData = await getRemoteServerStatus(host, user, pass);
            }
        }
        
        // Formátování: Název serveru tučně, Uptime
        message += `**Server ${server.name}**\n`;
        message += `Status: ${statusData.status}\n`;
        message += `Uptime: \`${statusData.uptime}\`\n`; 
        
        // Sekce Volné místo
        message += `Volné místo celkem: ${formatDiskSpace(statusData.totalFreeBytes)}\n`;

        // Detailní výpis disků
        if (statusData.systemDisk) {
            // 1. Systémový disk
            message += `- Systémový disk \`${statusData.systemDisk.mountPoint}\`: ${formatDiskSpace(statusData.systemDisk.freeBytes)}\n`;
        } else {
             message += `- Systémový disk: N/A\n`;
        }

        // 2. Připojené disky
        if (statusData.mountedDisks.length > 0) {
            statusData.mountedDisks.forEach(disk => {
                message += `- Připojený disk \`${disk.mountPoint}\`: ${formatDiskSpace(disk.freeBytes)}\n`;
            });
        }
        
        message += '\n'; // Mezera mezi servery
    }
    
    return message.trim(); 
}

//----------------------------------------------------------------------
// HLAVNÍ LOGIKA BOTA
//----------------------------------------------------------------------

/**
 * Hlavní funkce pro aktualizaci status zprávy.
 */
async function updateStatusMessage() {
    try {
        const channelId = process.env.DISCORD_CHANNEL_ID;
        const channel = await client.channels.fetch(channelId);

        if (!channel) {
            console.error('Discord kanál nenalezen! Zkontrolujte DISCORD_CHANNEL_ID v .env.');
            return;
        }

        const newMessageContent = await generateNewStatusMessage();

        if (statusMessageId) {
            // 1. Zpráva je v paměti: pokus o editaci.
            const message = await channel.messages.fetch(statusMessageId).catch(() => null);
            
            if (message) {
                await message.edit(newMessageContent);
                console.log(`[${new Date().toLocaleTimeString()}] Zpráva ID ${statusMessageId} aktualizována.`);
            } else {
                // Zpráva byla smazána/nenalezena, vytvoříme novou.
                const sentMessage = await channel.send(newMessageContent);
                statusMessageId = sentMessage.id;
                console.log(`[${new Date().toLocaleTimeString()}] Původní zpráva smazána, vytvořena nová s ID: ${statusMessageId}`);
            }

        } else {
            // 2. První spuštění: Pokus o nalezení existující status zprávy.
            const messages = await channel.messages.fetch({ limit: 100 });
            
            // Hledáme poslední zprávu, která obsahuje úvodní řetězec a byla poslána botem.
            const latestStatusMessage = messages.find(m => 
                m.author.id === client.user.id && 
                m.content.includes('📡 **Status zařízení**')
            );

            if (latestStatusMessage) {
                // Nalezena existující zpráva, uložíme její ID a aktualizujeme ji.
                statusMessageId = latestStatusMessage.id;
                await latestStatusMessage.edit(newMessageContent);
                console.log(`[${new Date().toLocaleTimeString()}] Nalezena a aktualizována existující status zpráva ID: ${statusMessageId}`);
            } else {
                // Zpráva neexistuje, vytvoříme novou.
                const sentMessage = await channel.send(newMessageContent);
                statusMessageId = sentMessage.id;
                console.log(`[${new Date().toLocaleTimeString()}] Vytvořena nová status zpráva s ID: ${statusMessageId}`);
            }
        }

    } catch (error) {
        console.error('Kritická chyba při aktualizaci status zprávy:', error);
    }
}

//----------------------------------------------------------------------
// STARTOVACÍ SEKCE
//----------------------------------------------------------------------

client.on('ready', () => {
    console.log(`\n---------------------------------`);
    console.log(`Discord bot přihlášen jako ${client.user.tag}!`);
    console.log(`---------------------------------`);
    
    updateStatusMessage(); 

    // Pravidelná aktualizace každou 1 minutu (60000 ms)
    setInterval(updateStatusMessage, 60000); 
});

client.login(process.env.DISCORD_TOKEN).catch(err => {
    console.error('Chyba při přihlašování bota! Zkontrolujte DISCORD_TOKEN v .env.');
    console.error(err);
});