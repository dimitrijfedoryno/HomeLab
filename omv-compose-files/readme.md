# Serverové Služby s Docker Compose na OMV

Tento repozitář obsahuje konfigurační soubory (`.yaml`) pro Docker Compose, které spravují klíčové služby na mém serveru s OpenMediaVault (OMV). Cílem je snadná správa a reprodukovatelnost nastavení.

## 💾 Struktura a Konfigurace

Většina kontejnerů sdílí podobný základ pro adresářovou strukturu na disku, který je identifikován UUID: `/srv/dev-disk-by-uuid-1cfc3f1a-e64c-4b80-8151-d8f58a25e10f/`.

### 1. Nginx Webserver (`nginx-webserver.yaml`) 🌐

Jednoduchý Nginx webserver pro hostování statického obsahu.

| Konfigurace | Hodnota / Popis |
| :--- | :--- |
| **Image** | `nginx:latest` |
| **Název Kontejneru** | `Webserver` |
| **Restart Policy** | `always` |
| **Časové Pásmo (TZ)** | `Europe/Prague` |
| **Host Port** | `8080` (Dostupné na `http://[IP_OMV]:8080`) |
| **Data Volume** | `/srv/dev-disk-by-uuid-1cfc3f1a-e64c-4b80-8151-d8f58a25e10f/Surikata/Web` (Read-only) |

> **🚨 DŮLEŽITÉ:** Cesta pro `volumes` by měla být ověřena a případně změněna na cestu ke sdílené složce, která bude sloužit jako kořen webu.

***

### 2. Home Assistant (`home-assistant.yaml`) 🏠

Jádro chytré domácnosti. Konfigurace používá `network_mode: host` pro přímý přístup k síti serveru, což je běžné pro Home Assistant.

| Konfigurace | Hodnota / Popis |
| :--- | :--- |
| **Image** | `ghcr.io/home-assistant/home-assistant:stable` |
| **Název Kontejneru** | `homeassistant` |
| **Restart Policy** | `unless-stopped` |
| **Síťový Mód** | `host` |
| **Privileged** | `true` |
| **Config Volume** | `/srv/dev-disk-by-uuid-1cfc3f1a-e64c-4b80-8151-d8f58a25e10f/Docker_Compose_Configs/homeassistant-config` |
| **System Volumes** | `/etc/localtime`, `/var/run/dbus/system_bus_socket` (pro správný čas a D-Bus komunikaci) |

***

### 3. Jellyfin Media Server (`jellyfin.yaml`) 🎬

Streamovací server pro multimédia (filmy, seriály, hudba).

| Konfigurace | Hodnota / Popis |
| :--- | :--- |
| **Image** | `lscr.io/linuxserver/jellyfin:latest` |
| **Název Kontejneru** | `jellyfin` |
| **PUID/PGID** | `1000`/`1000` (Zkontrolujte uživatelská práva v OMV) |
| **Časové Pásmo (TZ)** | `Etc/UTC` |
| **Hlavní Port** | `8096:8096` |
| **Konfigurace Volume** | `/srv/dev-disk-by-uuid-1cfc3f1a-e64c-4b80-8151-d8f58a25e10f/Docker_Compose_Configs:/config` |
| **Mediální Cesty** | Namapovány konkrétní složky pro **Seriály**, **Filmy** a **Hudbu** |
| **Další Porty** | `8920` (volitelný HTTPS), `7359/udp`, `1900/udp` (volitelné pro objevování) |

***

### 4. Immich Photo Management (Immich složka - `composer.yaml` a `Immich.env`) 📸

Immich je řešení pro správu fotografií. Konfigurace je rozdělena na `composer.yaml` (služby) a `Immich.env` (proměnné prostředí).

#### `Immich.env` Proměnné

Konfigurační soubor s citlivými cestami a hesly.

| Proměnná | Popis / Původní Hodnota | Poznámka |
| :--- | :--- | :--- |
| **UPLOAD\_LOCATION** | Cesta pro nahrávané soubory | `/srv/dev-disk-by-uuid-1cfc3f1a-e64c-4b80-8151-d8f58a25e10f/Surikata/Multimedia/Fotky/Immich/library` |
| **DB\_DATA\_LOCATION** | Cesta pro databázi PostgreSQL | `/srv/dev-disk-by-uuid-1cfc3f1a-e64c-4b80-8151-d8f58a25e10f/Surikata/Multimedia/Fotky/Immich/postgres` |
| **IMMICH\_VERSION** | Verze Immich | [cite_start]`release` (Lze připnout na konkrétní verzi, např. `v1.71.0`) [cite: 3] |
| **DB\_PASSWORD** | Heslo pro databázi | [cite_start]`tvoje-bezpecne-heslo` (**Změňte na náhodné heslo!**) [cite: 4] |
| **DB\_USERNAME** | Uživatel databáze | `dimitrij` |
| **DB\_DATABASE\_NAME** | Název databáze | `immich` |

> [cite_start]**⚠️ POZOR:** Pro databázi (`DB_DATA_LOCATION`) nejsou podporovány síťové sdílené složky. [cite: 2]

#### `composer.yaml` Služby

Definuje 4 hlavní služby: `immich-server`, `immich-machine-learning`, `redis` a `database` (PostgreSQL).

* **immich-server:** Hlavní aplikační server. Port **2283** je vystaven.
* **immich-machine-learning:** Kontejner pro úlohy strojového učení (ML).
* **redis:** Používá `valkey/valkey:8-bookworm`. Slouží jako cache/broker.
* **database (PostgreSQL):** Používá `immich-app/postgres:14-vectorchord0.4.3-pgvectors0.2.0`. Databázové heslo a uživatel jsou načteny z `Immich.env`.

> [cite_start]Konfigurace Immich by měla být vždy aktualizována dle oficiálního návodu na Immich dokumentaci. [cite: 1]

***

## 🚀 Spuštění Služeb

V příslušném adresáři s `.yaml` souborem (nebo v případě Immich v adresáři s `composer.yaml` a `Immich.env`) použijte následující příkazy (spouštějte vždy jako uživatel s oprávněním pro Docker):

### Pro jednotlivé služby (Nginx, Home Assistant, Jellyfin):

```bash
docker compose -f <NAZEV_SOUBORU>.yaml up -d