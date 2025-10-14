```
# 📡 Home Center Status Bot

Discord bot vytvořený pro **pravidelné monitorování stavu a volného místa** na vašich lokálních a vzdálených Linux serverech (např. Pi-Hole, OpenMediaVault, NAS atd.) a pro reportování těchto dat do Discord kanálu.

Bot je psán v **Node.js** s využitím Discord.js a pro získání detailních dat o discích používá nativní systémové příkazy (`df`) a SSH pro vzdálené servery, což zajišťuje maximální stabilitu na Linuxových systémech.

---

## ✨ Klíčové Funkce a Formát Zprávy

Bot vytvoří a pravidelně aktualizuje jednu zprávu s přehledem všech monitorovaných serverů ve standardizovaném formátu:

* **Monitorování Uptime** a **Status** (Online/Chyba).
* **Volné Místo Celkem:** Součet volného místa ze všech připojených disků.
* **Detailní Výpis Disků:** Volné místo na **systémovém disku** a **každém připojeném disku** (např. `/srv/dev-disk-by-uuid-...`) zvlášť.
* **Škálovatelné Jednotky:** Volné místo je formátováno v **TB**, **GB** a **MB**.

**Příklad výstupu v Discordu:**

```

📡 **Status zařízení**

Poslední update: `2025-10-14 14:23:00`

**Server OMV**
Status: 🟢 Online
Uptime: `08d 03h 41m`
Volné místo celkem: 1 TB, 750 GB, 20 MB

  - Systémový disk `/`: 50 GB, 100 MB
  - Připojený disk `/srv/disk-data`: 1 TB, 700 GB, 0 MB

**Server Pi-Hole**
Status: 🟢 Online
Uptime: `01d 12h 05m`
Volné místo celkem: 10 GB, 500 MB

  - Systémový disk `/`: 10 GB, 500 MB

<!-- end list -->

````

---

## 🛠️ Instalace a Spuštění

Následujte tyto kroky pro zprovoznění bota na vašem serveru (doporučuje se Node.js v18+).

### 1. Klonování a Moduly

```bash
# Přesuňte se do adresáře, kde chcete bota hostovat (např. /homelab/status-dc-bot)
cd status-dc-bot

# Instalace závislostí
npm install
````

### 2\. Konfigurace Serverů (`servers.json`)

Váš bot se řídí souborem `servers.json`, který definuje, jaké servery má sledovat.

**Příklad `servers.json`:**

```json
[
  {
    "name": "Pi-Hole",
    "current": true,
    "env_prefix": "PIHOLE" 
  },
  {
    "name": "OMV",
    "current": false,
    "env_prefix": "OMV" 
  }
]
```

  * `"current": true`: Znamená, že se jedná o **lokální server** (na kterém bot běží). Data o disku a uptime získá přímo ze systému bez SSH.
  * `"current": false`: Znamená, že jde o **vzdálený server**. Data získá přes SSH.
  * `"env_prefix"`: Používá se pro načtení SSH přihlašovacích údajů ze souboru `.env`.

### 3\. Konfigurace Proměnných Prostředí (`.env`)

Vytvořte v kořenové složce bota soubor s názvem **`.env`** a vyplňte v něm potřebné údaje. **Tento soubor NIKDY necommitujte do Gitu\!**

```dotenv
# ------------------------------------------------------------------
# ZÁKLADNÍ KONFIGURACE DISCORD
# ------------------------------------------------------------------
# Token vašeho Discord Bota (z Discord Developer Portal)
DISCORD_TOKEN="VÁŠ_DISCORD_BOT_TOKEN"
# ID textového kanálu, kam se bude zpráva posílat
DISCORD_CHANNEL_ID="ID_VAŠEHO_KANÁLU"

# ------------------------------------------------------------------
# KONFIGURACE PRO VZDÁLENÉ SERVERY (OMV)
# ------------------------------------------------------------------
# SSH host, uživatel a heslo pro server definovaný s prefixem OMV
OMV_SSH_HOST="192.168.1.10"
OMV_SSH_USER="ssh_user"
OMV_SSH_PASS="super_tajne_heslo"
```

### 4\. Spuštění Bota

Bota můžete spustit přímo nebo, doporučeno, cez `pm2` pro zajištění, že poběží na pozadí a automaticky se restartuje po chybě/pádu.

#### Standardní spuštění:

```bash
node index.js
```

#### Doporučené spuštění (s PM2):

```bash
# Instalace pm2, pokud jej nemáte
npm install -g pm2

# Spuštění bota pod jménem 'dc-status'
pm2 start index.js --name dc-status

# Uložení konfigurace pm2 pro automatický start po restartu systému
pm2 save
```

-----

## 📄 Licencování

Tento projekt je šířen pod licencí **MIT**.

```