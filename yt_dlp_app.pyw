import os
import re
import sys
import json
import time
import ctypes
import shutil
import threading
import subprocess
import webbrowser
import urllib.request
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ============================================================================
# APP VERSION & GITHUB REPOSITORY CONFIG
# ============================================================================
APP_VERSION = "1.1.0"
GITHUB_REPO = "Greatly07/yt-dlp-downloader"

# Resolve paths matching "%~dp0" and "%~dp0.." from the batch file
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

PARENT_DIR = os.path.abspath(os.path.join(APP_DIR, ".."))
if any(p in APP_DIR.lower() for p in ("program files", "appdata")):
    DEFAULT_SAVE_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
else:
    DEFAULT_SAVE_DIR = PARENT_DIR

YTDLP_PATH = os.path.join(APP_DIR, "yt-dlp.exe")
FFMPEG_PATH = os.path.join(APP_DIR, "ffmpeg.exe")
FFPROBE_PATH = os.path.join(APP_DIR, "ffprobe.exe")
NODE_PATH = os.path.join(APP_DIR, "node.exe")
ICON_PATH = os.path.join(APP_DIR, "yt-dlp.ico")
SETTINGS_FILE = os.path.join(APP_DIR, "yt_dlp_settings.json")
HISTORY_FILE = os.path.join(APP_DIR, "yt_dlp_history.json")

PREVIEW_W = 360
PREVIEW_H = 202
PREVIEW_FPS = 15
LOG_MIN_HEIGHT = 130
LOG_MAX_HEIGHT = 220

QUALITY_PRESETS = [
    ("Auto (Best)", "best"),
    ("2160p (4K)", "2160"),
    ("1440p", "1440"),
    ("1080p", "1080"),
    ("720p", "720"),
    ("480p", "480"),
    ("360p", "360"),
]
QUALITY_LABEL_TO_VAL = {lbl: val for lbl, val in QUALITY_PRESETS}
QUALITY_VAL_TO_LABEL = {val: lbl for lbl, val in QUALITY_PRESETS}

SUB_LANG_PRESETS = [
    ("English (en)", "en.*,en"),
    ("Indonesian (id)", "id.*,id"),
    ("Japanese (ja)", "ja.*,ja"),
    ("English + Indonesian", "en.*,en,id.*,id"),
    ("All Languages", "all"),
    ("Custom", "custom"),
]
SUB_LABEL_TO_VAL = {lbl: val for lbl, val in SUB_LANG_PRESETS}
SUB_VAL_TO_LABEL = {val: lbl for lbl, val in SUB_LANG_PRESETS}

COOKIE_BROWSERS = [
    ("None", "none"),
    ("Firefox (Recommended)", "firefox"),
    ("Chrome", "chrome"),
    ("Edge", "edge"),
    ("Brave", "brave"),
    ("Opera", "opera"),
    ("Vivaldi", "vivaldi"),
]
COOKIE_LABEL_TO_VAL = {lbl: val for lbl, val in COOKIE_BROWSERS}
COOKIE_VAL_TO_LABEL = {val: lbl for lbl, val in COOKIE_BROWSERS}

VIDEO_FORMATS = [
    (
        "mp4",
        "MP4 (Standard)",
        "MP4 (MPEG-4 Part 14)\n\n"
        "• Best all-around video format.\n"
        "• Plays on almost every phone, TV, tablet, web browser, and video editor.\n"
        "• Merges video and audio cleanly into an .mp4 container.",
    ),
    (
        "mkv",
        "MKV (High Quality)",
        "MKV (Matroska Video)\n\n"
        "• Flexible container that stores the highest quality video (VP9/AV1 4K) and Opus audio without re-encoding.\n"
        "• Ideal for watching on PC (VLC, MPV), though some mobile devices may not open it natively.",
    ),
    (
        "webm",
        "WebM (Original)",
        "WebM\n\n"
        "• YouTube's native streaming format.\n"
        "• Downloads directly without converting or repackaging, preserving original quality.\n"
        "• Works in modern web browsers and PC media players.",
    ),
    (
        "mov",
        "MOV (Editing)",
        "MOV (Apple QuickTime Container)\n\n"
        "• Repackages the video into a QuickTime .mov container.\n"
        "• Useful if you plan to import the clip directly into video editing software.",
    ),
]

AUDIO_FORMATS = [
    (
        "mp3",
        "MP3 (Standard)",
        "MP3 (MPEG Audio Layer III)\n\n"
        "• The most universal music format.\n"
        "• Compatible with every music player, phone, car stereo, and speaker.\n"
        "• Slightly compresses audio to keep file sizes small.",
    ),
    (
        "m4a",
        "M4A (AAC)",
        "M4A (Advanced Audio Coding)\n\n"
        "• Often downloaded directly from the source without needing lossy re-conversion.\n"
        "• Delivers slightly cleaner sound than MP3 at the same file size.",
    ),
    (
        "wav",
        "WAV (Uncompressed)",
        "WAV (Waveform Audio File Format)\n\n"
        "• Uncompressed raw audio.\n"
        "• Produces large files, ideal for importing into audio or video editing software.",
    ),
    (
        "flac",
        "FLAC (Lossless)",
        "FLAC (Free Lossless Audio Codec)\n\n"
        "• Compresses audio with zero quality loss compared to WAV.\n"
        "• Supports full album art and metadata tags at roughly half the size of WAV.",
    ),
    (
        "opus",
        "Opus",
        "Opus Audio\n\n"
        "• YouTube's highest-quality native audio stream.\n"
        "• Offers excellent sound fidelity at small file sizes.",
    ),
    (
        "orig",
        "Original (No Conversion)",
        "Original Audio Stream\n\n"
        "• Saves the raw audio file (.webm or .m4a) straight from the server without converting it.\n"
        "• Fastest download speed and zero conversion quality loss.",
    ),
]

EXTRA_HELP = {
    "quality": (
        "Strict Resolution & Custom Scaling\n\n"
        "• Auto (Best): Downloads the highest available video quality.\n"
        "• Preset (e.g., 1080p): Forces yt-dlp to select that exact resolution stream (supports both landscape and vertical videos).\n"
        "• Custom Resolution: Downloads the best stream and rescales it via FFmpeg to your exact height (e.g., 540) or dimensions (e.g., 1280x720)."
    ),
    "custom_title": (
        "Custom File Title\n\n"
        "• Leave blank to keep the video's original title.\n"
        "• Always resets to empty when the app starts so you don't accidentally overwrite future downloads."
    ),
    "remove_links": (
        "Remove Links from Titles\n\n"
        "• Automatically strips http:// and https:// URLs out of video titles (very useful for Twitter/X, TikTok, and Instagram posts)."
    ),
    "playlist_folder": (
        "Playlist Folder\n\n"
        "• Automatically creates a subfolder when downloading a playlist (never creates a folder for single videos or tracks).\n"
        "• Leave the folder name box blank to use the playlist's real title, or type a custom folder name."
    ),
    "playlist_numbers": (
        "Order Playlist with Numbers\n\n"
        "• Adds the track/video number in front of playlist filenames (e.g., '1 - Song Title.mp3', '2 - Song Title.mp3').\n"
        "• Has no effect when downloading a single video or song."
    ),
    "meta": (
        "Cover Art & Media Info\n\n"
        "• Embeds the video thumbnail as the song/video cover image.\n"
        "• Writes the title, artist/channel name, upload date, and description into the file tags."
    ),
    "subtitles": (
        "Include Subtitles & Language\n\n"
        "• Downloads and embeds available subtitles (including auto-generated captions) directly into video files.\n"
        "• Pick a language preset or choose Custom and enter comma-separated language codes (e.g., en,id,ja,ko)."
    ),
    "cookies": (
        "Browser Cookies (Preview & Download)\n\n"
        "• Reads your browser's active login session so yt-dlp can access Instagram login-walled posts, age-restricted videos, and private playlists.\n"
        "• Also helps bypass YouTube bot checks.\n"
        "• Note: Firefox works seamlessly while open. Chrome/Edge/Brave lock cookies while running on Windows, so close them briefly if you see a cookie database error."
    ),
}


def sanitize_filename(name):
    """Removes invalid Windows filename characters and yt-dlp template tokens."""
    cleaned = re.sub(r'[<>:"/\\|?*]', "", name).strip()
    return cleaned.replace("%", "%%").replace("{", "{{").replace("}", "}}")


def _json_unquote(raw):
    try:
        val = json.loads(raw)
        return "" if val is None else str(val)
    except Exception:
        return raw


def _alnum_key(text):
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


# ============================================================================
# NATIVE WINDOWS AUDIO PLAYER (winmm.dll - Zero External Dependencies)
# ============================================================================
class WAVEFORMATEX(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("wFormatTag", ctypes.c_uint16),
        ("nChannels", ctypes.c_uint16),
        ("nSamplesPerSec", ctypes.c_uint32),
        ("nAvgBytesPerSec", ctypes.c_uint32),
        ("nBlockAlign", ctypes.c_uint16),
        ("wBitsPerSample", ctypes.c_uint16),
        ("cbSize", ctypes.c_uint16),
    ]


class WAVEHDR(ctypes.Structure):
    _fields_ = [
        ("lpData", ctypes.c_void_p),
        ("dwBufferLength", ctypes.c_uint32),
        ("dwBytesRecorded", ctypes.c_uint32),
        ("dwUser", ctypes.c_size_t),
        ("dwFlags", ctypes.c_uint32),
        ("dwLoops", ctypes.c_uint32),
        ("lpNext", ctypes.c_void_p),
        ("reserved", ctypes.c_size_t),
    ]


class WaveOutPlayer:
    """Streams 16-bit 44.1kHz stereo PCM to Windows WaveOut with instant volume control."""

    WHDR_DONE = 0x00000001
    WHDR_PREPARED = 0x00000002

    def __init__(self, sample_rate=44100, channels=2, num_buffers=8):
        self.sample_rate = sample_rate
        self.channels = channels
        self.num_buffers = num_buffers
        self.h_wave = None
        self.lock = threading.Lock()
        self.volume = 0.7
        self.active = False
        self.slots = []
        self._winmm = None

        if os.name == "nt":
            try:
                w = ctypes.windll.winmm
                w.waveOutOpen.argtypes = [
                    ctypes.POINTER(ctypes.c_void_p),
                    ctypes.c_uint,
                    ctypes.POINTER(WAVEFORMATEX),
                    ctypes.c_size_t,
                    ctypes.c_size_t,
                    ctypes.c_uint,
                ]
                w.waveOutOpen.restype = ctypes.c_uint
                w.waveOutPrepareHeader.argtypes = [ctypes.c_void_p, ctypes.POINTER(WAVEHDR), ctypes.c_uint]
                w.waveOutPrepareHeader.restype = ctypes.c_uint
                w.waveOutWrite.argtypes = [ctypes.c_void_p, ctypes.POINTER(WAVEHDR), ctypes.c_uint]
                w.waveOutWrite.restype = ctypes.c_uint
                w.waveOutUnprepareHeader.argtypes = [ctypes.c_void_p, ctypes.POINTER(WAVEHDR), ctypes.c_uint]
                w.waveOutUnprepareHeader.restype = ctypes.c_uint
                w.waveOutReset.argtypes = [ctypes.c_void_p]
                w.waveOutReset.restype = ctypes.c_uint
                w.waveOutClose.argtypes = [ctypes.c_void_p]
                w.waveOutClose.restype = ctypes.c_uint
                w.waveOutSetVolume.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
                w.waveOutSetVolume.restype = ctypes.c_uint
                self._winmm = w
            except Exception:
                self._winmm = None

    def open(self):
        if not self._winmm:
            return False
        self.stop()
        with self.lock:
            wfx = WAVEFORMATEX(
                wFormatTag=1,
                nChannels=self.channels,
                nSamplesPerSec=self.sample_rate,
                nAvgBytesPerSec=self.sample_rate * self.channels * 2,
                nBlockAlign=self.channels * 2,
                wBitsPerSample=16,
                cbSize=0,
            )
            h = ctypes.c_void_p()
            res = self._winmm.waveOutOpen(ctypes.byref(h), 0xFFFFFFFF, ctypes.byref(wfx), 0, 0, 0)
            if res != 0:
                return False
            self.h_wave = h
            self.active = True
            self.slots = [[None, None, False] for _ in range(self.num_buffers)]
            self._apply_volume_locked()
            return True

    def set_volume(self, vol_float):
        self.volume = max(0.0, min(1.0, float(vol_float)))
        with self.lock:
            self._apply_volume_locked()

    def _apply_volume_locked(self):
        if self._winmm and self.h_wave:
            v = int(self.volume * 0xFFFF)
            dw = (v << 16) | v
            try:
                self._winmm.waveOutSetVolume(self.h_wave, dw)
            except Exception:
                pass

    def write(self, data_bytes):
        if not self._winmm or not self.active or not data_bytes:
            return False
        while self.active:
            with self.lock:
                if not self.active or not self.h_wave:
                    return False
                for slot in self.slots:
                    hdr, buf, in_use = slot
                    if not in_use or (hdr and (hdr.dwFlags & self.WHDR_DONE)):
                        if hdr and (hdr.dwFlags & self.WHDR_PREPARED):
                            self._winmm.waveOutUnprepareHeader(
                                self.h_wave, ctypes.byref(hdr), ctypes.sizeof(WAVEHDR)
                            )
                        new_buf = ctypes.create_string_buffer(data_bytes, len(data_bytes))
                        new_hdr = WAVEHDR(
                            lpData=ctypes.cast(new_buf, ctypes.c_void_p).value,
                            dwBufferLength=len(data_bytes),
                            dwFlags=0,
                        )
                        self._winmm.waveOutPrepareHeader(
                            self.h_wave, ctypes.byref(new_hdr), ctypes.sizeof(WAVEHDR)
                        )
                        self._winmm.waveOutWrite(
                            self.h_wave, ctypes.byref(new_hdr), ctypes.sizeof(WAVEHDR)
                        )
                        slot[0] = new_hdr
                        slot[1] = new_buf
                        slot[2] = True
                        return True
            time.sleep(0.01)
        return False

    def stop(self):
        self.active = False
        if not self._winmm:
            return
        with self.lock:
            if self.h_wave:
                try:
                    self._winmm.waveOutReset(self.h_wave)
                    for hdr, _, _ in self.slots:
                        if hdr and (hdr.dwFlags & self.WHDR_PREPARED):
                            self._winmm.waveOutUnprepareHeader(
                                self.h_wave, ctypes.byref(hdr), ctypes.sizeof(WAVEHDR)
                            )
                    self._winmm.waveOutClose(self.h_wave)
                except Exception:
                    pass
                self.h_wave = None
                self.slots = []


# ============================================================================
# CUSTOM MODERN UI WIDGETS
# ============================================================================
class ModernSlider(tk.Canvas):
    """Sleek flat media slider with filled progress bar, circular thumb, and click-to-seek."""

    def __init__(
        self,
        master,
        from_=0.0,
        to=100.0,
        value=0.0,
        height=22,
        on_start=None,
        on_move=None,
        on_end=None,
        **kwargs,
    ):
        super().__init__(master, height=height, highlightthickness=0, bd=0, cursor="hand2", **kwargs)
        self.from_ = float(from_)
        self.to = float(to)
        self._value = float(value)
        self.on_start = on_start
        self.on_move = on_move
        self.on_end = on_end

        self.bg_color = "#18181b"
        self.track_color = "#3f3f46"
        self.fill_color = "#3b82f6"
        self.thumb_color = "#ffffff"
        self.thumb_hover = "#93c5fd"
        self._hover = False
        self._dragging = False
        self._pad = 9

        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)

    def set_theme(self, bg, track, fill, thumb):
        self.bg_color = bg
        self.track_color = track
        self.fill_color = fill
        self.thumb_color = thumb
        self.configure(bg=bg)
        self.redraw()

    def set_range(self, from_, to):
        self.from_ = float(from_)
        self.to = max(self.from_ + 0.001, float(to))
        self.redraw()

    def set(self, val):
        self._value = max(self.from_, min(self.to, float(val)))
        self.redraw()

    def get(self):
        return self._value

    def _x_to_val(self, x):
        w = max(1, self.winfo_width() - 2 * self._pad)
        ratio = max(0.0, min(1.0, (x - self._pad) / w))
        return self.from_ + ratio * (self.to - self.from_)

    def _on_enter(self, event):
        self._hover = True
        self.redraw()

    def _on_leave(self, event):
        self._hover = False
        self.redraw()

    def _on_press(self, event):
        self._dragging = True
        self._value = self._x_to_val(event.x)
        self.redraw()
        if self.on_start:
            self.on_start(self._value)
        if self.on_move:
            self.on_move(self._value)

    def _on_drag(self, event):
        if not self._dragging:
            return
        self._value = self._x_to_val(event.x)
        self.redraw()
        if self.on_move:
            self.on_move(self._value)

    def _on_release(self, event):
        if not self._dragging:
            return
        self._dragging = False
        self._value = self._x_to_val(event.x)
        self.redraw()
        if self.on_end:
            self.on_end(self._value)

    def redraw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 4 or h <= 4:
            return

        cy = h / 2
        x0 = self._pad
        x1 = max(x0 + 1, w - self._pad)
        ratio = (self._value - self.from_) / max(0.001, self.to - self.from_)
        kx = x0 + ratio * (x1 - x0)

        self.create_line(x0, cy, x1, cy, fill=self.track_color, width=5, capstyle="round")
        if kx > x0 + 1:
            self.create_line(x0, cy, kx, cy, fill=self.fill_color, width=5, capstyle="round")

        r = 7 if (self._hover or self._dragging) else 6
        knob_fill = self.thumb_hover if self._dragging else self.thumb_color
        self.create_oval(
            kx - r, cy - r, kx + r, cy + r, fill=knob_fill, outline=self.fill_color, width=2
        )


class HelpBadge(tk.Label):
    """A (?) badge that displays a floating tooltip on hover and a dialog on click."""

    def __init__(self, master, title, description, app_ref):
        super().__init__(
            master,
            text="(?)",
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
            padx=2,
            pady=0,
        )
        self.title = title
        self.description = description
        self.app_ref = app_ref
        self.tip_win = None

        self.bind("<Enter>", self.show_tip)
        self.bind("<Leave>", self.hide_tip)
        self.bind("<Button-1>", self.show_dialog)
        self.update_colors()

    def update_colors(self):
        is_dark = self.app_ref.get_target_dark_state()
        bg = "#18181b" if is_dark else "#f4f4f5"
        fg = "#60a5fa" if is_dark else "#2563eb"
        self.configure(bg=bg, fg=fg)

    def show_tip(self, event=None):
        if self.tip_win:
            return
        is_dark = self.app_ref.get_target_dark_state()
        tip_bg = "#27272a" if is_dark else "#ffffff"
        tip_fg = "#f4f4f5" if is_dark else "#18181b"
        border = "#52525b" if is_dark else "#a1a1aa"

        x = self.winfo_rootx() + 18
        y = self.winfo_rooty() + 20

        self.tip_win = tw = tk.Toplevel(self)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)

        frame = tk.Frame(tw, bg=tip_bg, highlightbackground=border, highlightthickness=1, padx=10, pady=8)
        frame.pack()

        tk.Label(
            frame,
            text=self.description,
            justify="left",
            bg=tip_bg,
            fg=tip_fg,
            font=("Segoe UI", 9),
            wraplength=340,
        ).pack()

    def hide_tip(self, event=None):
        if self.tip_win:
            self.tip_win.destroy()
            self.tip_win = None

    def show_dialog(self, event=None):
        self.hide_tip()
        messagebox.showinfo(f"About {self.title}", self.description)


class WrapFrame(ttk.Frame):
    """A container that automatically wraps child widgets onto new rows when space runs out."""

    def __init__(self, master=None, padx=6, pady=3, **kwargs):
        super().__init__(master, **kwargs)
        self.padx = padx
        self.pady = pady
        self.bind("<Configure>", self.rearrange)

    def rearrange(self, event=None):
        width = self.winfo_width()
        if width <= 1:
            return
        x = 0
        y = self.pady
        row_h = 0
        for child in self.winfo_children():
            cw = child.winfo_reqwidth()
            ch = child.winfo_reqheight()
            if x > 0 and x + cw + self.padx > width:
                x = 0
                y += row_h + self.pady * 2
                row_h = 0
            child.place(x=x, y=y)
            x += cw + self.padx * 2
            if ch > row_h:
                row_h = ch
        total_h = max(26, y + row_h + self.pady)
        if self.winfo_height() != total_h:
            self.configure(height=total_h)


# ============================================================================
# MAIN APPLICATION
# ============================================================================
class YtDlpApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("yt-dlp Downloader")
        self.geometry("740x830")
        self.minsize(540, 620)
        self.resizable(True, True)

        # Apply custom .ico if available
        try:
            if os.path.exists(ICON_PATH):
                self.iconbitmap(ICON_PATH)
            elif getattr(sys, "frozen", False):
                self.iconbitmap(sys.executable)
        except Exception:
            pass

        # Downloader Variables (Saved Options)
        self.url_var = tk.StringVar()
        self.save_dir_var = tk.StringVar(value=DEFAULT_SAVE_DIR)
        self.media_type = tk.StringVar(value="video")
        self.video_fmt = tk.StringVar(value="mp4")
        self.audio_fmt = tk.StringVar(value="mp3")
        self.quality_label_var = tk.StringVar(value="Auto (Best)")
        self.range_choice = tk.StringVar(value="1")

        # Non-Saved Defaults (Always reset on app launch)
        self.custom_title_var = tk.StringVar(value="")
        self.use_custom_res_var = tk.BooleanVar(value=False)
        self.custom_res_var = tk.StringVar(value="")
        self.playlist_folder_var = tk.BooleanVar(value=True)
        self.custom_playlist_folder_var = tk.StringVar(value="")

        # Saved Naming, Subtitles & Cookies Options
        self.remove_link_title_var = tk.BooleanVar(value=False)
        self.playlist_numbering_var = tk.BooleanVar(value=False)
        self.meta_var = tk.BooleanVar(value=False)
        self.subs_var = tk.BooleanVar(value=False)
        self.sub_lang_label_var = tk.StringVar(value="English (en)")
        self.custom_sub_lang_var = tk.StringVar(value="en,id")
        self.cookie_browser_label_var = tk.StringVar(value="None")

        # Duration Spinbox Variables (Default: 00:01:00 to 00:02:00)
        self.sh_var = tk.IntVar(value=0)
        self.sm_var = tk.IntVar(value=1)
        self.ss_var = tk.IntVar(value=0)
        self.eh_var = tk.IntVar(value=0)
        self.em_var = tk.IntVar(value=2)
        self.es_var = tk.IntVar(value=0)

        # Playlist Index Range Variables
        self.use_p_start = tk.BooleanVar(value=True)
        self.p_start_var = tk.IntVar(value=1)
        self.use_p_end = tk.BooleanVar(value=True)
        self.p_end_var = tk.IntVar(value=5)

        # Settings & Version Variables
        self.theme_mode = tk.StringVar(value="system")
        self.version_var = tk.StringVar(value="yt-dlp version: Checking...")
        self.app_ver_var = tk.StringVar(value=f"App Version: v{APP_VERSION}")

        # Download Process & Queue State
        self.download_queue = []
        self.is_downloading = False
        self.cancel_requested = False
        self.active_dl_proc = None

        # Preview Engine State
        self.wave_player = WaveOutPlayer()
        self.preview_video_proc = None
        self.preview_audio_proc = None
        self.preview_playing = False
        self.preview_video_url = None
        self.preview_audio_url = None
        self.preview_headers = {}
        self.preview_has_video = False
        self.preview_duration = 0.0
        self.preview_pos = 0.0
        self.preview_seeking = False
        self.preview_photo = None
        self.preview_session_id = 0
        self.preview_muted = False
        self.preview_volume = 0.7

        self._pending_cr = False
        self._applied_dark_state = None
        self.help_badges = []
        self.cleaned_logs = []
        self.history_items = []

        self.load_settings()
        self.load_history()
        self.cleanup_redundant_local_binaries()
        self.build_ui()
        self.refresh_format_options()
        self.update_quality_controls()
        self.update_subtitle_controls()
        self.update_playlist_folder_controls()
        self.update_scope_visibility()
        self.refresh_queue_ui()
        self.refresh_history_tree()
        self.apply_theme(force=True)
        self.poll_system_theme()
        self.after(300, self.check_ytdlp_version)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def cleanup_redundant_local_binaries(self):
        for exe_name in ("ffmpeg.exe", "ffprobe.exe", "node.exe"):
            global_path = find_global_binary(exe_name)
            local_path = os.path.join(APP_DIR, exe_name)
            if global_path and os.path.isfile(local_path):
                try:
                    os.remove(local_path)
                    self.cleaned_logs.append(
                        f"Removed local {exe_name} from App Folder (using Global PATH: {global_path})"
                    )
                except OSError as e:
                    self.cleaned_logs.append(f"Could not remove local {exe_name} ({e})")

    def make_help_badge(self, parent, title, description):
        badge = HelpBadge(parent, title, description, self)
        self.help_badges.append(badge)
        return badge

    def build_ui(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self.dl_tab_outer = ttk.Frame(self.notebook)
        self.history_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.dl_tab_outer, text="  Downloader  ")
        self.notebook.add(self.history_tab, text="  History  ")
        self.notebook.add(self.settings_tab, text="  Settings & Updates  ")

        self.build_downloader_tab()
        self.build_history_tab()
        self.build_settings_tab()

        self.bind_all("<MouseWheel>", self._on_global_mousewheel)

    def _on_global_mousewheel(self, event):
        if self.notebook.index(self.notebook.select()) != 0:
            return
        w = event.widget
        if isinstance(w, (tk.Text, tk.Listbox, ttk.Spinbox, ttk.Combobox, ttk.Treeview)):
            return
        self.dl_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def build_downloader_tab(self):
        # Scrollable Viewport for Downloader Tab
        self.dl_canvas = tk.Canvas(self.dl_tab_outer, highlightthickness=0, bd=0)
        self.dl_vscroll = ttk.Scrollbar(
            self.dl_tab_outer, orient="vertical", command=self.dl_canvas.yview
        )
        self.dl_canvas.configure(yscrollcommand=self.dl_vscroll.set)

        self.dl_vscroll.pack(side="right", fill="y")
        self.dl_canvas.pack(side="left", fill="both", expand=True)

        self.dl_tab = ttk.Frame(self.dl_canvas)
        self.dl_canvas_window = self.dl_canvas.create_window((0, 0), window=self.dl_tab, anchor="nw")

        self.dl_tab.bind(
            "<Configure>",
            lambda e: self.dl_canvas.configure(scrollregion=self.dl_canvas.bbox("all")),
        )
        self.dl_canvas.bind(
            "<Configure>",
            lambda e: self.dl_canvas.itemconfig(self.dl_canvas_window, width=e.width),
        )

        pad = {"padx": 10, "pady": 4}

        # 1. Link, Queue & Preview Section
        self.url_frame = ttk.LabelFrame(self.dl_tab, text="1. Video or Playlist Link")
        self.url_frame.pack(fill="x", **pad)

        url_top_row = ttk.Frame(self.url_frame)
        url_top_row.pack(fill="x")

        self.url_entry = ttk.Entry(url_top_row, textvariable=self.url_var, font=("Segoe UI", 10))
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(8, 4), pady=7)

        ttk.Button(url_top_row, text="Paste", width=6, command=self.paste_url).pack(side="left", padx=2, pady=7)
        ttk.Button(url_top_row, text="+ Queue", width=8, command=self.add_to_queue).pack(side="left", padx=2, pady=7)
        ttk.Button(url_top_row, text="Clear", width=6, command=self.clear_url).pack(side="left", padx=2, pady=7)
        self.preview_btn = ttk.Button(url_top_row, text="Preview", width=8, command=self.start_preview)
        self.preview_btn.pack(side="left", padx=(2, 8), pady=7)

        # Batch Queue Box (Auto-shows when 1 or more links are queued)
        self.queue_frame = ttk.Frame(self.url_frame)
        q_head = ttk.Frame(self.queue_frame)
        q_head.pack(fill="x", padx=8, pady=(0, 3))
        self.queue_lbl = ttk.Label(q_head, text="Download Queue (0):", font=("Segoe UI", 9, "bold"))
        self.queue_lbl.pack(side="left")
        ttk.Button(q_head, text="Clear Queue", width=11, command=self.clear_queue).pack(side="right", padx=(4, 0))
        ttk.Button(q_head, text="Remove", width=8, command=self.remove_selected_queue).pack(side="right", padx=2)
        ttk.Button(q_head, text="Paste Multi-Links", width=15, command=self.paste_multiple_to_queue).pack(side="right", padx=2)

        q_list_wrap = ttk.Frame(self.queue_frame)
        q_list_wrap.pack(fill="x", padx=8, pady=(0, 6))
        q_scroll = ttk.Scrollbar(q_list_wrap, orient="vertical")
        q_scroll.pack(side="right", fill="y")
        self.queue_listbox = tk.Listbox(
            q_list_wrap,
            height=4,
            font=("Consolas", 9),
            yscrollcommand=q_scroll.set,
            selectmode="extended",
            relief="flat",
            highlightthickness=1,
        )
        self.queue_listbox.pack(side="left", fill="x", expand=True)
        q_scroll.config(command=self.queue_listbox.yview)

        # Collapsible Preview Box
        self.preview_box = ttk.Frame(self.url_frame)

        self.preview_header = ttk.Frame(self.preview_box)
        self.preview_header.pack(fill="x", padx=8, pady=(0, 4))
        self.preview_title_lbl = ttk.Label(
            self.preview_header, text="", font=("Segoe UI", 9, "bold"), wraplength=500
        )
        self.preview_title_lbl.pack(side="left", fill="x", expand=True)
        ttk.Button(self.preview_header, text="Close Preview", width=13, command=self.close_preview).pack(side="right")

        # Loading Progressbar
        self.preview_loading_frame = ttk.Frame(self.preview_box)
        self.preview_loading_lbl = ttk.Label(
            self.preview_loading_frame, text="Loading preview...", font=("Segoe UI", 9)
        )
        self.preview_loading_lbl.pack(pady=(4, 4))
        self.preview_progress = ttk.Progressbar(
            self.preview_loading_frame, mode="indeterminate", length=280
        )
        self.preview_progress.pack(pady=(0, 8))

        # Status / Error Message Label
        self.preview_msg_lbl = ttk.Label(
            self.preview_box, text="", font=("Segoe UI", 9), justify="center", anchor="center", wraplength=560
        )

        # Media Player Area (Video Canvas or Album Cover + Modern Slider + Volume + Clip Markers)
        self.preview_player_frame = ttk.Frame(self.preview_box)

        self.video_canvas_lbl = tk.Label(
            self.preview_player_frame, bg="#000000", width=PREVIEW_W, height=PREVIEW_H
        )
        self.video_canvas_lbl.pack(pady=(2, 4))

        # Row 1: Play/Pause + Modern Progress Slider + Timestamp
        ctrl_row1 = ttk.Frame(self.preview_player_frame)
        ctrl_row1.pack(fill="x", padx=12, pady=(0, 2))

        self.play_pause_btn = ttk.Button(
            ctrl_row1, text="Pause", width=7, command=self.toggle_preview_play
        )
        self.play_pause_btn.pack(side="left", padx=(0, 8))

        self.preview_slider = ModernSlider(
            ctrl_row1,
            from_=0.0,
            to=100.0,
            value=0.0,
            height=22,
            on_start=self.on_preview_scrub_start,
            on_move=self.on_preview_scrub_move,
            on_end=self.on_preview_scrub_end,
        )
        self.preview_slider.pack(side="left", fill="x", expand=True, padx=4)

        self.preview_time_lbl = ttk.Label(ctrl_row1, text="00:00 / 00:00", font=("Consolas", 9))
        self.preview_time_lbl.pack(side="left", padx=(8, 0))

        # Row 2: Volume + Clip Start/End Marker Buttons
        ctrl_row2 = ttk.Frame(self.preview_player_frame)
        ctrl_row2.pack(fill="x", padx=12, pady=(0, 6))

        self.mute_btn = ttk.Button(ctrl_row2, text="Vol:", width=6, command=self.toggle_mute)
        self.mute_btn.pack(side="left", padx=(0, 4))

        self.vol_slider = ModernSlider(
            ctrl_row2,
            from_=0.0,
            to=100.0,
            value=70.0,
            height=20,
            width=120,
            on_move=self.on_volume_change,
            on_end=self.on_volume_change,
        )
        self.vol_slider.pack(side="left", padx=4)

        self.vol_pct_lbl = ttk.Label(ctrl_row2, text="70%", font=("Consolas", 9), width=4)
        self.vol_pct_lbl.pack(side="left", padx=(2, 10))

        ttk.Button(
            ctrl_row2, text="Set Clip Start", width=13, command=lambda: self.set_clip_marker(True)
        ).pack(side="left", padx=2)
        ttk.Button(
            ctrl_row2, text="Set Clip End", width=12, command=lambda: self.set_clip_marker(False)
        ).pack(side="left", padx=2)

        self.preview_mode_badge = ttk.Label(ctrl_row2, text="", font=("Segoe UI", 8))
        self.preview_mode_badge.pack(side="right")

        # 2. Media Type & Format Section
        type_frame = ttk.LabelFrame(self.dl_tab, text="2. Type & File Format  (Hover or click (?) for details)")
        type_frame.pack(fill="x", **pad)

        step1_row = WrapFrame(type_frame, padx=6, pady=2)
        step1_row.pack(fill="x", padx=8, pady=(4, 2))
        ttk.Label(step1_row, text="Download as:", font=("Segoe UI", 9, "bold"))
        ttk.Radiobutton(
            step1_row, text="Video", value="video", variable=self.media_type, command=self.on_media_type_change
        )
        ttk.Radiobutton(
            step1_row, text="Audio Only", value="audio", variable=self.media_type, command=self.on_media_type_change
        )

        self.fmt_options_frame = WrapFrame(type_frame, padx=6, pady=3)
        self.fmt_options_frame.pack(fill="x", padx=8, pady=(2, 6))

        # 3. Video Quality Section
        self.qual_frame = ttk.LabelFrame(self.dl_tab, text="3. Video Quality (Forces Selected Resolution)")
        self.qual_frame.pack(fill="x", **pad)

        qual_row = WrapFrame(self.qual_frame, padx=6, pady=4)
        qual_row.pack(fill="x", padx=8, pady=5)

        ttk.Label(qual_row, text="Resolution:", font=("Segoe UI", 9, "bold"))
        self.quality_combo = ttk.Combobox(
            qual_row,
            textvariable=self.quality_label_var,
            values=[lbl for lbl, _ in QUALITY_PRESETS],
            state="readonly",
            width=15,
        )
        self.quality_combo.bind("<<ComboboxSelected>>", lambda e: self.save_settings())

        self.custom_res_chk = ttk.Checkbutton(
            qual_row,
            text="Custom Resolution:",
            variable=self.use_custom_res_var,
            command=self.update_quality_controls,
        )
        self.custom_res_entry = ttk.Entry(qual_row, textvariable=self.custom_res_var, width=13)
        ttk.Label(qual_row, text="(e.g. 540 or 1280x720)")
        self.make_help_badge(qual_row, "Video Quality", EXTRA_HELP["quality"])

        # 4. What to Download (Scope)
        scope_frame = ttk.LabelFrame(self.dl_tab, text="4. What to Download")
        scope_frame.pack(fill="x", **pad)

        scopes = [
            ("1", "Full video or full playlist"),
            ("2", "Cut a time clip (Start to End)"),
            ("3", "Pick specific playlist videos"),
        ]
        for val, label in scopes:
            ttk.Radiobutton(
                scope_frame, text=label, value=val, variable=self.range_choice, command=self.on_scope_change
            ).pack(anchor="w", padx=10, pady=2)

        # Sub-panel: Duration Spinboxes (Default 00:01:00 to 00:02:00)
        self.dur_panel = WrapFrame(scope_frame, padx=3, pady=3)
        ttk.Label(self.dur_panel, text="From (H:M:S):")
        self._make_spinbox(self.dur_panel, self.sh_var, 23)
        self._make_spinbox(self.dur_panel, self.sm_var, 59)
        self._make_spinbox(self.dur_panel, self.ss_var, 59)
        ttk.Label(self.dur_panel, text="   To (H:M:S):")
        self._make_spinbox(self.dur_panel, self.eh_var, 23)
        self._make_spinbox(self.dur_panel, self.em_var, 59)
        self._make_spinbox(self.dur_panel, self.es_var, 59)

        # Sub-panel: Playlist Index Range Controls
        self.play_panel = ttk.Frame(scope_frame)
        row_p = WrapFrame(self.play_panel, padx=4, pady=2)
        row_p.pack(fill="x", padx=20, pady=2)

        ttk.Checkbutton(row_p, text="Start at video #:", variable=self.use_p_start, command=self.save_settings)
        self._make_spinbox(row_p, self.p_start_var, 999, from_=1, width=4)
        ttk.Checkbutton(row_p, text="   Stop at video #:", variable=self.use_p_end, command=self.save_settings)
        self._make_spinbox(row_p, self.p_end_var, 999, from_=1, width=4)

        # 5. Naming & Playlist Organization Section
        name_frame = ttk.LabelFrame(self.dl_tab, text="5. Naming & Playlist Folders")
        name_frame.pack(fill="x", **pad)

        title_row = ttk.Frame(name_frame)
        title_row.pack(fill="x", padx=10, pady=(6, 3))
        ttk.Label(title_row, text="Custom Title (optional):").pack(side="left")
        ttk.Entry(title_row, textvariable=self.custom_title_var).pack(side="left", fill="x", expand=True, padx=6)
        self.make_help_badge(title_row, "Custom Title", EXTRA_HELP["custom_title"]).pack(side="left")

        link_row = ttk.Frame(name_frame)
        link_row.pack(anchor="w", padx=10, pady=2)
        ttk.Checkbutton(
            link_row,
            text="Remove URLs/links from video titles",
            variable=self.remove_link_title_var,
            command=self.save_settings,
        ).pack(side="left")
        self.make_help_badge(link_row, "Remove Links from Titles", EXTRA_HELP["remove_links"]).pack(side="left", padx=4)

        pl_folder_row = ttk.Frame(name_frame)
        pl_folder_row.pack(fill="x", padx=10, pady=2)
        ttk.Checkbutton(
            pl_folder_row,
            text="Create folder for playlists (ignored for single files):",
            variable=self.playlist_folder_var,
            command=self.update_playlist_folder_controls,
        ).pack(side="left")
        self.custom_pl_entry = ttk.Entry(pl_folder_row, textvariable=self.custom_playlist_folder_var, width=20)
        self.custom_pl_entry.pack(side="left", fill="x", expand=True, padx=6)
        self.make_help_badge(pl_folder_row, "Playlist Folder", EXTRA_HELP["playlist_folder"]).pack(side="left")

        pl_num_row = ttk.Frame(name_frame)
        pl_num_row.pack(anchor="w", padx=10, pady=(2, 6))
        ttk.Checkbutton(
            pl_num_row,
            text="Order playlist files with numbers (1 - Title, 2 - Title)",
            variable=self.playlist_numbering_var,
            command=self.save_settings,
        ).pack(side="left")
        self.make_help_badge(pl_num_row, "Playlist Numbering", EXTRA_HELP["playlist_numbers"]).pack(side="left", padx=4)

        # 6. Extras, Subtitles, Cookies & Save Folder
        meta_frame = ttk.LabelFrame(self.dl_tab, text="6. Extras, Browser Cookies & Save Folder")
        meta_frame.pack(fill="x", **pad)

        meta_row = ttk.Frame(meta_frame)
        meta_row.pack(anchor="w", padx=10, pady=(4, 2))
        ttk.Checkbutton(
            meta_row,
            text="Include cover art & media info",
            variable=self.meta_var,
            command=self.save_settings,
        ).pack(side="left")
        self.make_help_badge(meta_row, "Cover Art & Media Info", EXTRA_HELP["meta"]).pack(side="left", padx=4)

        # Subtitles + Language Dropdown Row
        subs_row = WrapFrame(meta_frame, padx=5, pady=2)
        subs_row.pack(fill="x", padx=8, pady=2)
        self.subs_chk = ttk.Checkbutton(
            subs_row,
            text="Include subtitles:",
            variable=self.subs_var,
            command=self.on_subs_toggle,
        )
        self.sub_lang_combo = ttk.Combobox(
            subs_row,
            textvariable=self.sub_lang_label_var,
            values=[lbl for lbl, _ in SUB_LANG_PRESETS],
            state="readonly",
            width=19,
        )
        self.sub_lang_combo.bind("<<ComboboxSelected>>", self.on_sub_lang_change)
        self.custom_sub_entry = ttk.Entry(subs_row, textvariable=self.custom_sub_lang_var, width=12)
        self.custom_sub_entry.bind("<FocusOut>", lambda e: self.save_settings())
        self.make_help_badge(subs_row, "Subtitles", EXTRA_HELP["subtitles"])

        # Browser Cookies Row (Used for BOTH Preview and Download)
        cookie_row = WrapFrame(meta_frame, padx=5, pady=2)
        cookie_row.pack(fill="x", padx=8, pady=2)
        ttk.Label(cookie_row, text="Browser Cookies (Preview & Download):", font=("Segoe UI", 9))
        self.cookie_combo = ttk.Combobox(
            cookie_row,
            textvariable=self.cookie_browser_label_var,
            values=[lbl for lbl, _ in COOKIE_BROWSERS],
            state="readonly",
            width=21,
        )
        self.cookie_combo.bind("<<ComboboxSelected>>", lambda e: self.save_settings())
        self.make_help_badge(cookie_row, "Browser Cookies", EXTRA_HELP["cookies"])

        # Save Directory Row
        dir_row = ttk.Frame(meta_frame)
        dir_row.pack(fill="x", padx=10, pady=(4, 7))
        ttk.Label(dir_row, text="Save to:").pack(side="left")
        ttk.Entry(dir_row, textvariable=self.save_dir_var, state="readonly").pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(dir_row, text="Change...", command=self.browse_dir).pack(side="left", padx=(0, 4))
        ttk.Button(dir_row, text="Open Folder", command=self.open_save_dir).pack(side="left")

        # 7. Action Button (Swaps between Download and Stop/Cancel)
        btn_frame = ttk.Frame(self.dl_tab)
        btn_frame.pack(fill="x", padx=10, pady=6)

        self.dl_btn = tk.Button(
            btn_frame,
            text="Download",
            font=("Segoe UI", 11, "bold"),
            bg="#2563eb",
            fg="white",
            activebackground="#1d4ed8",
            activeforeground="white",
            relief="flat",
            height=2,
            command=self.on_download_or_cancel,
        )
        self.dl_btn.pack(fill="x", expand=True)

        # 8. Progress Log (Fixed Clamped Min/Max Height)
        log_frame = ttk.LabelFrame(self.dl_tab, text="Progress Log")
        log_frame.pack(fill="x", **pad)

        self.log_box_container = ttk.Frame(log_frame, height=175)
        self.log_box_container.pack(fill="x", padx=6, pady=6)
        self.log_box_container.pack_propagate(False)

        self.log_scroll = ttk.Scrollbar(self.log_box_container, orient="vertical")
        self.log_scroll.pack(side="right", fill="y")

        self.log_text = tk.Text(
            self.log_box_container,
            font=("Consolas", 9),
            wrap="word",
            yscrollcommand=self.log_scroll.set,
            relief="flat",
            padx=6,
            pady=6,
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        self.log_scroll.config(command=self.log_text.yview)

        self.bind("<Configure>", self._clamp_log_height)

    def _clamp_log_height(self, event=None):
        if event is not None and event.widget is not self:
            return
        target = int(self.winfo_height() * 0.22)
        clamped = max(LOG_MIN_HEIGHT, min(LOG_MAX_HEIGHT, target))
        if self.log_box_container.cget("height") != clamped:
            self.log_box_container.configure(height=clamped)

    # ========================================================================
    # DOWNLOAD QUEUE MANAGEMENT
    # ========================================================================
    def add_to_queue(self):
        raw = self.url_var.get().strip()
        if not raw:
            try:
                raw = self.clipboard_get().strip()
            except tk.TclError:
                raw = ""
        links = [ln.strip().replace('"', "") for ln in raw.splitlines() if ln.strip()]
        if not links:
            messagebox.showwarning("No Link", "Paste or enter a link to add to the queue.")
            return
        added = 0
        for ln in links:
            if ln not in self.download_queue:
                self.download_queue.append(ln)
                added += 1
        self.url_var.set("")
        self.close_preview()
        self.refresh_queue_ui()
        if added == 0:
            messagebox.showinfo("Already Queued", "That link is already in the queue.")

    def paste_multiple_to_queue(self):
        try:
            clip = self.clipboard_get().strip()
        except tk.TclError:
            clip = ""
        links = [ln.strip().replace('"', "") for ln in clip.splitlines() if ln.strip().startswith(("http://", "https://"))]
        if not links:
            messagebox.showwarning("No Links Found", "Copy one or more http/https links (one per line) to your clipboard first.")
            return
        for ln in links:
            if ln not in self.download_queue:
                self.download_queue.append(ln)
        self.refresh_queue_ui()

    def remove_selected_queue(self):
        sel = list(self.queue_listbox.curselection())
        for idx in reversed(sel):
            if 0 <= idx < len(self.download_queue):
                self.download_queue.pop(idx)
        self.refresh_queue_ui()

    def clear_queue(self):
        self.download_queue.clear()
        self.refresh_queue_ui()

    def refresh_queue_ui(self):
        self.queue_listbox.delete(0, "end")
        for i, url in enumerate(self.download_queue, start=1):
            self.queue_listbox.insert("end", f"{i}. {url}")
        count = len(self.download_queue)
        self.queue_lbl.config(text=f"Download Queue ({count}):")
        if count > 0:
            if not self.queue_frame.winfo_ismapped():
                self.queue_frame.pack(fill="x", before=self.preview_box if self.preview_box.winfo_ismapped() else None)
        else:
            self.queue_frame.pack_forget()

    # ========================================================================
    # DOWNLOAD HISTORY TAB + RIGHT-CLICK CONTEXT MENU
    # ========================================================================
    def build_history_tab(self):
        top_bar = ttk.Frame(self.history_tab)
        top_bar.pack(fill="x", padx=12, pady=(10, 6))

        self.hist_count_lbl = ttk.Label(top_bar, text="Downloads: 0", font=("Segoe UI", 10, "bold"))
        self.hist_count_lbl.pack(side="left")

        ttk.Button(top_bar, text="Clear History", command=self.clear_history).pack(side="right", padx=(6, 0))
        ttk.Button(top_bar, text="Open File Location", command=self.open_selected_history_file).pack(side="right", padx=(6, 0))
        ttk.Button(top_bar, text="Open in Browser", command=self.open_selected_history_link).pack(side="right")

        hint_lbl = ttk.Label(
            self.history_tab,
            text="Tip: Click a link to open in browser, or right-click any row to open the downloaded file location.",
            font=("Segoe UI", 8),
        )
        hint_lbl.pack(anchor="w", padx=12, pady=(0, 6))

        tree_frame = ttk.Frame(self.history_tab)
        tree_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        yscroll = ttk.Scrollbar(tree_frame, orient="vertical")
        yscroll.pack(side="right", fill="y")
        xscroll = ttk.Scrollbar(tree_frame, orient="horizontal")
        xscroll.pack(side="bottom", fill="x")

        cols = ("date", "title", "link", "author")
        self.history_tree = ttk.Treeview(
            tree_frame,
            columns=cols,
            show="headings",
            yscrollcommand=yscroll.set,
            xscrollcommand=xscroll.set,
        )
        self.history_tree.heading("date", text="Date & Time")
        self.history_tree.heading("title", text="Original Title")
        self.history_tree.heading("link", text="Link (Click to Open)")
        self.history_tree.heading("author", text="Author / Creator / Artist")

        self.history_tree.column("date", width=125, minwidth=110, stretch=False)
        self.history_tree.column("title", width=210, minwidth=140)
        self.history_tree.column("link", width=190, minwidth=140)
        self.history_tree.column("author", width=130, minwidth=100)

        self.history_tree.pack(side="left", fill="both", expand=True)
        yscroll.config(command=self.history_tree.yview)
        xscroll.config(command=self.history_tree.xview)

        self.history_tree.bind("<Motion>", self._on_history_hover)
        self.history_tree.bind("<ButtonRelease-1>", self._on_history_click)
        self.history_tree.bind("<Double-1>", lambda e: self.open_selected_history_link())
        self.history_tree.bind("<Button-3>", self._on_history_right_click)

        # Right-click context menu
        self.hist_menu = tk.Menu(self, tearoff=0)
        self.hist_menu.add_command(label="Open Downloaded File Location", command=self.open_selected_history_file)
        self.hist_menu.add_command(label="Open Link in Browser", command=self.open_selected_history_link)
        self.hist_menu.add_command(label="Copy Link", command=self.copy_selected_history_link)
        self.hist_menu.add_separator()
        self.hist_menu.add_command(label="Remove Entry", command=self.remove_selected_history_entry)

    def _on_history_hover(self, event):
        col = self.history_tree.identify_column(event.x)
        row = self.history_tree.identify_row(event.y)
        self.history_tree.configure(cursor="hand2" if (col == "#3" and row) else "")

    def _on_history_click(self, event):
        col = self.history_tree.identify_column(event.x)
        row = self.history_tree.identify_row(event.y)
        if col == "#3" and row:
            vals = self.history_tree.item(row, "values")
            if len(vals) >= 3 and vals[2].startswith(("http://", "https://")):
                webbrowser.open(vals[2])

    def _on_history_right_click(self, event):
        row = self.history_tree.identify_row(event.y)
        if not row:
            return
        self.history_tree.selection_set(row)
        self.history_tree.focus(row)
        try:
            self.hist_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.hist_menu.grab_release()

    def _get_selected_history_index(self):
        sel = self.history_tree.selection()
        if not sel:
            return None
        try:
            return int(sel[0])
        except ValueError:
            return None

    def _find_downloaded_file_fallback(self, entry):
        """Finds files whose stored path missed Unicode punctuation (like ：) or older entries without filepath."""
        saved_path = entry.get("filepath", "")
        title_key = _alnum_key(entry.get("title", ""))
        base_key = _alnum_key(os.path.splitext(os.path.basename(saved_path))[0]) if saved_path else ""
        folder_key = _alnum_key(os.path.basename(os.path.dirname(saved_path))) if saved_path else ""

        search_roots = []
        if saved_path:
            parent_of_folder = os.path.dirname(os.path.dirname(saved_path))
            if os.path.isdir(parent_of_folder):
                search_roots.append(parent_of_folder)
        save_dir = self.save_dir_var.get()
        if os.path.isdir(save_dir) and save_dir not in search_roots:
            search_roots.append(save_dir)

        best_match = None
        best_score = 0

        for root_dir in search_roots:
            try:
                entries = list(os.scandir(root_dir))
            except OSError:
                continue

            # Check root files + 1 level of subfolders
            scan_dirs = [(root_dir, False)]
            for e in entries:
                if e.is_dir():
                    scan_dirs.append((e.path, True))

            for dpath, is_sub in scan_dirs:
                dkey = _alnum_key(os.path.basename(dpath)) if is_sub else ""
                try:
                    for item in os.scandir(dpath):
                        if not item.is_file():
                            continue
                        fname_no_ext = os.path.splitext(item.name)[0]
                        fkey = _alnum_key(fname_no_ext)
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

    def open_selected_history_file(self):
        idx = self._get_selected_history_index()
        if idx is None or not (0 <= idx < len(self.history_items)):
            return
        entry = self.history_items[idx]
        filepath = entry.get("filepath", "")

        target_path = filepath if (filepath and os.path.exists(filepath)) else None
        if not target_path:
            found = self._find_downloaded_file_fallback(entry)
            if found and os.path.exists(found):
                target_path = found
                # Repair the saved filepath in history so future clicks are instant
                entry["filepath"] = os.path.normpath(found)
                self.save_history()

        if target_path:
            abs_path = os.path.normpath(os.path.abspath(target_path))
            if os.name == "nt":
                # Keep /select, and quoted path glued together with no space for Windows Explorer
                subprocess.Popen(f'explorer /select,"{abs_path}"')
            else:
                webbrowser.open(os.path.dirname(abs_path))
        elif filepath and os.path.isdir(os.path.dirname(filepath)):
            os.startfile(os.path.dirname(filepath))
        else:
            messagebox.showinfo(
                "File Not Found",
                "Could not locate the downloaded file on disk (it may have been moved or deleted).",
            )

    def open_selected_history_link(self):
        idx = self._get_selected_history_index()
        if idx is None or not (0 <= idx < len(self.history_items)):
            return
        link = self.history_items[idx].get("link", "")
        if link.startswith(("http://", "https://")):
            webbrowser.open(link)

    def copy_selected_history_link(self):
        idx = self._get_selected_history_index()
        if idx is None or not (0 <= idx < len(self.history_items)):
            return
        link = self.history_items[idx].get("link", "")
        if link:
            self.clipboard_clear()
            self.clipboard_append(link)

    def remove_selected_history_entry(self):
        idx = self._get_selected_history_index()
        if idx is None or not (0 <= idx < len(self.history_items)):
            return
        self.history_items.pop(idx)
        self.save_history()
        self.refresh_history_tree()

    def record_history_entry(self, title, url, author, filepath=""):
        abs_path = os.path.normpath(filepath) if filepath else ""
        entry = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "title": (title or "Untitled").strip(),
            "link": (url or "").strip(),
            "author": (author or "Unknown").strip(),
            "filepath": abs_path,
        }
        self.history_items.insert(0, entry)
        self.save_history()
        self.refresh_history_tree()

    def refresh_history_tree(self):
        if not hasattr(self, "history_tree"):
            return
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        for idx, entry in enumerate(self.history_items):
            self.history_tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(
                    entry.get("date", ""),
                    entry.get("title", ""),
                    entry.get("link", ""),
                    entry.get("author", ""),
                ),
            )
        self.hist_count_lbl.config(text=f"Downloads: {len(self.history_items)}")

    def clear_history(self):
        if not self.history_items:
            return
        if messagebox.askyesno("Clear History", "Clear all download history entries?"):
            self.history_items = []
            self.save_history()
            self.refresh_history_tree()

    def load_history(self):
        if not os.path.exists(HISTORY_FILE):
            return
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                self.history_items = data
        except Exception:
            self.history_items = []

    def save_history(self):
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.history_items, f, indent=2)
        except OSError:
            pass

    # ========================================================================
    # SETTINGS & UPDATES TAB
    # ========================================================================
    def build_settings_tab(self):
        pad = {"padx": 14, "pady": 6}

        theme_frame = ttk.LabelFrame(self.settings_tab, text="Appearance & Reset")
        theme_frame.pack(fill="x", **pad)

        modes = [
            ("system", "Use Windows System Setting (Auto Light/Dark)"),
            ("dark", "Always Dark Mode"),
            ("light", "Always Light Mode"),
        ]
        for val, label in modes:
            ttk.Radiobutton(
                theme_frame,
                text=label,
                value=val,
                variable=self.theme_mode,
                command=self.on_theme_change,
            ).pack(anchor="w", padx=12, pady=3)

        reset_row = ttk.Frame(theme_frame)
        reset_row.pack(fill="x", padx=12, pady=(6, 8))
        ttk.Button(
            reset_row, text="Reset All Settings / Options to Default", command=self.reset_all_settings
        ).pack(side="left")

        app_upd_frame = ttk.LabelFrame(self.settings_tab, text=f"App Updates ({GITHUB_REPO})")
        app_upd_frame.pack(fill="x", **pad)

        app_row = ttk.Frame(app_upd_frame)
        app_row.pack(fill="x", padx=12, pady=8)

        ttk.Label(app_row, textvariable=self.app_ver_var, font=("Segoe UI", 10, "bold")).pack(
            side="left", padx=(0, 16)
        )
        self.app_upd_btn = ttk.Button(
            app_row, text="Check & Update App from GitHub", command=self.check_and_update_app
        )
        self.app_upd_btn.pack(side="left")

        upd_frame = ttk.LabelFrame(self.settings_tab, text="yt-dlp Engine & Dependencies")
        upd_frame.pack(fill="both", expand=True, **pad)

        ttk.Label(upd_frame, textvariable=self.version_var, font=("Segoe UI", 10, "bold")).pack(
            anchor="w", padx=12, pady=(8, 4)
        )

        btn_row = ttk.Frame(upd_frame)
        btn_row.pack(fill="x", padx=12, pady=4)

        self.chk_ver_btn = ttk.Button(btn_row, text="Check Version & Files", command=self.check_ytdlp_version)
        self.chk_ver_btn.pack(side="left", padx=(0, 8))

        self.upd_btn = ttk.Button(btn_row, text="Update yt-dlp Now", command=self.update_ytdlp)
        self.upd_btn.pack(side="left")

        ttk.Label(upd_frame, text="Status & Update Log:").pack(anchor="w", padx=12, pady=(6, 2))

        upd_log_inner = ttk.Frame(upd_frame)
        upd_log_inner.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        upd_scroll = ttk.Scrollbar(upd_log_inner, orient="vertical")
        upd_scroll.pack(side="right", fill="y")

        self.upd_log_text = tk.Text(
            upd_log_inner,
            height=9,
            font=("Consolas", 9),
            wrap="word",
            yscrollcommand=upd_scroll.set,
            relief="flat",
            padx=6,
            pady=6,
        )
        self.upd_log_text.pack(side="left", fill="both", expand=True)
        upd_scroll.config(command=self.upd_log_text.yview)

    def reset_all_settings(self):
        if not messagebox.askyesno(
            "Reset Settings",
            "Reset all format, quality, clip, subtitle, cookie, folder, and theme options back to default?\n\n(Your Download History will NOT be deleted.)",
        ):
            return
        try:
            if os.path.exists(SETTINGS_FILE):
                os.remove(SETTINGS_FILE)
        except OSError:
            pass

        self.save_dir_var.set(DEFAULT_SAVE_DIR)
        self.media_type.set("video")
        self.video_fmt.set("mp4")
        self.audio_fmt.set("mp3")
        self.quality_label_var.set("Auto (Best)")
        self.use_custom_res_var.set(False)
        self.custom_res_var.set("")
        self.range_choice.set("1")
        self.sh_var.set(0)
        self.sm_var.set(1)
        self.ss_var.set(0)
        self.eh_var.set(0)
        self.em_var.set(2)
        self.es_var.set(0)
        self.use_p_start.set(True)
        self.p_start_var.set(1)
        self.use_p_end.set(True)
        self.p_end_var.set(5)
        self.custom_title_var.set("")
        self.remove_link_title_var.set(False)
        self.playlist_folder_var.set(True)
        self.custom_playlist_folder_var.set("")
        self.playlist_numbering_var.set(False)
        self.meta_var.set(False)
        self.subs_var.set(False)
        self.sub_lang_label_var.set("English (en)")
        self.custom_sub_lang_var.set("en,id")
        self.cookie_browser_label_var.set("None")
        self.theme_mode.set("system")

        self.refresh_format_options()
        self.update_quality_controls()
        self.update_subtitle_controls()
        self.update_playlist_folder_controls()
        self.update_scope_visibility()
        self.apply_theme(force=True)
        self.save_settings()
        messagebox.showinfo("Settings Reset", "All settings have been restored to their default values.")

    # ========================================================================
    # VIDEO & AUDIO PREVIEW ENGINE (Pauses on Seek + Single-Frame Scrubbing)
    # ========================================================================
    def set_clip_marker(self, is_start):
        sec = max(0, int(self.preview_pos))
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        if is_start:
            self.sh_var.set(h)
            self.sm_var.set(m)
            self.ss_var.set(s)
            label = f"Start set -> {h:02d}:{m:02d}:{s:02d}"
        else:
            self.eh_var.set(h)
            self.em_var.set(m)
            self.es_var.set(s)
            label = f"End set -> {h:02d}:{m:02d}:{s:02d}"

        self.range_choice.set("2")
        self.update_scope_visibility()
        self.save_settings()
        self.preview_mode_badge.config(text=label)

    def get_cookie_args(self):
        browser = COOKIE_LABEL_TO_VAL.get(self.cookie_browser_label_var.get(), "none")
        if browser and browser != "none":
            return ["--cookies-from-browser", browser]
        return []

    def start_preview(self):
        url = self.url_var.get().strip().replace('"', "")
        if not url:
            messagebox.showwarning("Missing Link", "Paste a link first before clicking Preview.")
            return

        self.stop_preview_streams()
        self.preview_session_id += 1
        session_id = self.preview_session_id

        self.preview_box.pack(fill="x", padx=8, pady=(0, 8))
        self.preview_player_frame.pack_forget()
        self.preview_msg_lbl.pack_forget()
        self.preview_title_lbl.config(text="Loading link preview...")
        self.preview_loading_lbl.config(text="Fetching media details & stream info...")
        self.preview_loading_frame.pack(fill="x", padx=12, pady=8)
        self.preview_progress.start(12)
        self.preview_btn.config(state="disabled")

        threading.Thread(target=self._preview_info_worker, args=(url, session_id), daemon=True).start()

    def _explain_ytdlp_error(self, raw_err):
        low = raw_err.lower()
        if "could not copy" in low and "cookie" in low:
            return "Your browser locked its cookie database while running. Close that browser briefly or switch Browser Cookies to Firefox / None."
        if any(k in low for k in ("sign in", "login", "cookies", "confirm your age", "age-restricted")):
            return "This site requires a logged-in session. Select a Browser Cookies option in Section 6 and try again."
        if "403" in low or "forbidden" in low:
            return "Access forbidden (HTTP 403). The site is blocking direct preview requests."
        if "429" in low or "rate-limit" in low or "too many requests" in low:
            return "Rate-limited (HTTP 429). The site temporarily blocked requests from your IP."
        if "private video" in low or "unavailable" in low or "removed" in low:
            return "This media is private, deleted, or unavailable in your region."
        if "unsupported url" in low:
            return "Unsupported URL — yt-dlp does not recognize a media link at this address."
        if "drm" in low:
            return "This stream is DRM-protected and cannot be previewed or downloaded."
        lines = [ln.strip() for ln in raw_err.splitlines() if "ERROR:" in ln]
        return lines[-1] if lines else raw_err.strip()[:220]

    def _preview_info_worker(self, url, session_id):
        try:
            cmd = [self.get_ytdlp_exe(), "--dump-single-json", "--flat-playlist", "--no-warnings"]
            cmd += self.get_cookie_args()
            node_exe = self.get_node_exe()
            if node_exe:
                cmd += ["--js-runtimes", f"node:{node_exe}"]
            cmd.append(url)

            env = os.environ.copy()
            env["PYTHONUTF8"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"

            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            out = subprocess.check_output(
                cmd,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                creationflags=creation_flags,
            )
            json_lines = [line for line in out.splitlines() if line.strip().startswith("{")]
            if not json_lines:
                raise RuntimeError("No media metadata returned by yt-dlp.")
            data = json.loads(json_lines[-1])
            self.after(0, self._handle_preview_metadata, data, session_id)
        except subprocess.CalledProcessError as e:
            reason = self._explain_ytdlp_error(e.output or str(e))
            self.after(
                0,
                self._show_preview_message,
                "Preview Unavailable",
                f"Could not preview this link.\nReason: {reason}",
                session_id,
            )
        except Exception as e:
            self.after(
                0,
                self._show_preview_message,
                "Preview Unavailable",
                f"Could not preview this link.\nReason: {e}",
                session_id,
            )

    def _handle_preview_metadata(self, data, session_id):
        if session_id != self.preview_session_id:
            return

        title = data.get("title") or "Untitled Media"

        if data.get("_type") in ("playlist", "multi_video") or "entries" in data:
            entries = data.get("entries") or []
            count = data.get("playlist_count") or len(entries)
            self._show_preview_message(
                f"Playlist: {title}",
                f"Playlist link detected ({count} items).\nPreview playback is skipped for playlists, but you can download all or selected items below.",
                session_id,
            )
            return

        ffmpeg_exe = self.get_ffmpeg_exe()
        if not ffmpeg_exe:
            self._show_preview_message(
                "Preview Unavailable",
                "ffmpeg.exe is required for preview playback, but was not found on PATH or in the app folder.",
                session_id,
            )
            return

        formats = data.get("formats") or []
        valid_formats = [f for f in formats if f.get("url")]

        muxed = [
            f
            for f in valid_formats
            if f.get("vcodec") not in (None, "none", "images")
            and f.get("acodec") not in (None, "none")
        ]
        video_only = [
            f for f in valid_formats if f.get("vcodec") not in (None, "none", "images")
        ]
        audio_only = [
            f
            for f in valid_formats
            if f.get("acodec") not in (None, "none")
            and f.get("vcodec") in (None, "none")
        ]

        self.preview_video_url = None
        self.preview_audio_url = None
        self.preview_headers = data.get("http_headers") or {}
        self.preview_has_video = False

        if muxed:
            pref = [f for f in muxed if (f.get("height") or 9999) <= 480]
            chosen = pref[-1] if pref else muxed[0]
            self.preview_video_url = chosen["url"]
            self.preview_audio_url = chosen["url"]
            self.preview_headers = chosen.get("http_headers") or self.preview_headers
            self.preview_has_video = True
        elif video_only:
            pref = [f for f in video_only if (f.get("height") or 9999) <= 480]
            v_chosen = pref[-1] if pref else video_only[0]
            self.preview_video_url = v_chosen["url"]
            self.preview_headers = v_chosen.get("http_headers") or self.preview_headers
            self.preview_has_video = True
            if audio_only:
                self.preview_audio_url = audio_only[-1]["url"]
        elif audio_only:
            a_chosen = audio_only[-1]
            self.preview_audio_url = a_chosen["url"]
            self.preview_headers = a_chosen.get("http_headers") or self.preview_headers
            self.preview_has_video = False
        elif data.get("url"):
            if data.get("vcodec") == "none":
                self.preview_audio_url = data["url"]
                self.preview_has_video = False
            else:
                self.preview_video_url = data["url"]
                self.preview_audio_url = data["url"]
                self.preview_has_video = True
        else:
            self._show_preview_message(
                "Preview Unavailable",
                "No playable video or audio stream was found for this link (the site may restrict direct streaming).",
                session_id,
            )
            return

        self.preview_duration = float(data.get("duration") or 0.0)
        self.preview_pos = 0.0

        self.preview_progress.stop()
        self.preview_loading_frame.pack_forget()
        self.preview_msg_lbl.pack_forget()
        self.preview_btn.config(state="normal")

        self.preview_title_lbl.config(text=title)
        self.preview_slider.set_range(0.0, max(1.0, self.preview_duration))
        self.preview_slider.set(0.0)
        self.preview_time_lbl.config(text=f"00:00 / {format_seconds(self.preview_duration)}")

        if self.preview_has_video:
            self.preview_mode_badge.config(text="Video + Audio" if self.preview_audio_url else "Video Only")
            self.video_canvas_lbl.config(image="", text="Buffering video...", fg="#a1a1aa", width=PREVIEW_W, height=PREVIEW_H)
            self.preview_player_frame.pack(fill="x")
        else:
            self.preview_mode_badge.config(text="Audio Only")
            self.video_canvas_lbl.config(image="", text="Loading album cover...", fg="#a1a1aa", width=PREVIEW_W, height=PREVIEW_H)
            self.preview_player_frame.pack(fill="x")
            thumb_url = self._pick_thumbnail_url(data)
            if thumb_url:
                threading.Thread(
                    target=self._load_cover_art_worker,
                    args=(thumb_url, self.preview_headers, session_id),
                    daemon=True,
                ).start()
            else:
                self.video_canvas_lbl.config(text="Audio Track (No Cover Art Available)", fg="#a1a1aa")

        self.start_preview_streams_at(0.0)

    def _pick_thumbnail_url(self, data):
        if data.get("thumbnail"):
            return data["thumbnail"]
        thumbs = data.get("thumbnails") or []
        for t in reversed(thumbs):
            if t.get("url"):
                return t["url"]
        return None

    def _load_cover_art_worker(self, thumb_url, headers, session_id):
        ffmpeg_exe = self.get_ffmpeg_exe()
        if not ffmpeg_exe:
            return
        try:
            req = urllib.request.Request(
                thumb_url,
                headers={"User-Agent": headers.get("User-Agent", "Mozilla/5.0")},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                img_bytes = resp.read()

            vf_str = (
                f"scale={PREVIEW_W}:{PREVIEW_H}:force_original_aspect_ratio=decrease,"
                f"pad={PREVIEW_W}:{PREVIEW_H}:(ow-iw)/2:(oh-ih)/2"
            )
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            proc = subprocess.run(
                [
                    ffmpeg_exe,
                    "-i",
                    "pipe:0",
                    "-vf",
                    vf_str,
                    "-frames:v",
                    "1",
                    "-f",
                    "image2pipe",
                    "-vcodec",
                    "ppm",
                    "-loglevel",
                    "quiet",
                    "-",
                ],
                input=img_bytes,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                creationflags=creation_flags,
            )
            if proc.stdout and proc.stdout.startswith(b"P6"):
                self.after(0, self._display_cover_art, proc.stdout, session_id)
        except Exception:
            self.after(
                0,
                lambda: self.video_canvas_lbl.config(text="Audio Track (No Cover Art Available)")
                if session_id == self.preview_session_id
                else None,
            )

    def _display_cover_art(self, ppm_bytes, session_id):
        if session_id != self.preview_session_id or self.preview_has_video:
            return
        try:
            self.preview_photo = tk.PhotoImage(data=ppm_bytes)
            self.video_canvas_lbl.config(image=self.preview_photo, text="")
        except Exception:
            pass

    def _show_preview_message(self, header_text, body_text, session_id):
        if session_id != self.preview_session_id:
            return
        self.preview_progress.stop()
        self.preview_loading_frame.pack_forget()
        self.preview_player_frame.pack_forget()
        self.preview_btn.config(state="normal")
        self.preview_title_lbl.config(text=header_text)
        self.preview_msg_lbl.config(text=body_text)
        self.preview_msg_lbl.pack(fill="x", padx=12, pady=12)

    def _build_ffmpeg_header_args(self):
        if not self.preview_headers:
            return []
        lines = []
        for k, v in self.preview_headers.items():
            if k.lower() in ("user-agent", "referer", "origin", "accept", "cookie"):
                lines.append(f"{k}: {v}")
        if not lines:
            return []
        return ["-headers", "\r\n".join(lines) + "\r\n"]

    def start_preview_streams_at(self, start_sec):
        self.stop_preview_streams()
        if not self.preview_video_url and not self.preview_audio_url:
            return

        self.preview_pos = max(0.0, min(start_sec, self.preview_duration))
        self.preview_playing = True
        self.play_pause_btn.config(text="Pause")
        self.preview_session_id += 1
        session_id = self.preview_session_id

        if self.preview_has_video and self.preview_video_url:
            threading.Thread(
                target=self._ffmpeg_video_worker,
                args=(self.preview_video_url, self.preview_pos, session_id),
                daemon=True,
            ).start()

        if self.preview_audio_url:
            threading.Thread(
                target=self._ffmpeg_audio_worker,
                args=(self.preview_audio_url, self.preview_pos, session_id, not self.preview_has_video),
                daemon=True,
            ).start()

    def _fetch_single_frame_worker(self, stream_url, target_sec, session_id):
        """Fetches a single preview frame at target_sec so seeking updates the picture while staying paused."""
        ffmpeg_exe = self.get_ffmpeg_exe()
        if not ffmpeg_exe:
            return
        vf_str = (
            f"scale={PREVIEW_W}:{PREVIEW_H}:force_original_aspect_ratio=decrease,"
            f"pad={PREVIEW_W}:{PREVIEW_H}:(ow-iw)/2:(oh-ih)/2"
        )
        cmd = [ffmpeg_exe] + self._build_ffmpeg_header_args() + [
            "-ss",
            f"{target_sec:.2f}",
            "-i",
            stream_url,
            "-an",
            "-vf",
            vf_str,
            "-frames:v",
            "1",
            "-f",
            "image2pipe",
            "-vcodec",
            "ppm",
            "-loglevel",
            "quiet",
            "-",
        ]
        try:
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            proc = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=8, creationflags=creation_flags
            )
            if proc.stdout and proc.stdout.startswith(b"P6"):
                self.after(0, self._display_paused_frame, proc.stdout, session_id)
        except Exception:
            pass

    def _display_paused_frame(self, ppm_frame, session_id):
        if session_id != self.preview_session_id or self.preview_playing:
            return
        try:
            self.preview_photo = tk.PhotoImage(data=ppm_frame)
            self.video_canvas_lbl.configure(image=self.preview_photo, text="")
        except Exception:
            pass

    def _ffmpeg_video_worker(self, stream_url, start_sec, session_id):
        ffmpeg_exe = self.get_ffmpeg_exe()
        if not ffmpeg_exe:
            return

        vf_str = (
            f"scale={PREVIEW_W}:{PREVIEW_H}:force_original_aspect_ratio=decrease,"
            f"pad={PREVIEW_W}:{PREVIEW_H}:(ow-iw)/2:(oh-ih)/2"
        )
        cmd = [ffmpeg_exe] + self._build_ffmpeg_header_args() + [
            "-ss",
            f"{start_sec:.2f}",
            "-re",
            "-i",
            stream_url,
            "-an",
            "-vf",
            vf_str,
            "-r",
            str(PREVIEW_FPS),
            "-f",
            "image2pipe",
            "-vcodec",
            "ppm",
            "-loglevel",
            "error",
            "-",
        ]

        frames_received = 0
        try:
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creation_flags,
            )
            self.preview_video_proc = proc

            while session_id == self.preview_session_id and self.preview_playing:
                magic = proc.stdout.readline()
                if not magic or not magic.startswith(b"P6"):
                    break
                dims = proc.stdout.readline()
                while dims.startswith(b"#"):
                    dims = proc.stdout.readline()
                maxval = proc.stdout.readline()
                if not dims or not maxval:
                    break

                w, h = map(int, dims.split())
                pixel_bytes = proc.stdout.read(w * h * 3)
                if len(pixel_bytes) < w * h * 3:
                    break

                frames_received += 1
                ppm_frame = magic + dims + maxval + pixel_bytes
                cur_time = start_sec + (frames_received / PREVIEW_FPS)
                self.after(0, self._render_preview_frame, ppm_frame, cur_time, session_id)

            if frames_received == 0 and session_id == self.preview_session_id and self.preview_playing:
                err_txt = proc.stderr.read().decode("utf-8", errors="replace").strip()
                reason = err_txt.splitlines()[-1] if err_txt else "The host blocked direct FFmpeg streaming."
                self.after(
                    0,
                    self._show_preview_message,
                    "Video Stream Blocked",
                    f"Preview could not play this stream (downloading may still work).\nReason: {reason}",
                    session_id,
                )
        except Exception:
            pass

    def _ffmpeg_audio_worker(self, stream_url, start_sec, session_id, drives_clock):
        ffmpeg_exe = self.get_ffmpeg_exe()
        if not ffmpeg_exe:
            return

        if not self.wave_player.open():
            return
        self.wave_player.set_volume(0.0 if self.preview_muted else self.preview_volume)

        cmd = [ffmpeg_exe] + self._build_ffmpeg_header_args() + [
            "-ss",
            f"{start_sec:.2f}",
            "-i",
            stream_url,
            "-vn",
            "-f",
            "s16le",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-loglevel",
            "error",
            "-",
        ]

        bytes_per_sec = 44100 * 2 * 2
        chunk_size = 17640
        total_bytes = 0

        try:
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creation_flags,
            )
            self.preview_audio_proc = proc

            while session_id == self.preview_session_id and self.preview_playing:
                chunk = proc.stdout.read(chunk_size)
                if not chunk:
                    break
                if not self.wave_player.write(chunk):
                    break
                total_bytes += len(chunk)
                if drives_clock:
                    cur_time = start_sec + (total_bytes / bytes_per_sec)
                    self.after(0, self._update_clock_only, cur_time, session_id)

            if total_bytes == 0 and drives_clock and session_id == self.preview_session_id and self.preview_playing:
                err_txt = proc.stderr.read().decode("utf-8", errors="replace").strip()
                reason = err_txt.splitlines()[-1] if err_txt else "The host blocked direct audio streaming."
                self.after(
                    0,
                    self._show_preview_message,
                    "Audio Stream Blocked",
                    f"Preview could not play this audio stream (downloading may still work).\nReason: {reason}",
                    session_id,
                )
        except Exception:
            pass

    def _render_preview_frame(self, ppm_frame, cur_time, session_id):
        if session_id != self.preview_session_id or not self.preview_playing:
            return
        try:
            self.preview_photo = tk.PhotoImage(data=ppm_frame)
            self.video_canvas_lbl.configure(image=self.preview_photo, text="")
            self.preview_pos = min(cur_time, self.preview_duration)
            if not self.preview_seeking:
                self.preview_slider.set(self.preview_pos)
                self.preview_time_lbl.config(
                    text=f"{format_seconds(self.preview_pos)} / {format_seconds(self.preview_duration)}"
                )
        except Exception:
            pass

    def _update_clock_only(self, cur_time, session_id):
        if session_id != self.preview_session_id or not self.preview_playing:
            return
        self.preview_pos = min(cur_time, self.preview_duration)
        if not self.preview_seeking:
            self.preview_slider.set(self.preview_pos)
            self.preview_time_lbl.config(
                text=f"{format_seconds(self.preview_pos)} / {format_seconds(self.preview_duration)}"
            )

    def toggle_preview_play(self):
        if not self.preview_video_url and not self.preview_audio_url:
            return
        if self.preview_playing:
            self.stop_preview_streams()
            self.play_pause_btn.config(text="Play")
        else:
            self.start_preview_streams_at(self.preview_pos)

    def on_preview_scrub_start(self, val):
        self.preview_seeking = True
        self.stop_preview_streams()
        self.play_pause_btn.config(text="Play")

    def on_preview_scrub_move(self, val):
        if self.preview_seeking:
            self.preview_pos = max(0.0, min(float(val), self.preview_duration))
            self.preview_time_lbl.config(
                text=f"{format_seconds(self.preview_pos)} / {format_seconds(self.preview_duration)}"
            )

    def on_preview_scrub_end(self, val):
        if not self.preview_seeking:
            return
        self.preview_seeking = False
        self.stop_preview_streams()
        self.preview_pos = max(0.0, min(float(val), self.preview_duration))
        self.preview_slider.set(self.preview_pos)
        self.preview_time_lbl.config(
            text=f"{format_seconds(self.preview_pos)} / {format_seconds(self.preview_duration)}"
        )
        self.play_pause_btn.config(text="Play")

        # Update the video preview picture at the seeked timestamp while staying paused
        if self.preview_has_video and self.preview_video_url:
            self.preview_session_id += 1
            session_id = self.preview_session_id
            threading.Thread(
                target=self._fetch_single_frame_worker,
                args=(self.preview_video_url, self.preview_pos, session_id),
                daemon=True,
            ).start()

    def on_volume_change(self, val):
        pct = int(round(val))
        self.preview_volume = pct / 100.0
        self.preview_muted = pct == 0
        self.mute_btn.config(text="Muted" if self.preview_muted else "Vol:")
        self.vol_pct_lbl.config(text=f"{pct}%")
        self.wave_player.set_volume(0.0 if self.preview_muted else self.preview_volume)

    def toggle_mute(self):
        self.preview_muted = not self.preview_muted
        if self.preview_muted:
            self.mute_btn.config(text="Muted")
            self.vol_pct_lbl.config(text="0%")
            self.wave_player.set_volume(0.0)
        else:
            if self.preview_volume <= 0.01:
                self.preview_volume = 0.5
                self.vol_slider.set(50)
            self.mute_btn.config(text="Vol:")
            self.vol_pct_lbl.config(text=f"{int(round(self.preview_volume * 100))}%")
            self.wave_player.set_volume(self.preview_volume)

    def stop_preview_streams(self):
        self.preview_playing = False
        self.wave_player.stop()
        for attr in ("preview_video_proc", "preview_audio_proc"):
            proc = getattr(self, attr, None)
            setattr(self, attr, None)
            if proc and proc.poll() is None:
                try:
                    proc.kill()
                except Exception:
                    pass

    def close_preview(self):
        self.preview_session_id += 1
        self.stop_preview_streams()
        self.preview_progress.stop()
        self.preview_video_url = None
        self.preview_audio_url = None
        self.preview_box.pack_forget()
        self.preview_btn.config(state="normal")

    def clear_url(self):
        self.url_var.set("")
        self.close_preview()

    # ========================================================================
    # GITHUB SELF-UPDATER
    # ========================================================================
    def check_and_update_app(self):
        self.app_upd_btn.config(state="disabled")
        self.upd_log_text.delete("1.0", "end")
        self._append_upd_log(f"Checking GitHub ({GITHUB_REPO}) for app updates...\n")
        threading.Thread(target=self._github_update_worker, daemon=True).start()

    def _github_update_worker(self):
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        try:
            req = urllib.request.Request(api_url, headers={"User-Agent": "yt-dlp-Downloader-App"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                release = json.loads(resp.read().decode("utf-8"))

            latest_tag = release.get("tag_name", "").lstrip("vV")
            if not latest_tag:
                self.after(0, self._append_upd_log, "No release tag found on GitHub.\n")
                return

            if latest_tag == APP_VERSION:
                self.after(
                    0,
                    self._append_upd_log,
                    f"You are already on the latest version (v{APP_VERSION}).\n",
                )
                return

            is_frozen = getattr(sys, "frozen", False)
            target_ext = ".exe" if is_frozen else ".pyw"
            assets = release.get("assets") or []
            dl_url = None
            for asset in assets:
                name = asset.get("name", "")
                if name.lower().endswith(target_ext) and "setup" not in name.lower():
                    dl_url = asset.get("browser_download_url")
                    break

            if not dl_url:
                self.after(
                    0,
                    self._append_upd_log,
                    f"New version v{latest_tag} found, but no {target_ext} file was attached to the GitHub Release.\n",
                )
                return

            self.after(0, self._prompt_and_install_app_update, latest_tag, dl_url)
        except Exception as e:
            self.after(0, self._append_upd_log, f"Failed to check GitHub updates: {e}\n")
        finally:
            self.after(0, lambda: self.app_upd_btn.config(state="normal"))

    def _prompt_and_install_app_update(self, latest_tag, dl_url):
        msg = f"A new version (v{latest_tag}) is available on GitHub!\n\nCurrent version: v{APP_VERSION}\n\nUpdate and restart now?"
        if not messagebox.askyesno("Update Available", msg):
            self._append_upd_log("Update cancelled by user.\n")
            return

        self.app_upd_btn.config(state="disabled")
        self._append_upd_log(f"Downloading v{latest_tag} from GitHub...\n")
        threading.Thread(target=self._download_and_swap_app, args=(dl_url,), daemon=True).start()

    def _download_and_swap_app(self, dl_url):
        try:
            is_frozen = getattr(sys, "frozen", False)
            current_file = sys.executable if is_frozen else os.path.abspath(__file__)
            temp_file = current_file + ".new"

            req = urllib.request.Request(dl_url, headers={"User-Agent": "yt-dlp-Downloader-App"})
            with urllib.request.urlopen(req, timeout=30) as resp, open(temp_file, "wb") as out_f:
                shutil.copyfileobj(resp, out_f)

            if is_frozen and os.name == "nt":
                bat_path = os.path.join(APP_DIR, "_update_swap.bat")
                with open(bat_path, "w", encoding="utf-8") as bf:
                    bf.write(
                        "@echo off\n"
                        "timeout /t 2 /nobreak >nul\n"
                        f'move /y "{temp_file}" "{current_file}" >nul\n'
                        f'start "" "{current_file}"\n'
                        'del "%~f0"\n'
                    )
                subprocess.Popen(
                    ["cmd.exe", "/c", bat_path],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                self.after(0, self.on_close)
            else:
                os.replace(temp_file, current_file)
                subprocess.Popen([sys.executable, current_file])
                self.after(0, self.on_close)
        except Exception as e:
            self.after(0, self._append_upd_log, f"Failed to install update: {e}\n")
            self.after(0, lambda: self.app_upd_btn.config(state="normal"))

    # ========================================================================
    # CORE DOWNLOADER, QUEUE RUNNER & STOP/CANCEL
    # ========================================================================
    def get_ytdlp_exe(self):
        return YTDLP_PATH if os.path.exists(YTDLP_PATH) else (find_global_binary("yt-dlp.exe") or "yt-dlp")

    def get_ffmpeg_exe(self):
        global_ff = find_global_binary("ffmpeg.exe")
        if global_ff:
            return global_ff
        if os.path.exists(FFMPEG_PATH):
            return FFMPEG_PATH
        return None

    def get_node_exe(self):
        global_node = find_global_binary("node.exe")
        if global_node:
            return global_node
        if os.path.exists(NODE_PATH):
            return NODE_PATH
        return None

    def _parse_custom_res_filter(self, raw_text):
        txt = raw_text.strip().lower().replace("p", "")
        if "x" in txt:
            parts = txt.split("x", 1)
            if parts[0].isdigit() and parts[1].isdigit():
                w, h = int(parts[0]), int(parts[1])
                if w >= 64 and h >= 64:
                    return f"scale={w}:{h}"
        elif txt.isdigit():
            h = int(txt)
            if h >= 64:
                return f"scale=-2:{h}"
        return None

    def build_command(self, url):
        self.cleanup_redundant_local_binaries()
        # Use JSON-escaped %(field)j so Unicode characters like "：" survive Windows pipe encoding losslessly
        cmd = [
            self.get_ytdlp_exe(),
            "--progress",
            "--no-quiet",
            "--no-simulate",
            "--print",
            "after_move:__HIST__\t%(fulltitle,title)j\t%(webpage_url)j\t%(artist,uploader,channel,creator|Unknown)j\t%(filepath)j",
        ]

        cmd += self.get_cookie_args()

        ffmpeg_exe = self.get_ffmpeg_exe()
        if ffmpeg_exe:
            cmd += ["--ffmpeg-location", os.path.dirname(ffmpeg_exe)]

        node_exe = self.get_node_exe()
        if node_exe:
            cmd += ["--js-runtimes", f"node:{node_exe}"]

        if self.remove_link_title_var.get():
            cmd += [
                "--replace-in-metadata",
                "title",
                r"https?://\S+",
                "",
                "--replace-in-metadata",
                "title",
                r"\s{2,}",
                " ",
                "--replace-in-metadata",
                "title",
                r"^\s+|\s+$",
                "",
            ]

        is_video = self.media_type.get() == "video"

        if is_video:
            vfmt = self.video_fmt.get()
            use_custom_res = self.use_custom_res_var.get()
            custom_scale = self._parse_custom_res_filter(self.custom_res_var.get()) if use_custom_res else None
            qual_val = QUALITY_LABEL_TO_VAL.get(self.quality_label_var.get(), "best")

            if use_custom_res and custom_scale:
                cmd += [
                    "-f",
                    "bestvideo+bestaudio/best",
                    "--recode-video",
                    vfmt,
                    "--postprocessor-args",
                    f"VideoConvertor:-vf {custom_scale}",
                ]
            else:
                if qual_val == "best":
                    if vfmt == "mp4":
                        cmd += ["-f", "bestvideo+bestaudio/best", "--merge-output-format", "mp4"]
                    elif vfmt == "webm":
                        cmd += ["-f", "bestvideo[ext=webm]+bestaudio[ext=webm]/bestvideo+bestaudio/best"]
                    elif vfmt == "mkv":
                        cmd += ["-f", "bestvideo+bestaudio/best", "--merge-output-format", "mkv"]
                    elif vfmt == "mov":
                        cmd += ["-f", "bestvideo+bestaudio/best", "--remux-video", "mov"]
                else:
                    strict_f = (
                        f"bestvideo[height={qual_val}]+bestaudio/"
                        f"bestvideo[width={qual_val}]+bestaudio/"
                        f"best[height={qual_val}]/best[width={qual_val}]"
                    )
                    cmd += ["-f", strict_f]
                    if vfmt in ("mp4", "mkv"):
                        cmd += ["--merge-output-format", vfmt]
                    elif vfmt == "mov":
                        cmd += ["--remux-video", "mov"]

            if self.subs_var.get():
                sub_val = SUB_LABEL_TO_VAL.get(self.sub_lang_label_var.get(), "en.*,en")
                if sub_val == "custom":
                    sub_langs = self.custom_sub_lang_var.get().strip() or "en.*,en"
                else:
                    sub_langs = sub_val
                cmd += ["--write-subs", "--write-auto-subs", "--sub-langs", sub_langs, "--embed-subs"]
        else:
            afmt = self.audio_fmt.get()
            if afmt == "orig":
                cmd += ["-f", "ba"]
            else:
                cmd += ["-x", "--audio-format", afmt]

        # Scope Arguments
        scope = self.range_choice.get()
        if scope == "2":
            dur_str = (
                f"*{self.sh_var.get():02d}:{self.sm_var.get():02d}:{self.ss_var.get():02d}"
                f"-{self.eh_var.get():02d}:{self.em_var.get():02d}:{self.es_var.get():02d}"
            )
            cmd += ["--download-sections", dur_str]
        elif scope == "3":
            if self.use_p_start.get():
                cmd += ["--playlist-start", str(self.p_start_var.get())]
            if self.use_p_end.get():
                cmd += ["--playlist-end", str(self.p_end_var.get())]

        # Output Template: "/" sits outside %(...)s so playlists create a real folder
        folder_part = ""
        if self.playlist_folder_var.get():
            custom_pl = sanitize_filename(self.custom_playlist_folder_var.get())
            if custom_pl:
                folder_part = f"./%(playlist_title&{custom_pl}|)s/"
            else:
                folder_part = "./%(playlist_title&{}|)s/"

        num_part = "%(playlist_index&{} - |)s" if self.playlist_numbering_var.get() else ""

        custom_title = sanitize_filename(self.custom_title_var.get())
        if custom_title:
            suffix = "" if self.playlist_numbering_var.get() else "%(playlist_index& ({})|)s"
            title_part = f"{custom_title}{suffix}"
        else:
            title_part = "%(title)s"

        out_tmpl = f"{folder_part}{num_part}{title_part}.%(ext)s"
        cmd += ["-o", out_tmpl]

        if self.meta_var.get():
            cmd += ["--embed-thumbnail", "--embed-metadata"]

        cmd.append(url)
        return cmd

    def on_download_or_cancel(self):
        if self.is_downloading:
            self.cancel_download()
        else:
            self.start_download()

    def cancel_download(self):
        self.cancel_requested = True
        self.dl_btn.config(text="Stopping...", state="disabled")
        proc = self.active_dl_proc
        if proc and proc.poll() is None:
            try:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                else:
                    proc.kill()
            except Exception:
                pass

    def start_download(self):
        entry_raw = self.url_var.get().strip()
        entry_links = [ln.strip().replace('"', "") for ln in entry_raw.splitlines() if ln.strip()]

        urls = list(self.download_queue)
        for ln in entry_links:
            if ln not in urls:
                urls.append(ln)

        if not urls:
            messagebox.showwarning("Missing Link", "Paste a link or add links to the queue first.")
            return

        if self.media_type.get() == "video" and self.use_custom_res_var.get():
            if not self._parse_custom_res_filter(self.custom_res_var.get()):
                messagebox.showwarning(
                    "Invalid Custom Resolution",
                    "Enter a valid height (e.g., 540 or 720) or dimensions (e.g., 1280x720).",
                )
                return

        self.close_preview()
        self.save_settings()
        save_dir = self.save_dir_var.get()
        os.makedirs(save_dir, exist_ok=True)

        self.is_downloading = True
        self.cancel_requested = False
        self.dl_btn.config(
            text="Stop / Cancel" if len(urls) == 1 else f"Stop / Cancel (1/{len(urls)})",
            bg="#dc2626",
            activebackground="#b91c1c",
            state="normal",
        )
        self.log_text.delete("1.0", "end")
        self._pending_cr = False

        threading.Thread(target=self._run_queue_worker, args=(urls, save_dir), daemon=True).start()

    def _run_queue_worker(self, urls, save_dir):
        total = len(urls)
        try:
            for idx, url in enumerate(urls, start=1):
                if self.cancel_requested:
                    break
                if total > 1:
                    self.after(
                        0,
                        lambda i=idx, t=total: self.dl_btn.config(text=f"Stop / Cancel ({i}/{t})"),
                    )
                    self.after(0, self.log_raw, f"\n>>> Queue Item {idx}/{total}: {url}\n")

                cmd = self.build_command(url)
                self.after(
                    0,
                    self.log_raw,
                    f"Saving to: {save_dir}\nRunning: {' '.join(cmd)}\n" + "=" * 56 + "\n",
                )

                ok = self._run_single_process(cmd, save_dir)
                if ok and not self.cancel_requested:
                    self.after(0, self._remove_url_from_queue, url)

            if self.cancel_requested:
                self.after(0, self.log_raw, "\n========================================================\nDownload cancelled by user.\n")
            else:
                self.after(0, self.log_raw, "\n========================================================\nAll downloads complete!\n")
        finally:
            self.after(0, self._finish_download_ui)

    def _remove_url_from_queue(self, url):
        if url in self.download_queue:
            self.download_queue.remove(url)
            self.refresh_queue_ui()

    def _run_single_process(self, cmd, save_dir):
        hist_buf = ""
        try:
            env = os.environ.copy()
            env["PYTHONUTF8"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"

            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            proc = subprocess.Popen(
                cmd,
                cwd=save_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                creationflags=creation_flags,
            )
            self.active_dl_proc = proc

            while True:
                chunk = proc.stdout.read1(1024)
                if not chunk:
                    break
                text = hist_buf + chunk.decode("utf-8", errors="replace").replace("\r\n", "\n")
                hist_buf = ""

                out_parts = []
                idx = 0
                while idx < len(text):
                    marker_pos = text.find("__HIST__\t", idx)
                    if marker_pos == -1:
                        tail = text[idx:]
                        for prefix_len in range(min(8, len(tail)), 0, -1):
                            if "__HIST__\t".startswith(tail[-prefix_len:]):
                                hist_buf = tail[-prefix_len:]
                                tail = tail[:-prefix_len]
                                break
                        out_parts.append(tail)
                        break

                    out_parts.append(text[idx:marker_pos])
                    nl_pos = text.find("\n", marker_pos)
                    if nl_pos == -1:
                        hist_buf = text[marker_pos:]
                        break
                    hist_line = text[marker_pos:nl_pos]
                    parts = hist_line.split("\t")
                    if len(parts) >= 4:
                        h_title = _json_unquote(parts[1])
                        h_url = _json_unquote(parts[2])
                        h_author = _json_unquote(parts[3])
                        h_fpath = _json_unquote(parts[4]) if len(parts) >= 5 else ""
                        self.after(0, self.record_history_entry, h_title, h_url, h_author, h_fpath)
                    idx = nl_pos + 1

                visible_text = "".join(out_parts)
                if visible_text:
                    self.after(0, self.log_raw, visible_text)

            if hist_buf and not hist_buf.startswith("__HIST__\t"):
                self.after(0, self.log_raw, hist_buf)

            proc.wait()
            if proc.returncode != 0 and not self.cancel_requested:
                self.after(0, self.log_raw, f"\nProcess exited with code {proc.returncode}\n")
                return False
            return True
        except FileNotFoundError:
            self.after(0, self.log_raw, f"\nError: Could not find yt-dlp.exe in {APP_DIR}\n")
            return False
        except Exception as e:
            if not self.cancel_requested:
                self.after(0, self.log_raw, f"\nError: {e}\n")
            return False
        finally:
            self.active_dl_proc = None

    def _finish_download_ui(self):
        self.is_downloading = False
        self.cancel_requested = False
        self.dl_btn.config(
            text="Download",
            bg="#2563eb",
            activebackground="#1d4ed8",
            state="normal",
        )

    def log_raw(self, chunk):
        chunk = chunk.replace("\r\n", "\n")
        i = 0
        n = len(chunk)
        while i < n:
            ch = chunk[i]
            if ch == "\r":
                self._pending_cr = True
                i += 1
            elif ch == "\n":
                self._pending_cr = False
                self.log_text.insert("end-1c", "\n")
                i += 1
            else:
                j = i
                while j < n and chunk[j] not in ("\r", "\n"):
                    j += 1
                segment = chunk[i:j]
                if self._pending_cr:
                    self.log_text.delete("end-1c linestart", "end-1c")
                    self._pending_cr = False
                self.log_text.insert("end-1c", segment)
                i = j
        self.log_text.see("end")

    # ========================================================================
    # UI CONTROL STATE HELPERS & THEME
    # ========================================================================
    def refresh_format_options(self):
        for widget in self.fmt_options_frame.winfo_children():
            widget.destroy()

        is_video = self.media_type.get() == "video"
        ttk.Label(self.fmt_options_frame, text="Format:", font=("Segoe UI", 9, "bold"))

        items = VIDEO_FORMATS if is_video else AUDIO_FORMATS
        target_var = self.video_fmt if is_video else self.audio_fmt

        for val, label, desc in items:
            pair = ttk.Frame(self.fmt_options_frame)
            ttk.Radiobutton(
                pair,
                text=label,
                value=val,
                variable=target_var,
                command=self.save_settings,
            ).pack(side="left")
            self.make_help_badge(pair, label, desc).pack(side="left", padx=(1, 4))

        self.update_idletasks()
        self.fmt_options_frame.rearrange()
        self.update_quality_controls()
        self.update_subtitle_controls()

    def update_quality_controls(self):
        is_video = self.media_type.get() == "video"
        use_custom = self.use_custom_res_var.get()

        if not is_video:
            self.quality_combo.configure(state="disabled")
            self.custom_res_chk.configure(state="disabled")
            self.custom_res_entry.configure(state="disabled")
        else:
            self.custom_res_chk.configure(state="normal")
            self.quality_combo.configure(state="disabled" if use_custom else "readonly")
            self.custom_res_entry.configure(state="normal" if use_custom else "disabled")

    def on_subs_toggle(self):
        self.update_subtitle_controls()
        self.save_settings()

    def on_sub_lang_change(self, event=None):
        self.update_subtitle_controls()
        self.save_settings()

    def update_subtitle_controls(self):
        is_video = self.media_type.get() == "video"
        enabled = is_video and self.subs_var.get()
        is_custom = SUB_LABEL_TO_VAL.get(self.sub_lang_label_var.get()) == "custom"

        self.subs_chk.configure(state="normal" if is_video else "disabled")
        self.sub_lang_combo.configure(state="readonly" if enabled else "disabled")
        self.custom_sub_entry.configure(state="normal" if (enabled and is_custom) else "disabled")

    def update_playlist_folder_controls(self):
        self.custom_pl_entry.configure(state="normal" if self.playlist_folder_var.get() else "disabled")

    def on_media_type_change(self):
        self.refresh_format_options()
        self.save_settings()

    def on_theme_change(self):
        self.apply_theme(force=True)
        self.save_settings()

    def get_target_dark_state(self):
        mode = self.theme_mode.get()
        if mode == "dark":
            return True
        if mode == "light":
            return False
        return is_windows_dark_mode()

    def apply_theme(self, force=False):
        is_dark = self.get_target_dark_state()
        if not force and is_dark == self._applied_dark_state:
            return
        self._applied_dark_state = is_dark

        style = ttk.Style(self)
        style.theme_use("clam")

        if is_dark:
            bg = "#18181b"
            surface = "#27272a"
            fg = "#f4f4f5"
            muted_fg = "#71717a"
            border = "#3f3f46"
            log_bg = "#09090b"
            log_fg = "#e4e4e7"
            slider_track = "#3f3f46"
            slider_thumb = "#ffffff"
        else:
            bg = "#f4f4f5"
            surface = "#ffffff"
            fg = "#18181b"
            muted_fg = "#a1a1aa"
            border = "#d4d4d8"
            log_bg = "#ffffff"
            log_fg = "#18181b"
            slider_track = "#d4d4d8"
            slider_thumb = "#ffffff"

        self.configure(bg=bg)
        self.dl_canvas.configure(bg=bg)
        set_windows_titlebar_dark(self, is_dark)

        style.configure(".", background=bg, foreground=fg, bordercolor=border, font=("Segoe UI", 9))
        style.configure("TFrame", background=bg)
        style.configure("TLabelframe", background=bg, bordercolor=border)
        style.configure("TLabelframe.Label", background=bg, foreground=fg, font=("Segoe UI", 9, "bold"))
        style.configure("TLabel", background=bg, foreground=fg)

        style.configure("TNotebook", background=bg, borderwidth=0)
        style.configure("TNotebook.Tab", background=surface, foreground=fg, padding=[14, 5], font=("Segoe UI", 9, "bold"))
        style.map(
            "TNotebook.Tab",
            background=[("selected", "#2563eb")],
            foreground=[("selected", "#ffffff")],
        )

        style.configure("TRadiobutton", background=bg, foreground=fg, indicatorbackground=surface, indicatorforeground=fg)
        style.map(
            "TRadiobutton",
            background=[("active", bg)],
            foreground=[("disabled", muted_fg)],
            indicatorbackground=[("selected", "#2563eb"), ("disabled", bg)],
        )

        style.configure("TCheckbutton", background=bg, foreground=fg, indicatorbackground=surface, indicatorforeground=fg)
        style.map(
            "TCheckbutton",
            background=[("active", bg)],
            foreground=[("disabled", muted_fg)],
            indicatorbackground=[("selected", "#2563eb"), ("disabled", bg)],
        )

        style.configure("TButton", background=surface, foreground=fg, bordercolor=border, padding=4)
        style.map("TButton", background=[("active", border)])

        style.configure("TEntry", fieldbackground=surface, foreground=fg, insertcolor=fg, bordercolor=border)
        style.map(
            "TEntry",
            fieldbackground=[("readonly", surface), ("disabled", bg)],
            foreground=[("disabled", muted_fg)],
        )

        style.configure("TCombobox", fieldbackground=surface, background=surface, foreground=fg, arrowcolor=fg, bordercolor=border)
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", surface), ("disabled", bg)],
            foreground=[("readonly", fg), ("disabled", muted_fg)],
        )

        style.configure("TSpinbox", fieldbackground=surface, foreground=fg, insertcolor=fg, arrowcolor=fg, bordercolor=border)
        style.configure("Vertical.TScrollbar", background=surface, troughcolor=bg, arrowcolor=fg, bordercolor=border)
        style.configure("Horizontal.TScrollbar", background=surface, troughcolor=bg, arrowcolor=fg, bordercolor=border)
        style.configure("Horizontal.TProgressbar", background="#3b82f6", troughcolor=surface, bordercolor=border)

        style.configure("Treeview", background=surface, fieldbackground=surface, foreground=fg, bordercolor=border, rowheight=24)
        style.configure("Treeview.Heading", background=bg, foreground=fg, bordercolor=border, font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#2563eb")], foreground=[("selected", "#ffffff")])

        self.log_text.configure(bg=log_bg, fg=log_fg, insertbackground=log_fg)
        self.upd_log_text.configure(bg=log_bg, fg=log_fg, insertbackground=log_fg)
        self.queue_listbox.configure(
            bg=surface, fg=fg, selectbackground="#2563eb", selectforeground="#ffffff", highlightbackground=border
        )

        self.preview_slider.set_theme(bg, slider_track, "#3b82f6", slider_thumb)
        self.vol_slider.set_theme(bg, slider_track, "#22c55e", slider_thumb)

        self.help_badges = [b for b in self.help_badges if b.winfo_exists()]
        for badge in self.help_badges:
            badge.update_colors()

    def poll_system_theme(self):
        if self.theme_mode.get() == "system":
            self.apply_theme()
        self.after(2000, self.poll_system_theme)

    def _make_spinbox(self, parent, var, to_val, from_=0, width=3):
        sb = ttk.Spinbox(
            parent,
            from_=from_,
            to=to_val,
            textvariable=var,
            width=width,
            format="%02.0f" if from_ == 0 else "%1.0f",
            command=self.save_settings,
        )

        def on_wheel(event):
            step = 1 if event.delta > 0 else -1
            new_val = max(from_, min(to_val, var.get() + step))
            var.set(new_val)
            self.save_settings()

        sb.bind("<MouseWheel>", on_wheel)
        return sb

    def paste_url(self):
        try:
            clip = self.clipboard_get().strip()
        except tk.TclError:
            return
        lines = [ln.strip().replace('"', "") for ln in clip.splitlines() if ln.strip()]
        if len(lines) > 1:
            for ln in lines:
                if ln not in self.download_queue:
                    self.download_queue.append(ln)
            self.refresh_queue_ui()
        elif lines:
            self.url_var.set(lines[0])

    def browse_dir(self):
        chosen = filedialog.askdirectory(initialdir=self.save_dir_var.get())
        if chosen:
            self.save_dir_var.set(os.path.normpath(chosen))
            self.save_settings()

    def open_save_dir(self):
        folder = self.save_dir_var.get()
        if os.path.isdir(folder):
            os.startfile(folder)

    def on_scope_change(self):
        self.update_scope_visibility()
        self.save_settings()

    def update_scope_visibility(self):
        self.dur_panel.pack_forget()
        self.play_panel.pack_forget()
        choice = self.range_choice.get()
        if choice == "2":
            self.dur_panel.pack(fill="x", padx=20, pady=4)
            self.update_idletasks()
            self.dur_panel.rearrange()
        elif choice == "3":
            self.play_panel.pack(fill="x", pady=4)

    # ========================================================================
    # DEPENDENCY & YT-DLP VERSION CHECKS
    # ========================================================================
    def get_binary_status(self, exe_name):
        local_path = os.path.join(APP_DIR, exe_name)
        if exe_name == "yt-dlp.exe":
            if os.path.exists(local_path):
                return f"✔ {exe_name}: Using App Folder — {local_path}"
            global_yt = find_global_binary(exe_name)
            if global_yt:
                return f"✔ {exe_name}: Using PC Global PATH — {global_yt}"
            return f"✖ {exe_name}: NOT FOUND"

        global_path = find_global_binary(exe_name)
        if global_path:
            if os.path.isfile(local_path):
                try:
                    os.remove(local_path)
                    return f"✔ {exe_name}: Using PC Global PATH — {global_path} (Auto-deleted local folder copy)"
                except OSError:
                    pass
            return f"✔ {exe_name}: Using PC Global PATH (Preferred) — {global_path}"

        if os.path.exists(local_path):
            return f"✔ {exe_name}: Using Bundled Fallback (App Folder) — {local_path}"
        return f"✖ {exe_name}: NOT FOUND"

    def check_ytdlp_version(self):
        self.cleanup_redundant_local_binaries()
        self.version_var.set("yt-dlp version: Checking...")
        if hasattr(self, "upd_log_text"):
            self.upd_log_text.delete("1.0", "end")
            self.upd_log_text.insert("end", "=== Dependency Source Check (Global PATH Preferred) ===\n")
            for msg in self.cleaned_logs:
                self.upd_log_text.insert("end", msg + "\n")
            self.cleaned_logs.clear()
            for bin_name in ("yt-dlp.exe", "ffmpeg.exe", "ffprobe.exe", "node.exe"):
                self.upd_log_text.insert("end", self.get_binary_status(bin_name) + "\n")
            self.upd_log_text.insert("end", "=======================================================\n\n")
        threading.Thread(target=self._version_worker, daemon=True).start()

    def _version_worker(self):
        try:
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            out = subprocess.check_output(
                [self.get_ytdlp_exe(), "--version"],
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=creation_flags,
            ).strip()
            self.after(0, lambda: self.version_var.set(f"Installed yt-dlp version: {out}"))
        except FileNotFoundError:
            self.after(0, lambda: self.version_var.set("yt-dlp.exe not found in app folder"))
        except Exception as e:
            self.after(0, lambda: self.version_var.set(f"Error checking version: {e}"))

    def update_ytdlp(self):
        self.upd_btn.config(state="disabled")
        self.upd_log_text.delete("1.0", "end")
        self.upd_log_text.insert("end", "Checking for yt-dlp updates (yt-dlp -U)...\n\n")
        threading.Thread(target=self._update_worker, daemon=True).start()

    def _update_worker(self):
        try:
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            proc = subprocess.Popen(
                [self.get_ytdlp_exe(), "-U"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creation_flags,
            )
            for line in proc.stdout:
                self.after(0, self._append_upd_log, line)
            proc.wait()
            self.after(0, self.check_ytdlp_version)
        except Exception as e:
            self.after(0, self._append_upd_log, f"\nUpdate failed: {e}\n")
        finally:
            self.after(0, lambda: self.upd_btn.config(state="normal"))

    def _append_upd_log(self, text):
        self.upd_log_text.insert("end", text)
        self.upd_log_text.see("end")

    # ========================================================================
    # SETTINGS PERSISTENCE
    # ========================================================================
    def save_settings(self):
        data = {
            "save_dir": self.save_dir_var.get(),
            "media_type": self.media_type.get(),
            "video_fmt": self.video_fmt.get(),
            "audio_fmt": self.audio_fmt.get(),
            "quality_choice": QUALITY_LABEL_TO_VAL.get(self.quality_label_var.get(), "best"),
            "range_choice": self.range_choice.get(),
            "sh": self.sh_var.get(),
            "sm": self.sm_var.get(),
            "ss": self.ss_var.get(),
            "eh": self.eh_var.get(),
            "em": self.em_var.get(),
            "es": self.es_var.get(),
            "use_p_start": self.use_p_start.get(),
            "p_start": self.p_start_var.get(),
            "use_p_end": self.use_p_end.get(),
            "p_end": self.p_end_var.get(),
            "remove_link_title": self.remove_link_title_var.get(),
            "playlist_numbering": self.playlist_numbering_var.get(),
            "meta": self.meta_var.get(),
            "subs": self.subs_var.get(),
            "sub_lang": SUB_LABEL_TO_VAL.get(self.sub_lang_label_var.get(), "en.*,en"),
            "custom_sub_lang": self.custom_sub_lang_var.get(),
            "cookie_browser": COOKIE_LABEL_TO_VAL.get(self.cookie_browser_label_var.get(), "none"),
            "theme_mode": self.theme_mode.get(),
        }
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError:
            pass

    def load_settings(self):
        if not os.path.exists(SETTINGS_FILE):
            return
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.save_dir_var.set(data.get("save_dir", DEFAULT_SAVE_DIR))
            self.media_type.set(data.get("media_type", "video"))
            self.video_fmt.set(data.get("video_fmt", "mp4"))
            self.audio_fmt.set(data.get("audio_fmt", "mp3"))
            q_val = data.get("quality_choice", "best")
            self.quality_label_var.set(QUALITY_VAL_TO_LABEL.get(q_val, "Auto (Best)"))
            self.range_choice.set(data.get("range_choice", "1"))
            self.sh_var.set(data.get("sh", 0))
            self.sm_var.set(data.get("sm", 1))
            self.ss_var.set(data.get("ss", 0))
            self.eh_var.set(data.get("eh", 0))
            self.em_var.set(data.get("em", 2))
            self.es_var.set(data.get("es", 0))
            self.use_p_start.set(data.get("use_p_start", True))
            self.p_start_var.set(data.get("p_start", 1))
            self.use_p_end.set(data.get("use_p_end", True))
            self.p_end_var.set(data.get("p_end", 5))
            self.remove_link_title_var.set(data.get("remove_link_title", False))
            self.playlist_numbering_var.set(data.get("playlist_numbering", False))
            self.meta_var.set(data.get("meta", False))
            self.subs_var.set(data.get("subs", False))
            sub_val = data.get("sub_lang", "en.*,en")
            self.sub_lang_label_var.set(SUB_VAL_TO_LABEL.get(sub_val, "English (en)"))
            self.custom_sub_lang_var.set(data.get("custom_sub_lang", "en,id"))
            ck_val = data.get("cookie_browser", "none")
            self.cookie_browser_label_var.set(COOKIE_VAL_TO_LABEL.get(ck_val, "None"))
            self.theme_mode.set(data.get("theme_mode", "system"))
        except Exception:
            pass

    def on_close(self):
        if self.is_downloading:
            self.cancel_download()
        self.stop_preview_streams()
        self.save_settings()
        self.destroy()


if __name__ == "__main__":
    app = YtDlpApp()
    app.mainloop()