#!/usr/bin/env python3
"""
Discord bot pro stahování z YouTube, TikTok, Instagram, Spotify.
"""
import os
import sys
import re
import time
import base64
import requests
import subprocess
from pathlib import Path
import logging
from datetime import datetime
import asyncio
import json
import yt_dlp
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

# --- Pomocná funkce pro zajištění složky ---
def ensure_folder(folder: str):
    """Zajistí, že složka existuje."""
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)

# --- Nastavení cesty pro lokální balíčky ---
PACKAGES_DIR = os.path.join(os.path.dirname(__file__), "Packages")
if PACKAGES_DIR not in sys.path:
    sys.path.insert(0, PACKAGES_DIR)

# --- Nastavení logování ---
LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Logs")
ensure_folder(LOGS_DIR)

# Archivace předchozího logu
LATEST_LOG_PATH = os.path.join(LOGS_DIR, "latest.log")
if os.path.exists(LATEST_LOG_PATH):
    timestamp = datetime.fromtimestamp(os.path.getmtime(LATEST_LOG_PATH)).strftime('%H-%M-%S-%d-%m-%Y')
    archived_log_path = os.path.join(LOGS_DIR, f"{timestamp}.log")
    os.rename(LATEST_LOG_PATH, archived_log_path)

logging.basicConfig(
    filename=LATEST_LOG_PATH,
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(message)s'
)

# --- Instalace závislostí ---
REQUIRED_PACKAGES = ["yt-dlp", "requests", "python-dotenv", "discord.py"]

def install_dependencies():
    """Instaluje potřebné balíčky do složky 'Packages'."""
    logging.info("Kontroluji a instaluji potřebné závislosti...")
    for package in REQUIRED_PACKAGES:
        try:
            if package == "discord.py":
                __import__("discord")
            elif package == "python-dotenv":
                __import__("dotenv")
            else:
                __import__(package.replace("-", "_"))
            logging.info(f"✅ Balíček '{package}' je již nainstalován.")
        except ImportError:
            logging.error(f"❌ Chyba: Balíček '{package}' nebyl nalezen. Instaluji...")
            pip_command = [sys.executable, "-m", "pip", "install", "--target", PACKAGES_DIR, package]
            try:
                subprocess.check_call(pip_command)
                logging.info(f"✅ Balíček '{package}' byl úspěšně nainstalován.")
            except subprocess.CalledProcessError as e:
                logging.critical(f"❌ Kritická chyba při instalaci balíčku '{package}': {e}")
                sys.exit(1)

install_dependencies()

# načtení .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# -------------------------------------------
# Konfigurace bota a stahování
# -------------------------------------------

SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
DISCORD_OWNER_ID = os.environ.get("DISCORD_OWNER_ID")
DISCORD_CHANNEL_ID = os.environ.get("DISCORD_CHANNEL_ID")

# CESTY PRO STAHUÁNÍ
OMV_DEFAULT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Downloads")
BASE_DOWNLOAD_DIR = os.environ.get("OMV_BASE_DOWNLOAD_DIR", OMV_DEFAULT_DIR)
AUDIO_DIR_NAME = os.environ.get("AUDIO_SUB_DIR_NAME", "Zvuk")
VIDEO_DIR_NAME = os.environ.get("VIDEO_SUB_DIR_NAME", "Video")

# Fiktivní URL pro testování, Spotify token se získává z API
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"

# Globální proměnná pro stav "silent" módu
SILENT_MODE = False

# Globální proměnná pro sledování stahování yt-dlp
ACTIVE_DOWNLOAD_TASKS = {}

# Cesta k souboru pro sledování playlistů a archiv stahování
PLAYLIST_DATA_FILE = "downloaded_playlists.json"
DOWNLOAD_ARCHIVE_FILE = "downloaded_songs_archive.txt"

# -------------------------------------------
# Správa dat
# -------------------------------------------
def load_playlist_data():
    if os.path.exists(PLAYLIST_DATA_FILE):
        try:
            with open(PLAYLIST_DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logging.error("❌ Chyba při čtení souboru downloaded_playlists.json. Soubor je poškozen.")
            return {}
    return {}

def save_playlist_data(data):
    with open(PLAYLIST_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
        
# -------------------------------------------
# Pomocné a asynchronní funkce
# -------------------------------------------

async def check_for_new_songs_async(manual_run: bool = False):
    """
    Pravidelně kontroluje sledované playlisty a stahuje nové skladby.
    Spoléhá na DOWNLOAD_ARCHIVE_FILE pro přeskočení již stažených položek.
    """
    if not manual_run:
        await bot.wait_until_ready()
    
    logging.info("⏳ Zahajuji kontrolu nových skladeb v sledovaných playlistech.")
    
    total_songs_checked = 0

    try:
        playlists_to_check = load_playlist_data()
        if not playlists_to_check:
            logging.info("✅ Nejsou žádné playlisty ke kontrole.")
            if not manual_run:
                await asyncio.sleep(3600 * 6)
            return

        for playlist_id, data in playlists_to_check.items():
            playlist_url = data.get("url")
            playlist_folder_rel = data.get("folder") 
            
            if not playlist_url or not playlist_folder_rel:
                continue

            logging.info(f"🔍 Kontroluji playlist: {playlist_url}")
            
            # Tato funkce je pouze pro Spotify, takže cílová složka je pevně daná
            out_dir = os.path.join(BASE_DOWNLOAD_DIR, AUDIO_DIR_NAME, playlist_folder_rel)
            ensure_folder(out_dir)
            
            opts = {
                "format": "bestaudio",
                "outtmpl": os.path.join(out_dir, "%(title)s.%(ext)s"),
                "download_archive": DOWNLOAD_ARCHIVE_FILE, 
                "ignoreerrors": True, # PŘIDÁNO: Ignoruje chyby v playlistu
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }]
            }
            
            try:
                # Blokující volání v executoru
                token = await asyncio.to_thread(get_spotify_token, SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)
                tracks = await asyncio.to_thread(get_spotify_playlist_tracks, playlist_url, token)
                
                download_urls = []
                for track in tracks:
                    query = f"ytsearch1:{track['title']} {track['artist']}".strip()
                    download_urls.append(query)
                        
                if download_urls:
                    await asyncio.to_thread(yt_dlp.YoutubeDL(opts).download, download_urls)
                    
                    logging.info(f"✅ Úspěšně zkontrolováno {len(download_urls)} skladeb z playlistu: {playlist_url}")
                    total_songs_checked += len(download_urls) 
                else:
                    logging.info(f"✅ Žádné skladby k nalezení v playlistu: {playlist_url}")

            except Exception as e:
                logging.error(f"❌ Chyba při automatické kontrole playlistu '{playlist_url}': {e}")
                
        if total_songs_checked > 0:
            await send_dm_to_owner(f"✅ Automatická kontrola dokončena. Zkontrolováno {total_songs_checked} skladeb v playlistech (již stažené byly přeskočeny).")
        else:
            logging.info("✅ Kontrola dokončena. Nebyly nalezeny žádné skladby ke kontrole.")

    except Exception as e:
        logging.error(f"❌ Kritická chyba při automatické kontrole playlistů: {e}")
        await send_dm_to_owner(f"❌ Kritická chyba při automatické kontrole playlistů.", str(e))
    
    if not manual_run:
        await asyncio.sleep(3600 * 6)

def is_owner_or_designated_channel(interaction: discord.Interaction):
    """Kontroluje, zda příkaz přichází od vlastníka nebo z povoleného kanálu."""
    if DISCORD_OWNER_ID and interaction.user.id == int(DISCORD_OWNER_ID):
        return True
    
    if DISCORD_CHANNEL_ID and str(interaction.channel_id) == DISCORD_CHANNEL_ID:
        return True
    
    # Příkazy pro správu (sync, stop, shutdown, silent) mohou používat jen vlastníci
    if interaction.command.name in ['sync', 'stop', 'shutdown', 'silent']:
        return DISCORD_OWNER_ID and interaction.user.id == int(DISCORD_OWNER_ID)

    return False

async def send_dm_to_owner(message: str, error_details: str = None, log_file: str = None):
    """Odešle soukromou zprávu vlastníkovi bota."""
    if not DISCORD_OWNER_ID:
        logging.warning("Nelze odeslat soukromou zprávu, DISCORD_OWNER_ID není nastaven.")
        return

    try:
        user = await bot.fetch_user(int(DISCORD_OWNER_ID))
        if user:
            dm_message = f"**Upozornění bota:** {message}"
            if error_details:
                dm_message += f"\n\n**Chyba:**\n```\n{error_details}\n```"
            if log_file:
                dm_message += f"\nPodrobnosti najdete v logu: `{log_file}`"
            await user.send(dm_message)
    except discord.Forbidden:
        logging.error("Nemám oprávnění posílat soukromé zprávy uživateli s tímto ID.")
    except discord.HTTPException as e:
        logging.error(f"Chyba při odesílání soukromé zprávy: {e}")
    except ValueError:
        logging.error("DISCORD_OWNER_ID není platné číslo.")

def sanitize_filename(filename: str):
    """Odstraní nepovolené znaky z názvu složky."""
    return re.sub(r'[\\/*?:"<>|]', "", filename)

def detect_platform(url: str):
    if re.search(r"tiktok\.com", url, re.I):
        return "tiktok"
    if re.search(r"instagram\.com", url, re.I):
        return "instagram"
    if re.search(r"open\.spotify\.com/playlist|spotify:playlist|spotify\.com/playlist", url, re.I):
        return "spotify_playlist"
    if re.search(r"youtube\.com/playlist\?list=|youtube\.com/watch\?v=.+&list=", url, re.I):
        return "youtube_playlist"
    if re.search(r"youtube\.com|youtu\.be", url, re.I):
        return "youtube"
    if re.search(r"open\.spotify\.com/track|spotify:track|spotify\.com/track", url, re.I):
        return "spotify_track"
    if re.search(r"googleusercontent\.com/spotify\.com/\d+", url, re.I):
        return "spotify_test_url"
    return None

def format_speed(speed_bytes):
    """Formátuje rychlost v bajtech do čitelného formátu (KiB/s, MiB/s)."""
    if speed_bytes is None:
        return "N/A"
    if speed_bytes < 1024:
        return f"{speed_bytes} B/s"
    elif speed_bytes < 1024**2:
        return f"{speed_bytes/1024:.2f} KiB/s"
    elif speed_bytes < 1024**3:
        return f"{speed_bytes/1024**2:.2f} MiB/s"
    else:
        return f"{speed_bytes/1024**3:.2f} GiB/s"

async def download_with_ytdlp(urls, out_dir: str, ytdlp_opts: dict, status_message: discord.Message, item_name: str = "neznámá položka"):
    """
    Stahuje obsah pomocí yt-dlp a odesílá průběžné aktualizace na Discord.
    """
    download_state = {
        "last_update": time.time(),
        "total_size": 0,
        "filename": ""
    }

    def progress_hook(d):
        if d['status'] == 'downloading':
            current_time = time.time()
            # Aktualizace každé 2 sekundy
            if (current_time - download_state["last_update"]) > 2:
                download_state["last_update"] = current_time

                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                downloaded_bytes = d.get('downloaded_bytes', 0)
                
                percent = round((downloaded_bytes / total_bytes) * 100, 1) if total_bytes > 0 else 0
                speed = d.get('speed')
                filename = os.path.basename(d.get('filename', 'Neznámý soubor'))
                
                download_state["filename"] = filename
                download_state["speed"] = format_speed(speed)
                download_state["progress"] = f"{percent:.1f}%"
                
                # Zabráníme prázdnému názvu souboru
                if download_state['filename'] == 'Neznámý soubor' and item_name != 'neznámá položka':
                    display_name = item_name
                else:
                    display_name = download_state['filename']
                
                try:
                    # Tato část běží v jiném vlákně, proto je nutné run_coroutine_threadsafe
                    asyncio.run_coroutine_threadsafe(
                        status_message.edit(content=f"⏳ Stahuju `{display_name}`...\n**Progres:** {download_state['progress']} | **Rychlost:** {download_state['speed']}"),
                        bot.loop
                    ).result()
                except Exception as e:
                    # Varování, ale nezastavujeme stahování
                    logging.warning(f"Chyba při aktualizaci status zprávy: {e}")

        elif d['status'] == 'finished':
            pass

    opts = {
        "outtmpl": os.path.join(out_dir, "%(title)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [progress_hook],
        "ignoreerrors": True, # PŘIDÁNO: Ignoruje chyby jednotlivých videí (řeší DownloadError)
    }
    opts.update(ytdlp_opts or {})

    try:
        # Spuštění blokující funkce v odděleném vlákně
        await asyncio.to_thread(yt_dlp.YoutubeDL(opts).download, [urls] if isinstance(urls, str) else urls)
    except Exception as e:
        if "ffmpeg" in str(e).lower():
            logging.error(f"❌ Chyba yt-dlp: Pravděpodobně chybí FFMPEG. Nainstalujte přes 'sudo apt install ffmpeg'. Detaily: {e}")
            await status_message.edit(content=f"❌ **Chyba stahování:** Pravděpodobně chybí `ffmpeg`. Nainstalujte jej do systému. Detaily: `{str(e).splitlines()[-1]}`")
        else:
            raise e
            
def get_spotify_token(client_id: str, client_secret: str) -> str:
    # Zjednodušená funkce, která ignoruje fiktivní URL
    return "mock_token_12345"

def extract_track_id(track_url: str) -> str:
    m = re.search(r"track[/:]([A-Za-z0-9]+)", track_url)
    if m: return m.group(1)
    m2 = re.search(r"track/([A-Za-z0-9]+)", track_url)
    if m2: return m2.group(1)
    raise ValueError("Nelze extrahovat track ID ze zadané URL")

def get_spotify_track_info(track_url: str, token: str):
    # Fiktivní implementace pro testování, protože nevíme, jak se autentifikuje skutečné Spotify API
    return {"title": "Testovací Skladba", "artist": "Testovací Interpret", "thumbnail_url": "http://example.com/thumb.jpg", "album": "Testovací Album"}

def extract_playlist_id(playlist_url: str) -> str:
    """Vylepšená extrakce playlist ID s lepším handlováním různých URL formátů."""
    if "googleusercontent.com" in playlist_url:
        match = re.search(r"/(\d+)$", playlist_url.split("?")[0])
        return match.group(1) if match else None
    
    clean_url = playlist_url.split("?")[0].split("#")[0]
    
    patterns = [
        r"playlist[/:]([A-Za-z0-9]+)",
        r"playlist/([A-Za-z0-9]+)",
        r"/playlist/([A-Za-z0-9]+)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, clean_url)
        if match:
            return match.group(1)
    
    raise ValueError(f"Nelze extrahovat playlist ID ze zadané URL: {playlist_url}")

def get_spotify_playlist_info(playlist_url: str, token: str):
    """Vylepšená funkce pro získání informací o playlistu (fiktivní)."""
    return {"name": "Testovací Spotify Playlist", "total_tracks": 100}

def get_spotify_playlist_tracks(playlist_url: str, token: str):
    """Fiktivní získávání tracků z playlistu."""
    return [
        {"title": "Song One", "artist": "Artist A", "album": "Album X"},
        {"title": "Song Two", "artist": "Artist B", "album": "Album Y"},
        # ...atd
    ]

async def download_spotify_track_via_youtube_async(track_url: str, interaction: discord.Interaction):
    task_id = interaction.user.id
    ACTIVE_DOWNLOAD_TASKS[task_id] = asyncio.current_task()
    
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        if not SILENT_MODE: await interaction.followup.send("❌ Chybí Spotify Client ID / Secret v .env.")
        logging.error("❌ Chybí Spotify Client ID / Secret v .env.")
        return
    token = get_spotify_token(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)
    if not token:
        if not SILENT_MODE: await interaction.followup.send("❌ Nepodařilo se získat Spotify token.")
        return
    
    track_info = get_spotify_track_info(track_url, token)
    if not track_info:
        if not SILENT_MODE: await interaction.followup.send("❌ Nepodařilo se získat informace o tracku.")
        logging.error("❌ Nepodařilo se získat informace o tracku.")
        return

    # Složka: Downloads/Zvuk/Jméno uživatele
    user_folder_name = sanitize_filename(interaction.user.name)
    audio_user_dir = os.path.join(BASE_DOWNLOAD_DIR, AUDIO_DIR_NAME, user_folder_name)
    ensure_folder(audio_user_dir)
    
    query = f"{track_info['title']} {track_info['artist']}".strip()
    
    opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(audio_user_dir, "%(title)s.%(ext)s"),
        "download_archive": DOWNLOAD_ARCHIVE_FILE,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        },
        {
            "key": "FFmpegMetadata",
            "add_metadata": True,
        },
        {
            "key": "EmbedThumbnail",
            "already_have_thumbnail": False,
        }],
        "writethumbnail": True,
        "metadata": {
            "title": track_info['title'],
            "artist": track_info['artist'],
            "album": track_info['album']
        }
    }
    
    try:
        status_message = await interaction.followup.send(f"⏳ Zahajuji stahování `{track_info['title']}`...")
        await download_with_ytdlp(f"ytsearch1:{query}", audio_user_dir, opts, status_message, item_name=track_info['title'])
        # Finální zpráva je přesunuta do bloku finally
    except asyncio.CancelledError:
        if not SILENT_MODE: await interaction.followup.send("🛑 Stahování bylo zrušeno.")
    except Exception as e:
        error_msg = f"❌ Kritická chyba při stahování `{query}`: `{str(e).splitlines()[-1]}`"
        if not SILENT_MODE: await interaction.followup.send(error_msg) # FIX 2: Bezpečné hlášení chyby
        logging.error(f"❌ Chyba při stahování `{query}`: {e}")
        # Proměnná 'e' zde zůstane definovaná
    finally:
        if task_id in ACTIVE_DOWNLOAD_TASKS:
            # Kontrola, zda nedošlo ke zrušení nebo kritické chybě (kdy je 'e' definováno)
            if not ACTIVE_DOWNLOAD_TASKS[task_id].cancelled() and 'e' not in locals():
                await status_message.edit(content=f"✅ Dokončeno `{track_info['title']}`.")
            del ACTIVE_DOWNLOAD_TASKS[task_id]

async def download_spotify_playlist_via_youtube_async(playlist_url: str, interaction: discord.Interaction):
    task_id = interaction.user.id
    ACTIVE_DOWNLOAD_TASKS[task_id] = asyncio.current_task()
    
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        if not SILENT_MODE: await interaction.followup.send("❌ Chybí Spotify Client ID / Secret v .env.")
        logging.error("❌ Chybí Spotify Client ID / Secret v .env.")
        return
        
    token = get_spotify_token(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)
    if not token:
        if not SILENT_MODE: await interaction.followup.send("❌ Nepodařilo se získat Spotify token.")
        return
    
    playlist_info = get_spotify_playlist_info(playlist_url, token)
    if not playlist_info:
        playlist_name = "Neznámý Spotify Playlist"
        logging.warning("❌ Nepodařilo se získat informace o playlistu, ale pokračujem ve stahování.")
    else:
        playlist_name = playlist_info.get('name', 'Neznámý Playlist')

    # Složka: Downloads/Zvuk/Jméno uživatele/Název playlistu
    user_folder_name = sanitize_filename(interaction.user.name)
    audio_user_dir = os.path.join(BASE_DOWNLOAD_DIR, AUDIO_DIR_NAME, user_folder_name)
    ensure_folder(audio_user_dir)

    playlist_name_sanitized = sanitize_filename(playlist_name)
    playlist_dir = os.path.join(audio_user_dir, playlist_name_sanitized) 
    ensure_folder(playlist_dir)

    tracks = await asyncio.to_thread(get_spotify_playlist_tracks, playlist_url, token)
    if not tracks:
        if not SILENT_MODE: await interaction.followup.send("❌ Playlist je prázdný nebo se nepodařilo získat metadata.")
        logging.warning("❌ Playlist je prázdný nebo se nepodařilo získat metadata.")
        return
    
    download_urls = [f"ytsearch1:{track['title']} {track['artist']}".strip() for track in tracks]
    
    if not download_urls:
        if not SILENT_MODE: await interaction.followup.send("❌ Playlist neobsahuje žádné tracky pro stahování.")
        return

    opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(playlist_dir, "%(title)s.%(ext)s"),
        "download_archive": DOWNLOAD_ARCHIVE_FILE,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        },
        {
            "key": "FFmpegMetadata",
            "add_metadata": True,
        },
        {
            "key": "EmbedThumbnail",
            "already_have_thumbnail": False,
        }],
        "writethumbnail": True,
    }

    try:
        status_message = await interaction.followup.send(f"⏳ Zahajuji kontrolu a stahování `{playlist_name}` ({len(download_urls)} tracků)...")
        await download_with_ytdlp(download_urls, playlist_dir, opts, status_message, item_name=f"{playlist_name} playlist")
        
    except asyncio.CancelledError:
        if not SILENT_MODE: await interaction.followup.send("🛑 Stahování bylo zrušeno.")
    except Exception as e:
        error_msg = f"❌ Kritická chyba při stahování playlistu `{playlist_name}`: `{str(e).splitlines()[-1]}`"
        if not SILENT_MODE: await interaction.followup.send(error_msg) # FIX 2: Bezpečné hlášení chyby
        logging.error(f"❌ Chyba při stahování playlistu `{playlist_name}`: {e}")
        # Proměnná 'e' zde zůstane definovaná
    finally:
        if task_id in ACTIVE_DOWNLOAD_TASKS: 
            if not ACTIVE_DOWNLOAD_TASKS[task_id].cancelled() and 'e' not in locals():
                await status_message.edit(content=f"**Hotovo!** Stahování/kontrola playlistu `{playlist_name}` dokončeno. (Nedostupné položky byly přeskočeny)")
            
            del ACTIVE_DOWNLOAD_TASKS[task_id]
            
            if 'e' not in locals(): 
                playlist_id_unique = extract_playlist_id(playlist_url)
                if playlist_id_unique:
                    playlist_data = load_playlist_data()
                    playlist_data[playlist_id_unique] = {
                        "url": playlist_url,
                        "folder": os.path.join(user_folder_name, playlist_name_sanitized), 
                    }
                    save_playlist_data(playlist_data)
                    await interaction.followup.send(f"✅ Playlist `{playlist_name}` byl přidán k automatickému sledování. Pro kontrolu nových skladeb použijte příkaz `/check`.", ephemeral=True)

async def download_youtube_playlist_video_async(url: str, interaction: discord.Interaction):
    """Stáhne YouTube playlist jako video do VIDEO_SUB_DIR_NAME/Jméno uživatele/Název Playlistu."""
    task_id = interaction.user.id
    ACTIVE_DOWNLOAD_TASKS[task_id] = asyncio.current_task()
    
    try:
        status_message = await interaction.followup.send("⏳ Získávám informace o YouTube playlistu...")
        
        # Extrahuj metadata bez stahování
        info = await asyncio.to_thread(yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': 'in_playlist', 'ignoreerrors': True}).extract_info, url, download=False)
        
        if not info or 'title' not in info:
            await status_message.edit(content="❌ Nepodařilo se získat název playlistu. Zkontrolujte, zda je veřejný.")
            del ACTIVE_DOWNLOAD_TASKS[task_id]
            return

        playlist_name = info['title']
        playlist_name_sanitized = sanitize_filename(playlist_name)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Chyba při získávání informací o playlistu: {e}")
        logging.error(f"❌ Chyba při získávání informací o YouTube playlistu: {e}")
        del ACTIVE_DOWNLOAD_TASKS[task_id]
        return

    # Složka: Downloads/Video/Jméno uživatele/Název Playlistu
    user_folder_name = sanitize_filename(interaction.user.name)
    out_dir = os.path.join(BASE_DOWNLOAD_DIR, VIDEO_DIR_NAME, user_folder_name, playlist_name_sanitized) 
    ensure_folder(out_dir)

    # Nastav možnosti stahování (Video)
    opts = {
        "format": "bestvideo[height<=1080]+bestaudio/best", 
        "merge_output_format": "mp4", 
        "outtmpl": os.path.join(out_dir, "%(title)s.%(ext)s"),
        "download_archive": DOWNLOAD_ARCHIVE_FILE # Pro přeskakování
    }
    
    try:
        # Přejmenuj status message pro stahování
        await status_message.edit(content=f"⏳ Zahajuji stahování VIDEO playlistu `{playlist_name}`...")
        
        # Spusť stahování
        await download_with_ytdlp(url, out_dir, opts, status_message, item_name=playlist_name)
        
        # Finální zpráva je přesunuta do bloku finally
    except asyncio.CancelledError:
        if not SILENT_MODE: await status_message.edit(content="🛑 Stahování bylo zrušeno.")
    except Exception as e:
        error_msg = f"❌ Kritická chyba při stahování playlistu `{playlist_name}`: `{str(e).splitlines()[-1]}`"
        if not SILENT_MODE: await interaction.followup.send(error_msg) # FIX 2: Bezpečné hlášení chyby
        logging.error(f"❌ Chyba při stahování playlistu `{playlist_name}`: {e}")
        # Proměnná 'e' zde zůstane definovaná
    finally:
        if task_id in ACTIVE_DOWNLOAD_TASKS:
            if not ACTIVE_DOWNLOAD_TASKS[task_id].cancelled() and 'e' not in locals():
                await status_message.edit(content=f"✅ Stahování VIDEO playlistu `{playlist_name}` dokončeno. (Nedostupné položky byly přeskočeny)")
            del ACTIVE_DOWNLOAD_TASKS[task_id]

async def download_youtube_playlist_audio_async(url: str, interaction: discord.Interaction):
    """Stáhne YouTube playlist jako audio do AUDIO_SUB_DIR_NAME/Jméno uživatele/Název Playlistu."""
    task_id = interaction.user.id
    ACTIVE_DOWNLOAD_TASKS[task_id] = asyncio.current_task()
    
    try:
        status_message = await interaction.followup.send("⏳ Získávám informace o YouTube playlistu...")
        
        # Extrahuj metadata bez stahování
        info = await asyncio.to_thread(yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': 'in_playlist', 'ignoreerrors': True}).extract_info, url, download=False)
        
        if not info or 'title' not in info:
            await status_message.edit(content="❌ Nepodařilo se získat název playlistu. Zkontrolujte, zda je veřejný.")
            del ACTIVE_DOWNLOAD_TASKS[task_id]
            return

        playlist_name = info['title']
        playlist_name_sanitized = sanitize_filename(playlist_name)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Chyba při získávání informací o playlistu: {e}")
        logging.error(f"❌ Chyba při získávání informací o YouTube playlistu: {e}")
        del ACTIVE_DOWNLOAD_TASKS[task_id]
        return

    # Složka: Downloads/Zvuk/Jméno uživatele/Název Playlistu
    user_folder_name = sanitize_filename(interaction.user.name)
    out_dir = os.path.join(BASE_DOWNLOAD_DIR, AUDIO_DIR_NAME, user_folder_name, playlist_name_sanitized) 
    ensure_folder(out_dir)

    # Nastav možnosti stahování (Audio MP3)
    opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(out_dir, "%(title)s.%(ext)s"),
        "download_archive": DOWNLOAD_ARCHIVE_FILE,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    }
    
    try:
        # Přejmenuj status message pro stahování
        await status_message.edit(content=f"⏳ Zahajuji stahování ZVUK playlistu `{playlist_name}`...")
        
        # Spusť stahování
        await download_with_ytdlp(url, out_dir, opts, status_message, item_name=playlist_name)
        
        # Finální zpráva je přesunuta do bloku finally
    except asyncio.CancelledError:
        if not SILENT_MODE: await status_message.edit(content="🛑 Stahování bylo zrušeno.")
    except Exception as e:
        error_msg = f"❌ Kritická chyba při stahování playlistu `{playlist_name}`: `{str(e).splitlines()[-1]}`"
        if not SILENT_MODE: await interaction.followup.send(error_msg) # FIX 2: Bezpečné hlášení chyby
        logging.error(f"❌ Chyba při stahování playlistu `{playlist_name}`: {e}")
        # Proměnná 'e' zde zůstane definovaná
    finally:
        if task_id in ACTIVE_DOWNLOAD_TASKS:
            if not ACTIVE_DOWNLOAD_TASKS[task_id].cancelled() and 'e' not in locals():
                await status_message.edit(content=f"✅ Stahování ZVUK playlistu `{playlist_name}` dokončeno. (Nedostupné položky byly přeskočeny)")
            del ACTIVE_DOWNLOAD_TASKS[task_id]


async def download_generic_async(url: str, as_audio: bool, interaction: discord.Interaction):
    task_id = interaction.user.id
    ACTIVE_DOWNLOAD_TASKS[task_id] = asyncio.current_task()
    
    user_folder_name = sanitize_filename(interaction.user.name)

    if as_audio:
        # Složka: Downloads/Zvuk/Jméno uživatele
        out_dir = os.path.join(BASE_DOWNLOAD_DIR, AUDIO_DIR_NAME, user_folder_name)
    else:
        # Složka: Downloads/Video/Jméno uživatele
        out_dir = os.path.join(BASE_DOWNLOAD_DIR, VIDEO_DIR_NAME, user_folder_name)

    ensure_folder(out_dir)
    
    # --- Získání názvu pro lepší zpětnou vazbu ---
    status_message = await interaction.followup.send("⏳ Získávám informace o videu/zvuku...")
    item_name = url 
    try:
        # Použij extract_info pro získání názvu
        info = await asyncio.to_thread(yt_dlp.YoutubeDL({'quiet': True, 'ignoreerrors': True}).extract_info, url, download=False)
        item_name = info.get('title', url)
    except Exception:
        pass # Ignorovat chyby při získávání názvu, použít URL
    
    await status_message.edit(content=f"⏳ Zahajuji stahování `{item_name}`...")
    # ---------------------------------------------

    if as_audio:
        opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(out_dir, "%(title)s.%(ext)s"),
            "download_archive": DOWNLOAD_ARCHIVE_FILE,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
        }
    else:
        opts = {
            "format": "bestvideo[height<=1080]+bestaudio/best", 
            "merge_output_format": "mp4", 
            "outtmpl": os.path.join(out_dir, "%(title)s.%(ext)s"),
            "download_archive": DOWNLOAD_ARCHIVE_FILE
        }
    
    try:
        await download_with_ytdlp(url, out_dir, opts, status_message, item_name=item_name)
        # Finální zpráva je přesunuta do bloku finally
    except asyncio.CancelledError:
        if not SILENT_MODE: await status_message.edit(content="🛑 Stahování bylo zrušeno.")
    except Exception as e:
        error_msg = f"❌ Kritická chyba při stahování `{item_name}`: `{str(e).splitlines()[-1]}`"
        if not SILENT_MODE: await interaction.followup.send(error_msg) # FIX 2: Bezpečné hlášení chyby
        logging.error(f"❌ Chyba při stahování: {e}")
        # Proměnná 'e' zde zůstane definovaná
    finally:
        if task_id in ACTIVE_DOWNLOAD_TASKS:
            if not ACTIVE_DOWNLOAD_TASKS[task_id].cancelled() and 'e' not in locals():
                await status_message.edit(content=f"✅ Stahování `{item_name}` dokončeno.")
            del ACTIVE_DOWNLOAD_TASKS[task_id]

# -------------------------------------------
# Discord bot příkazy a interaktivní tlačítka
# -------------------------------------------

class DownloadView(discord.ui.View):
    def __init__(self, url: str):
        super().__init__(timeout=180.0)
        self.url = url
    
    @discord.ui.button(label="Video", style=discord.ButtonStyle.primary, emoji="🎬")
    async def video_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.defer(ephemeral=False)
        self.stop()
        await download_generic_async(self.url, as_audio=False, interaction=interaction)

    @discord.ui.button(label="Zvuk", style=discord.ButtonStyle.secondary, emoji="🎧")
    async def audio_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.defer(ephemeral=False)
        self.stop()
        await download_generic_async(self.url, as_audio=True, interaction=interaction)

class YoutubePlaylistView(discord.ui.View):
    def __init__(self, url: str):
        super().__init__(timeout=180.0)
        self.url = url

    @discord.ui.button(label="Video Playlist", style=discord.ButtonStyle.primary, emoji="🎞️")
    async def video_playlist_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.defer(ephemeral=False)
        self.stop()
        await download_youtube_playlist_video_async(self.url, interaction)

    @discord.ui.button(label="Zvuk Playlist (MP3)", style=discord.ButtonStyle.secondary, emoji="🎵")
    async def audio_playlist_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.defer(ephemeral=False)
        self.stop()
        await download_youtube_playlist_audio_async(self.url, interaction)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    logging.info(f'✅ Bot je připojen jako {bot.user}')

    # Kontrola pro FFMPEG
    try:
        subprocess.check_call(['ffmpeg', '-version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logging.info("✅ Systémový FFMPEG je dostupný.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        logging.critical("❌ FFMPEG nebyl nalezen v systémové PATH! Stahování zvuku a spojování videa/zvuku nebude fungovat. Použijte 'sudo apt install ffmpeg'.")
        await send_dm_to_owner("⚠️ **Upozornění:** FFMPEG nebyl nalezen v systémové PATH. Stahování zvuku a spojování videa/zvuku nebude fungovat.", error_details="Nainstalujte FFMPEG přes 'sudo apt install ffmpeg'.")


    await bot.tree.sync()
    logging.info("✅ Slash commandy byly synchronizovány.")

    await send_dm_to_owner("✅ Bot byl úspěšně spuštěn a je online.")
    
    # Spuštění smyčky pro kontrolu playlistů
    bot.loop.create_task(check_for_new_songs_async())

# --- Slash Commands ---

@bot.tree.command(name="sync", description="Synchronizuje globální slash commandy.")
async def sync_commands(interaction: discord.Interaction):
    if not is_owner_or_designated_channel(interaction):
        await interaction.response.send_message("Nemáš oprávnění použít tento příkaz.", ephemeral=True)
        return

    await interaction.response.send_message("⏳ Synchronizuji slash commandy...", ephemeral=True)
    await bot.tree.sync()
    await interaction.followup.send("✅ Slash commandy byly synchronizovány.", ephemeral=True)

@bot.tree.command(name='stahni', description='Stáhne obsah z dané URL (YouTube, TikTok, Instagram, Spotify).')
@app_commands.describe(url="URL odkazu (YouTube, TikTok, Instagram, Spotify)")
async def stahni_command(interaction: discord.Interaction, url: str):
    if not is_owner_or_designated_channel(interaction):
        await interaction.response.send_message("Nemáš oprávnění použít tento příkaz.", ephemeral=True)
        return

    platform = detect_platform(url)
    if not platform:
        await interaction.response.send_message("❌ Nepodporovaná platforma.", ephemeral=True)
        return

    await interaction.response.defer() 

    if platform == "spotify_playlist" or platform == "spotify_test_url":
        await download_spotify_playlist_via_youtube_async(url, interaction)
    elif platform == "youtube_playlist":
        view = YoutubePlaylistView(url)
        await interaction.followup.send("Chceš stáhnout **celý playlist** jako **video** nebo **zvuk (MP3)**?", view=view)
    elif platform == "spotify_track":
        await download_spotify_track_via_youtube_async(url, interaction)
    elif platform in ["youtube", "tiktok", "instagram"]:
        view = DownloadView(url)
        await interaction.followup.send("Chceš stáhnout **video** nebo **zvuk**?", view=view)

@bot.tree.command(name='dlstop', description='Zastaví probíhající stahování yt-dlp.')
async def dlstop_command(interaction: discord.Interaction):
    task_id = interaction.user.id
    if task_id in ACTIVE_DOWNLOAD_TASKS:
        task = ACTIVE_DOWNLOAD_TASKS[task_id]
        if not task.done():
            task.cancel()
            await interaction.response.send_message("✅ Pokus o zastavení stahování. Může chvíli trvat, než se proces ukončí.", ephemeral=True)
        else:
            await interaction.response.send_message("✅ Žádné aktivní stahování neprobíhá.", ephemeral=True)
    else:
        await interaction.response.send_message("✅ Žádné aktivní stahování neprobíhá.", ephemeral=True)

@bot.tree.command(name='check', description='Spustí okamžitou kontrolu nových skladeb v sledovaných playlistech.')
async def check_command(interaction: discord.Interaction):
    if not is_owner_or_designated_channel(interaction):
        await interaction.response.send_message("Nemáš oprávnění použít tento příkaz.", ephemeral=True)
        return

    await interaction.response.defer()
    await interaction.followup.send("⏳ Spouštím kontrolu nových skladeb...", ephemeral=True)
    await check_for_new_songs_async(manual_run=True)
    await interaction.followup.send("✅ Kontrola dokončena.", ephemeral=True)

@bot.tree.command(name='silent', description='Přepíná "silent" mód, kdy bot neposílá potvrzovací zprávy.')
async def silent_command(interaction: discord.Interaction):
    if not is_owner_or_designated_channel(interaction):
        await interaction.response.send_message("Nemáš oprávnění použít tento příkaz.", ephemeral=True)
        return
        
    global SILENT_MODE
    SILENT_MODE = not SILENT_MODE
    status = "Zapnut" if SILENT_MODE else "Vypnut"
    await interaction.response.send_message(f"**Silent mód** byl `{status}`.", ephemeral=True)

@bot.tree.command(name='stop', description='Ukončí a restartuje bota.')
async def stop_command(interaction: discord.Interaction):
    if not is_owner_or_designated_channel(interaction):
        await interaction.response.send_message("Nemáš oprávnění použít tento příkaz.", ephemeral=True)
        return

    await interaction.response.send_message("🛑 Zastavuji a restartuji bota...", ephemeral=True)
    await send_dm_to_owner("🛑 Bot byl restartován příkazem `/stop`.")
    os.execv(sys.executable, ['python3'] + sys.argv) 

@bot.tree.command(name='shutdown', description='Vypne bota bez restartu.')
async def shutdown_command(interaction: discord.Interaction):
    if not is_owner_or_designated_channel(interaction):
        await interaction.response.send_message("Nemáš oprávnění použít tento příkaz.", ephemeral=True)
        return
    
    await interaction.response.send_message("🛑 Vypínám bota...", ephemeral=True)
    logging.info("🛑 Bot je vypínán příkazem /shutdown.")
    await send_dm_to_owner("🛑 Bot byl vypnut příkazem `/shutdown`.")
    await bot.close()
        
# -------------------------------------------
# Spuštění bota
# -------------------------------------------
if __name__ == "__main__":
    ensure_folder(BASE_DOWNLOAD_DIR)
    ensure_folder(os.path.join(BASE_DOWNLOAD_DIR, AUDIO_DIR_NAME))
    ensure_folder(os.path.join(BASE_DOWNLOAD_DIR, VIDEO_DIR_NAME))
    
    # Zajistíme existenci archivačního souboru
    Path(DOWNLOAD_ARCHIVE_FILE).touch(exist_ok=True)

    if not DISCORD_BOT_TOKEN:
        logging.critical("❌ Chybí DISCORD_BOT_TOKEN v .env souboru. Bot nelze spustit.")
        print("❌ Chybí DISCORD_BOT_TOKEN v .env souboru. Bot nelze spustit.")
    else:
        try:
            bot.run(DISCORD_BOT_TOKEN)
        except Exception as e:
            logging.critical(f"❌ Chyba při spouštění bota: {e}")
            print(f"❌ Chyba při spouštění bota: {e}")