import os
import re
import json
import ctypes
from .config import APP_DIR


def sanitize_filename(name):
    """Removes invalid Windows filename characters and yt-dlp template tokens."""
    cleaned = re.sub(r'[<>:"/\\|?*]', "", (name or "")).strip()
    return cleaned.replace("%", "%%").replace("{", "{{").replace("}", "}}")


def sanitize_folder_name(name):
    """Removes invalid Windows folder name characters for direct os.makedirs usage."""
    cleaned = re.sub(r'[<>:"/\\|?*]', "", (name or "")).strip().rstrip(".")
    return cleaned


def json_unquote(raw):
    try:
        val = json.loads(raw)
        return "" if val is None else str(val)
    except Exception:
        return raw


def alnum_key(text):
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def find_global_binary(exe_name):
    """Searches system PATH for exe_name while ignoring APP_DIR."""
    app_norm = os.path.normcase(os.path.abspath(APP_DIR))
    for folder in os.environ.get("PATH", "").split(os.pathsep):
        folder = folder.strip().strip('"')
        if not folder:
            continue
        try:
            if os.path.normcase(os.path.abspath(folder)) == app_norm:
                continue
            candidate = os.path.join(folder, exe_name)
            if os.path.isfile(candidate):
                return candidate
        except Exception:
            continue
    return None


def format_seconds(sec):
    sec = max(0, int(sec or 0))
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def is_windows_dark_mode():
    if os.name == "nt":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            )
            val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return val == 0
        except Exception:
            pass
    return False


def set_windows_titlebar_dark(window, is_dark):
    if os.name == "nt":
        try:
            window.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
            value = ctypes.c_int(1 if is_dark else 0)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 20, ctypes.byref(value), ctypes.sizeof(value)
            )
        except Exception:
            pass


def apply_high_dpi_window_icon(window, ico_path):
    """
    Loads the exact system-DPI small and large icon frames from ico_path via Win32 LoadImageW
    and assigns them with WM_SETICON so 4K / High-DPI titlebars and taskbars stay razor-sharp.
    """
    if os.name != "nt" or not os.path.isfile(ico_path):
        return
    try:
        window.update_idletasks()
        user32 = ctypes.windll.user32
        hwnd = user32.GetParent(window.winfo_id()) or window.winfo_id()

        SM_CXICON = 11
        SM_CYICON = 12
        SM_CXSMICON = 49
        SM_CYSMICON = 50
        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x0010
        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1

        sm_w = max(24, user32.GetSystemMetrics(SM_CXSMICON))
        sm_h = max(24, user32.GetSystemMetrics(SM_CYSMICON))
        lg_w = max(48, user32.GetSystemMetrics(SM_CXICON))
        lg_h = max(48, user32.GetSystemMetrics(SM_CYICON))

        user32.LoadImageW.argtypes = [
            ctypes.c_void_p,
            ctypes.c_wchar_p,
            ctypes.c_uint,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint,
        ]
        user32.LoadImageW.restype = ctypes.c_void_p

        h_small = user32.LoadImageW(None, ico_path, IMAGE_ICON, sm_w, sm_h, LR_LOADFROMFILE)
        h_big = user32.LoadImageW(None, ico_path, IMAGE_ICON, lg_w, lg_h, LR_LOADFROMFILE)

        if h_small:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, h_small)
        if h_big:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, h_big)
    except Exception:
        pass


def find_downloaded_file_fallback(entry, default_save_dir):
    """Finds files whose stored path missed Unicode punctuation or older entries without filepath."""
    saved_path = entry.get("filepath", "")
    title_key = alnum_key(entry.get("title", ""))
    base_key = alnum_key(os.path.splitext(os.path.basename(saved_path))[0]) if saved_path else ""
    folder_key = alnum_key(os.path.basename(os.path.dirname(saved_path))) if saved_path else ""

    search_roots = []
    if saved_path:
        parent_of_folder = os.path.dirname(os.path.dirname(saved_path))
        if os.path.isdir(parent_of_folder):
            search_roots.append(parent_of_folder)
    if os.path.isdir(default_save_dir) and default_save_dir not in search_roots:
        search_roots.append(default_save_dir)

    best_match = None
    best_score = 0

    for root_dir in search_roots:
        try:
            entries = list(os.scandir(root_dir))
        except OSError:
            continue

        scan_dirs = [(root_dir, False)]
        for e in entries:
            if e.is_dir():
                scan_dirs.append((e.path, True))

        for dpath, is_sub in scan_dirs:
            dkey = alnum_key(os.path.basename(dpath)) if is_sub else ""
            try:
                for item in os.scandir(dpath):
                    if not item.is_file():
                        continue
                    fname_no_ext = os.path.splitext(item.name)[0]
                    fkey = alnum_key(fname_no_ext)
                    if not fkey:
                        continue

                    score = 0
                    if base_key and fkey == base_key:
                        score += 10
                    elif title_key and (fkey == title_key or fkey.endswith(title_key)):
                        score += 6
                    elif title_key and len(title_key) >= 4 and title_key in fkey:
                        score += 3

                    if score > 0 and folder_key and dkey == folder_key:
                        score += 5

                    if score > best_score:
                        best_score = score
                        best_match = item.path
            except OSError:
                continue

    return best_match if best_score >= 6 else None
