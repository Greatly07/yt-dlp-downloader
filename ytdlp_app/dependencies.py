import os
import sys
import json
import base64
import shutil
import zipfile
import tempfile
import urllib.parse
import urllib.request
from .config import (
    APP_DIR,
    YTDLP_PATH,
    FFMPEG_PATH,
    FFPROBE_PATH,
    NODE_PATH,
    NODE_WIN64_URL,
    FFMPEG_WIN64_ZIP_URL,
    URI_SCHEME,
)
from .utils import find_global_binary


def resolve_ytdlp_exe(pref_mode="global"):
    """Resolves yt-dlp.exe path based on preference ('global' or 'local')."""
    global_yt = find_global_binary("yt-dlp.exe")
    local_exists = os.path.isfile(YTDLP_PATH)
    if pref_mode == "local":
        if local_exists:
            return YTDLP_PATH
        if global_yt:
            return global_yt
    else:
        if local_exists:
            # Keep app-folder yt-dlp priority for self-updating unless missing
            return YTDLP_PATH
        if global_yt:
            return global_yt
    return "yt-dlp"


def resolve_binary(exe_name, local_path, pref_mode="global"):
    """
    Resolves ffmpeg.exe, ffprobe.exe, or node.exe without deleting local files.
    pref_mode: 'global' (prefers system PATH, falls back to APP_DIR) or 'local' (prefers APP_DIR, falls back to PATH).
    """
    global_bin = find_global_binary(exe_name)
    local_exists = os.path.isfile(local_path)
    if pref_mode == "local":
        if local_exists:
            return local_path
        if global_bin:
            return global_bin
    else:
        if global_bin:
            return global_bin
        if local_exists:
            return local_path
    return None


def describe_binary_status(exe_name, local_path, pref_mode="global"):
    """Returns a human-readable status line showing both Global PATH and App Folder state."""
    global_bin = find_global_binary(exe_name)
    local_exists = os.path.isfile(local_path)

    active = resolve_binary(exe_name, local_path, pref_mode) if exe_name != "yt-dlp.exe" else (
        YTDLP_PATH if local_exists else global_bin
    )

    if not active:
        return f"✖ {exe_name}: NOT INSTALLED (Neither on Global PATH nor in App Folder)"

    using_local = os.path.normcase(os.path.abspath(active)) == os.path.normcase(os.path.abspath(local_path))
    source_tag = "App Folder (Local)" if using_local else "System Global PATH"
    extras = []
    if using_local and global_bin:
        extras.append(f"Global PATH also available: {global_bin}")
    elif (not using_local) and local_exists:
        extras.append("Local copy also present in App Folder")

    extra_str = f"  [{'; '.join(extras)}]" if extras else ""
    return f"✔ {exe_name}: Active via {source_tag} — {active}{extra_str}"


def download_ffmpeg_to_app_dir(progress_cb=None):
    """
    Downloads the official yt-dlp FFmpeg Windows x64 build zip and extracts ffmpeg.exe & ffprobe.exe into APP_DIR.
    progress_cb(str): optional callback for logging progress lines.
    """
    def log(msg):
        if progress_cb:
            progress_cb(msg)

    log(f"Downloading FFmpeg & FFprobe from:\n{FFMPEG_WIN64_ZIP_URL}\n")
    tmp_zip = os.path.join(tempfile.gettempdir(), "ytdlp_ffmpeg_win64.zip")
    try:
        req = urllib.request.Request(
            FFMPEG_WIN64_ZIP_URL, headers={"User-Agent": "yt-dlp-Downloader-App/2.0"}
        )
        with urllib.request.urlopen(req, timeout=60) as resp, open(tmp_zip, "wb") as out_f:
            total = int(resp.headers.get("Content-Length") or 0)
            downloaded = 0
            last_pct = -1
            while True:
                chunk = resp.read(256 * 1024)
                if not chunk:
                    break
                out_f.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = int((downloaded * 100) / total)
                    if pct >= last_pct + 10:
                        last_pct = pct
                        mb_done = downloaded / (1024 * 1024)
                        mb_tot = total / (1024 * 1024)
                        log(f"  FFmpeg download progress: {pct}% ({mb_done:.1f} / {mb_tot:.1f} MB)\n")

        log("Extracting ffmpeg.exe and ffprobe.exe into App Folder...\n")
        extracted = []
        with zipfile.ZipFile(tmp_zip, "r") as zf:
            for member in zf.namelist():
                base = os.path.basename(member).lower()
                if base in ("ffmpeg.exe", "ffprobe.exe"):
                    dest = os.path.join(APP_DIR, base)
                    with zf.open(member) as src, open(dest + ".tmp", "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    os.replace(dest + ".tmp", dest)
                    extracted.append(base)

        if not extracted:
            raise RuntimeError("Archive did not contain ffmpeg.exe or ffprobe.exe.")

        log(f"✔ Successfully installed {', '.join(extracted)} in {APP_DIR}\n")
        return True
    finally:
        if os.path.exists(tmp_zip):
            try:
                os.remove(tmp_zip)
            except OSError:
                pass


def download_nodejs_to_app_dir(progress_cb=None):
    """
    Downloads standalone Windows x64 node.exe from nodejs.org into APP_DIR.
    """
    def log(msg):
        if progress_cb:
            progress_cb(msg)

    log(f"Downloading standalone Node.js (node.exe) from:\n{NODE_WIN64_URL}\n")
    tmp_exe = NODE_PATH + ".tmp"
    try:
        req = urllib.request.Request(
            NODE_WIN64_URL, headers={"User-Agent": "yt-dlp-Downloader-App/2.0"}
        )
        with urllib.request.urlopen(req, timeout=60) as resp, open(tmp_exe, "wb") as out_f:
            total = int(resp.headers.get("Content-Length") or 0)
            downloaded = 0
            last_pct = -1
            while True:
                chunk = resp.read(256 * 1024)
                if not chunk:
                    break
                out_f.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = int((downloaded * 100) / total)
                    if pct >= last_pct + 10:
                        last_pct = pct
                        mb_done = downloaded / (1024 * 1024)
                        mb_tot = total / (1024 * 1024)
                        log(f"  Node.js download progress: {pct}% ({mb_done:.1f} / {mb_tot:.1f} MB)\n")

        os.replace(tmp_exe, NODE_PATH)
        log(f"✔ Successfully installed node.exe in {APP_DIR}\n")
        return True
    finally:
        if os.path.exists(tmp_exe):
            try:
                os.remove(tmp_exe)
            except OSError:
                pass


def cleanup_local_dependencies(only_if_global=False):
    """
    Deletes local ffmpeg.exe, ffprobe.exe, and node.exe from APP_DIR.
    Returns (removed_list, skipped_list, error_list).
    """
    removed = []
    skipped = []
    errors = []
    for exe_name, local_path in (
        ("ffmpeg.exe", FFMPEG_PATH),
        ("ffprobe.exe", FFPROBE_PATH),
        ("node.exe", NODE_PATH),
    ):
        if not os.path.isfile(local_path):
            continue
        if only_if_global and not find_global_binary(exe_name):
            skipped.append(f"{exe_name} (kept because not found on Global PATH)")
            continue
        try:
            os.remove(local_path)
            removed.append(exe_name)
        except OSError as e:
            errors.append(f"{exe_name}: {e}")
    return removed, skipped, errors


# ============================================================================
# SONGPULSE URI PROTOCOL REGISTRATION & CLI / URI PARSER
# ============================================================================
def get_launch_command_for_protocol():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" "%1"'
    script_path = os.path.join(APP_DIR, "yt_dlp_app.pyw")
    return f'"{sys.executable}" "{script_path}" "%1"'


def register_songpulse_protocol():
    """
    Registers ytdlp:// custom URI protocol in HKEY_CURRENT_USER\\Software\\Classes\\ytdlp
    so SongPulse (web or desktop) can launch yt-dlp Downloader directly without Admin permissions.
    """
    if os.name != "nt":
        return False, "Protocol registration is only supported on Windows."
    try:
        import winreg
        base_key_path = rf"Software\Classes\{URI_SCHEME}"
        cmd_str = get_launch_command_for_protocol()

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base_key_path) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "URL:yt-dlp Downloader Protocol")
            winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")

        icon_target = sys.executable if getattr(sys, "frozen", False) else os.path.join(APP_DIR, "yt-dlp.ico")
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{base_key_path}\DefaultIcon") as ikey:
            winreg.SetValueEx(ikey, "", 0, winreg.REG_SZ, f'"{icon_target}",0')

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{base_key_path}\shell\open\command") as ckey:
            winreg.SetValueEx(ckey, "", 0, winreg.REG_SZ, cmd_str)

        return True, f"Registered '{URI_SCHEME}://' protocol -> {cmd_str}"
    except Exception as e:
        return False, f"Failed to register '{URI_SCHEME}://' protocol: {e}"


def is_songpulse_protocol_registered():
    if os.name != "nt":
        return False
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, rf"Software\Classes\{URI_SCHEME}\shell\open\command"
        ) as key:
            val, _ = winreg.QueryValueEx(key, "")
            return bool(val)
    except Exception:
        return False


def _split_url_tokens(raw_str):
    """Splits a string of URLs separated by newlines, commas, or pipes."""
    if not raw_str:
        return []
    urls = []
    # First check if it's a JSON list
    s = raw_str.strip()
    if s.startswith("[") and s.endswith("]"):
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return [str(u).strip() for u in parsed if str(u).strip()]
        except Exception:
            pass
    # Otherwise split by newline, pipe, or comma preceding http(s)://
    for line in s.replace("|", "\n").splitlines():
        line = line.strip()
        if not line:
            continue
        # Split comma-separated URLs like "https://a,https://b"
        parts = [p.strip() for p in line.split(",") if p.strip()]
        if len(parts) > 1 and all(p.startswith(("http://", "https://")) for p in parts):
            urls.extend(parts)
        else:
            urls.append(line)
    return urls


def parse_launch_arguments(argv=None):
    """
    Parses CLI arguments or a SongPulse 'ytdlp://...' URI into a structured job dictionary:
    Returns None if launched normally without arguments, or:
    {
        "source": "songpulse" | "cli",
        "playlist_name": str,
        "urls": list[str],
        "preset": str | None,
        "auto_start": bool,
    }
    Supported URI patterns:
      ytdlp://download?playlist=My%20Playlist&urls=https://...,https://...
      ytdlp://songpulse?name=Chill%20Vibes&url=https://...&url=https://...
      ytdlp://batch?data=<base64-encoded JSON {"playlist": "...", "urls": [...]}>
    Supported CLI flags:
      yt_dlp_app.exe --songpulse --playlist "My Playlist" --urls <url1> <url2>
      yt_dlp_app.exe --batch-file <path-to-json-or-txt>
    """
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        return None

    playlist_name = ""
    urls = []
    preset = "Preset 3: Playlist"
    auto_start = True
    source = "cli"

    i = 0
    while i < len(argv):
        arg = argv[i].strip()
        if not arg:
            i += 1
            continue

        # 1. Check for ytdlp:// URI
        if arg.lower().startswith(f"{URI_SCHEME}://"):
            source = "songpulse"
            parsed = urllib.parse.urlparse(arg)
            qs = urllib.parse.parse_qs(parsed.query)

            # Check base64 JSON payload if present
            if "data" in qs and qs["data"]:
                try:
                    raw_b64 = qs["data"][0]
                    pad = "=" * ((4 - len(raw_b64) % 4) % 4)
                    payload = json.loads(base64.urlsafe_b64decode(raw_b64 + pad).decode("utf-8"))
                    if isinstance(payload, dict):
                        playlist_name = payload.get("playlist") or payload.get("name") or playlist_name
                        p_urls = payload.get("urls") or payload.get("tracks") or payload.get("links") or []
                        if isinstance(p_urls, list):
                            urls.extend([str(u).strip() for u in p_urls if str(u).strip()])
                        elif isinstance(p_urls, str):
                            urls.extend(_split_url_tokens(p_urls))
                except Exception:
                    pass

            for key in ("playlist", "name", "folder", "title"):
                if key in qs and qs[key]:
                    playlist_name = urllib.parse.unquote_plus(qs[key][0]).strip()
                    break

            for key in ("url", "urls", "links", "tracks"):
                if key in qs:
                    for val in qs[key]:
                        urls.extend(_split_url_tokens(urllib.parse.unquote(val)))

            if "preset" in qs and qs["preset"]:
                p_req = qs["preset"][0].lower()
                if "video" in p_req or p_req == "1":
                    preset = "Preset 1: Video"
                elif "music" in p_req or p_req == "2":
                    preset = "Preset 2: Music"
                else:
                    preset = "Preset 3: Playlist"

            if "autostart" in qs and qs["autostart"]:
                auto_start = qs["autostart"][0].lower() not in ("0", "false", "no")

            i += 1
            continue

        # 2. Check CLI flags
        if arg in ("--songpulse", "--batch"):
            source = "songpulse"
            i += 1
            continue

        if arg in ("--no-autostart", "--queue-only"):
            auto_start = False
            i += 1
            continue

        if arg in ("--playlist", "--playlist-name", "--folder", "-p") and i + 1 < len(argv):
            playlist_name = argv[i + 1].strip()
            i += 2
            continue

        if arg in ("--preset",) and i + 1 < len(argv):
            p_req = argv[i + 1].strip().lower()
            if "video" in p_req or p_req == "1":
                preset = "Preset 1: Video"
            elif "music" in p_req or p_req == "2":
                preset = "Preset 2: Music"
            else:
                preset = "Preset 3: Playlist"
            i += 2
            continue

        if arg in ("--batch-file", "--file", "-f") and i + 1 < len(argv):
            fpath = argv[i + 1].strip()
            if os.path.isfile(fpath):
                try:
                    with open(fpath, "r", encoding="utf-8") as bf:
                        content = bf.read().strip()
                    if content.startswith("{"):
                        data = json.loads(content)
                        playlist_name = data.get("playlist") or data.get("name") or playlist_name
                        raw_u = data.get("urls") or data.get("links") or []
                        if isinstance(raw_u, list):
                            urls.extend([str(u).strip() for u in raw_u if str(u).strip()])
                    else:
                        urls.extend(_split_url_tokens(content))
                except Exception:
                    pass
            i += 2
            continue

        if arg in ("--urls", "--url", "-u"):
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                urls.extend(_split_url_tokens(argv[i]))
                i += 1
            continue

        if arg.startswith(("http://", "https://")):
            urls.extend(_split_url_tokens(arg))
            i += 1
            continue

        i += 1

    # Deduplicate while preserving order
    clean_urls = []
    for u in urls:
        u_clean = u.strip().strip('"').strip("'")
        if u_clean and u_clean not in clean_urls:
            clean_urls.append(u_clean)

    if not clean_urls and not playlist_name:
        return None

    return {
        "source": source,
        "playlist_name": playlist_name,
        "urls": clean_urls,
        "preset": preset,
        "auto_start": auto_start,
    }
