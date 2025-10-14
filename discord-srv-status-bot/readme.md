# 📡 Home Center Status Bot

[![Node.js](https://img.shields.io/badge/Node.js-v18+-339933?logo=nodedotjs&logoColor=white)](https://nodejs.org/)
[![Discord.js](https://img.shields.io/badge/Discord.js-Latest-5865F2?logo=discord&logoColor=white)](https://discord.js.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Discord bot** vytvořený pro **pravidelné monitorování stavu a volného místa** na vašich lokálních a vzdálených Linux serverech (např. Pi-Hole, OpenMediaVault, NAS atd.) a pro reportování těchto dat do Discord kanálu.

Bot je napsán v **Node.js** a využívá knihovnu **Discord.js**. Pro získání detailních dat o discích používá nativní systémové příkazy (`df`) a **SSH** pro vzdálené servery, což zajišťuje **maximální stabilitu** na Linuxových systémech.

---

## ✨ Klíčové Funkce

Bot pravidelně vytváří a aktualizuje **jedinou zprávu** (tzv. "message update") s přehledem všech monitorovaných serverů ve standardizovaném a čitelném formátu:

* **Monitorování Uptime** a **Status** (🟢 Online / 🔴 Chyba).
* **Volné Místo Celkem:** Součet volného místa ze všech připojených disků daného serveru.
* **Detailní Výpis Disků:** Volné místo na **systémovém disku** (`/`) a **každém připojeném disku** (např. `/srv/disk-data`).
* **Škálovatelné Jednotky:** Volné místo je formátováno v přehledných jednotkách (**TB**, **GB**, **MB**).

### Příklad Výstupu v Discordu

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

````

---

## 🛠️ Instalace a Spuštění

Následujte tyto kroky pro zprovoznění bota na vašem serveru (doporučuje se **Node.js v18+**).

### 1. Klonování Repozitáře a Instalace Modulů

Přejděte do adresáře, kde chcete bota hostovat (např. `/homelab/status-dc-bot`), a nainstalujte závislosti:

```bash
# Příklad: Přesun do cílového adresáře
# cd /homelab/status-dc-bot

# Instalace závislostí
npm install
```

### 2. Konfigurace Serverů (`servers.json`)

Vytvořte a upravte soubor **`servers.json`**, který definuje, jaké lokální a vzdálené servery má bot sledovat.

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

| Klíč | Popis |
| :--- | :--- |
| `"name"` | Přátelské jméno serveru pro Discord výstup. |
| `"current"` | **`true`** = **Lokální server** (bot získá data přímo ze systému, na kterém běží). **`false`** = **Vzdálený server** (data získá přes SSH). |
| `"env_prefix"`| Prefix pro načítání SSH přihlašovacích údajů ze souboru `.env`. |

### 3. Konfigurace Proměnných Prostředí (`.env`)

Vytvořte v kořenové složce bota soubor s názvem **`.env`** a vyplňte v něm potřebné údaje. **Tento soubor NIKDY necommitujte do Gitu!**

```dotenv
# ------------------------------------------------------------------
# ZÁKLADNÍ KONFIGURACE DISCORD
# ------------------------------------------------------------------
# Token vašeho Discord Bota (z Discord Developer Portal)
DISCORD_TOKEN="VÁŠ_DISCORD_BOT_TOKEN"
# ID textového kanálu, kam se bude zpráva posílat
DISCORD_CHANNEL_ID="ID_VAŠEHO_KANÁLU"

# ------------------------------------------------------------------
# KONFIGURACE PRO VZDÁLENÉ SERVERY (Prefixy OMV, PIHOLE, atd.)
# ------------------------------------------------------------------
# SSH host, uživatel a heslo pro server definovaný s prefixem OMV
OMV_SSH_HOST="192.168.1.10"
OMV_SSH_USER="ssh_user"
OMV_SSH_PASS="super_tajne_heslo"

# Příklad pro další server (pokud by měl PIHOLE prefix "PIHOLE" a byl vzdálený)
# PIHOLE_SSH_HOST="192.168.1.5"
# PIHOLE_SSH_USER="pi"
# PIHOLE_SSH_PASS="moje_pi_heslo"
```

### 4. Spuštění Bota

#### Standardní Spuštění

Pro rychlé spuštění v popředí:

```bash
node index.js
```

#### Doporučené Spuštění (s PM2)

Pro zajištění, že bot poběží na pozadí, bude odolný proti pádům a automaticky se restartuje po restartu systému, doporučujeme použít správce procesů **PM2**:

```bash
# 1. Instalace pm2 (pokud jej nemáte)
npm install -g pm2

# 2. Spuštění bota pod jménem 'dc-status'
pm2 start index.js --name dc-status

# 3. Uložení konfigurace pm2 pro automatický start po restartu systému
pm2 save
```

---

## 📄 Licencování
Tento projekt je šířen pod licencí **MIT**.