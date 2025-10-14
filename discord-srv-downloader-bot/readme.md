# 🎧 Discord Download Bot (YouTube, Spotify, TikTok, Instagram) 🎬

Tento Discord bot umožňuje stahovat obsah (video nebo audio) z různých platforem (YouTube, TikTok, Instagram) a také automaticky sleduje a stahuje nové skladby ze **Spotify Playlistů** pomocí vyhledávání na YouTube (s konverzí na MP3).

Je navržen pro běh na serveru (např. v Dockeru nebo na OMV) a využívá **yt-dlp** a **FFMPEG**.

## 🚀 Funkce

* **Podpora Více Platforem:** Stahování z YouTube (včetně celých playlistů), TikTok, Instagram.
* **Spotify Integrace:** Stahování jednotlivých skladeb a sledování celých playlistů (vyhledává a stahuje skladby z YouTube, ukládá jako MP3).
* **Archivace:** Přeskakuje již stažené soubory (pomocí `downloaded_songs_archive.txt`).
* **Automatická Kontrola:** Pravidelně kontroluje sledované Spotify playlisty a stahuje nové skladby.
* **Asynchronní Stahování:** Běží bez blokování pro více uživatelů.
* **Správa:** Příkazy pro zastavení stahování, přepínání tichého módu a restart/vypnutí.
* **Strukturované Ukládání:** Soubory jsou ukládány do oddělených složek pro Audio a Video a dále organizovány podle jména uživatele a názvu playlistu.

## 🛠️ Předpoklady

1.  **Python 3.8+**
2.  **FFMPEG:** Musí být nainstalován v systému (`sudo apt install ffmpeg`), protože je nezbytný pro konverzi na MP3 a spojování videa/audia.
3.  **Discord Bot Token:** Musíte mít vytvořenou aplikaci na Discord Developers a získaný token.
4.  **Spotify API Keys (Volitelné, ale doporučené):** Pro plnou funkčnost Spotify musíte mít `SPOTIFY_CLIENT_ID` a `SPOTIFY_CLIENT_SECRET`.

## ⚙️ Instalace a Konfigurace

### 1. Klonování Repozitáře

```bash
git clone <url_vaseho_repozitare>
cd discord-download-bot
````

### 2\. Konfigurace `.env` souboru

Vytvořte soubor s názvem `.env` ve stejném adresáři jako `bot.py` a vyplňte následující proměnné:

```env
# --- Povinné ---
DISCORD_BOT_TOKEN="VÁŠ_DISCORD_BOT_TOKEN"
DISCORD_OWNER_ID="VAŠE_DISCORD_USER_ID" # ID vlastníka pro administraci a DM upozornění

# --- Volitelné (doporučené pro funkčnost Spotify) ---
SPOTIFY_CLIENT_ID="VÁŠ_SPOTIFY_CLIENT_ID"
SPOTIFY_CLIENT_SECRET="VÁŠ_SPOTIFY_CLIENT_SECRET"

# --- Volitelné nastavení cest ---
# Základní složka pro stahování. Pokud není nastavena, použije se ./Downloads
# OMV_BASE_DOWNLOAD_DIR="/cesta/k/vase/sdilene/sloze"
# AUDIO_SUB_DIR_NAME="Zvuk"  # Název podsložky pro audio (např. Downloads/Zvuk)
# VIDEO_SUB_DIR_NAME="Video" # Název podsložky pro video (např. Downloads/Video)

# --- Volitelné omezení kanálu ---
# DISCORD_CHANNEL_ID="ID_KANÁLU_PRO_POVOLENÉ_PŘÍKAZY" # Pouze v tomto kanálu budou povoleny /stahni
```

### 3\. Spuštění

Skript `bot.py` automaticky zkontroluje a nainstaluje chybějící Python závislosti (yt-dlp, discord.py atd.) do lokální složky `Packages`.

```bash
python3 bot.py
```

## 📂 Struktura Stahovaných Souborů

Bot automaticky vytváří složky a organizuje stažený obsah.

  * **Základní Adresář:** `OMV_BASE_DOWNLOAD_DIR` (výchozí: `./Downloads`)
  * **Audio:** `[Základní Adresář]/Zvuk/[Jméno Uživatele]/`
      * *Spotify/YT Playlisty:* `[Základní Adresář]/Zvuk/[Jméno Uživatele]/[Název Playlistu]/`
  * **Video:** `[Základní Adresář]/Video/[Jméno Uživatele]/`
      * *YT Playlisty:* `[Základní Adresář]/Video/[Jméno Uživatele]/[Název Playlistu]/`

## 💻 Discord Příkazy

Bot používá Discord **Slash Commands**.

| Příkaz | Popis | Oprávnění |
| :--- | :--- | :--- |
| `/stahni <url>` | Zahájí stahování obsahu z dané URL. Pro jednotlivé položky se zobrazí tlačítka pro volbu **Video** nebo **Zvuk (MP3)**. Playlisty ze Spotify se stáhnou automaticky jako MP3. | Vlastník nebo povolený kanál |
| `/dlstop` | Zastaví probíhající stahování, které spustil daný uživatel. | Všichni |
| `/check` | Spustí okamžitou kontrolu nových skladeb ve všech sledovaných Spotify playlistech. | Vlastník |
| `/silent` | Přepne **Silent mód**. Bot neposílá potvrzovací zprávy o spuštění/dokončení stahování (pouze chyby). | Vlastník |
| `/sync` | Synchronizuje globální slash commandy. Použijte po změnách v kódu. | Vlastník |
| `/stop` | Ukončí a **restartuje** bota (používá `os.execv`). | Vlastník |
| `/shutdown` | Vypne bota bez restartu. | Vlastník |

## ❗ Důležité Upozornění

  * **FFMPEG:** Pokud FFMPEG není správně nainstalován v systémové PATH, stahování zvuku a spojování videa/zvuku (což je standardní operace yt-dlp) nebude fungovat. Bot o tom odešle DM zprávu vlastníkovi.
  * **Spotify Stahování:** Bot nevolá přímo Spotify API pro stahování audia, ale získává název skladby a interpreta, a poté vyhledává na YouTube (`ytsearch1:`). Je to nutné pro získání stahovatelného souboru.

<!-- end list -->