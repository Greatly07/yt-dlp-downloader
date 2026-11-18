import os
import sys
import json
import shutil
import threading
import subprocess
import urllib.request
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ============================================================================
# APP VERSION & GITHUB REPOSITORY CONFIG
# ============================================================================
APP_VERSION = "1.0.0"
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

PREVIEW_W = 360
PREVIEW_H = 202
PREVIEW_FPS = 15

VIDEO_FORMATS = [
    (
        "mp4",
        "MP4 (Standard)",
        "MP4 (MPEG-4 Part 14)\n\n"
        "• Best all-around video format.\n"
        "• Plays on almost every phone, TV, tablet, web browser, and video editor.\n"
        "• Combines H.264/AVC or AV1 video with M4A (AAC) audio.",
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
    "meta": (
        "Cover Art & Media Info\n\n"
        "• Embeds the video thumbnail as the song/video cover image.\n"
        "• Writes the title, artist/channel name, upload date, and description into the file tags."
    ),
    "subfolder": (
        "Playlist Subfolder\n\n"
        "• Creates a dedicated folder named after the playlist inside your Save Folder.\n"
        "• Numbers each file in order (e.g., '1 - Song Title.mp3', '2 - Song Title.mp3')."
    ),
}


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
            import ctypes
            window.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
            value = ctypes.c_int(1 if is_dark else 0)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 20, ctypes.byref(value), ctypes.sizeof(value)
            )
        except Exception:
            pass


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

        lbl = tk.Label(
            frame,
            text=self.description,
            justify="left",
            bg=tip_bg,
            fg=tip_fg,
            font=("Segoe UI", 9),
            wraplength=320,
        )
        lbl.pack()

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


class YtDlpApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("yt-dlp Downloader")
        self.geometry("690x820")
        self.minsize(500, 640)
        self.resizable(True, True)

        # Apply custom .ico if available
        try:
            if os.path.exists(ICON_PATH):
                self.iconbitmap(ICON_PATH)
            elif getattr(sys, "frozen", False):
                self.iconbitmap(sys.executable)
        except Exception:
            pass

        # Downloader Variables
        self.url_var = tk.StringVar()
        self.save_dir_var = tk.StringVar(value=DEFAULT_SAVE_DIR)
        self.media_type = tk.StringVar(value="video")
        self.video_fmt = tk.StringVar(value="mp4")
        self.audio_fmt = tk.StringVar(value="mp3")
        self.quality_choice = tk.StringVar(value="best")
        self.range_choice = tk.StringVar(value="1")

        # Duration Spinbox Variables (HH:MM:SS - HH:MM:SS)
        self.sh_var = tk.IntVar(value=0)
        self.sm_var = tk.IntVar(value=1)
        self.ss_var = tk.IntVar(value=15)
        self.eh_var = tk.IntVar(value=0)
        self.em_var = tk.IntVar(value=2)
        self.es_var = tk.IntVar(value=30)

        # Playlist Variables
        self.use_p_start = tk.BooleanVar(value=False)
        self.p_start_var = tk.IntVar(value=1)
        self.use_p_end = tk.BooleanVar(value=False)
        self.p_end_var = tk.IntVar(value=5)
        self.p_folder_var = tk.BooleanVar(value=False)

        # Extra Options & Settings Variables
        self.meta_var = tk.BooleanVar(value=False)
        self.theme_mode = tk.StringVar(value="system")
        self.version_var = tk.StringVar(value="yt-dlp version: Checking...")
        self.app_ver_var = tk.StringVar(value=f"App Version: v{APP_VERSION}")

        # Video Preview State
        self.preview_proc = None
        self.preview_playing = False
        self.preview_stream_url = None
        self.preview_duration = 0.0
        self.preview_pos = 0.0
        self.preview_seeking = False
        self.preview_photo = None
        self.preview_session_id = 0

        self._pending_cr = False
        self._applied_dark_state = None
        self.quality_radios = []
        self.help_badges = []
        self.cleaned_logs = []

        self.load_settings()
        self.cleanup_redundant_local_binaries()
        self.build_ui()
        self.refresh_format_options()
        self.update_scope_visibility()
        self.apply_theme(force=True)
        self.poll_system_theme()
        self.after(300, self.check_ytdlp_version)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def cleanup_redundant_local_binaries(self):
        """Removes ffmpeg, ffprobe, and node from APP_DIR if a global PATH version exists."""
        for exe_name in ("ffmpeg.exe", "ffprobe.exe", "node.exe"):
            global_path = find_global_binary(exe_name)
            local_path = os.path.join(APP_DIR, exe_name)
            if global_path and os.path.isfile(local_path):
                try:
                    os.remove(local_path)
                    self.cleaned_logs.append(
                        f"🧹 Removed local {exe_name} from App Folder (using Global PATH: {global_path})"
                    )
                except OSError as e:
                    self.cleaned_logs.append(
                        f"⚠ Could not remove local {exe_name} ({e})"
                    )

    def make_help_badge(self, parent, title, description):
        badge = HelpBadge(parent, title, description, self)
        self.help_badges.append(badge)
        return badge

    def build_ui(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self.dl_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.dl_tab, text="  Downloader  ")
        self.notebook.add(self.settings_tab, text="  Settings & Updates  ")

        self.build_downloader_tab()
        self.build_settings_tab()

    def build_downloader_tab(self):
        pad = {"padx": 10, "pady": 4}

        # 1. Link & Video Preview Section
        self.url_frame = ttk.LabelFrame(self.dl_tab, text="1. Video or Playlist Link")
        self.url_frame.pack(fill="x", **pad)

        url_top_row = ttk.Frame(self.url_frame)
        url_top_row.pack(fill="x")

        self.url_entry = ttk.Entry(url_top_row, textvariable=self.url_var, font=("Segoe UI", 10))
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(8, 4), pady=7)

        ttk.Button(url_top_row, text="Paste", width=7, command=self.paste_url).pack(side="left", padx=2, pady=7)
        ttk.Button(url_top_row, text="Clear", width=6, command=self.clear_url).pack(side="left", padx=2, pady=7)
        self.preview_btn = ttk.Button(url_top_row, text="Preview", width=9, command=self.start_preview)
        self.preview_btn.pack(side="left", padx=(2, 8), pady=7)

        # Collapsible Preview Panel
        self.preview_box = ttk.Frame(self.url_frame)

        self.preview_header = ttk.Frame(self.preview_box)
        self.preview_header.pack(fill="x", padx=8, pady=(0, 4))
        self.preview_title_lbl = ttk.Label(
            self.preview_header, text="", font=("Segoe UI", 9, "bold"), wraplength=520
        )
        self.preview_title_lbl.pack(side="left", fill="x", expand=True)
        ttk.Button(self.preview_header, text="Close Preview", width=13, command=self.close_preview).pack(side="right")

        self.preview_msg_lbl = ttk.Label(
            self.preview_box, text="", font=("Segoe UI", 9), justify="center", anchor="center"
        )

        self.preview_player_frame = ttk.Frame(self.preview_box)

        self.video_canvas_lbl = tk.Label(
            self.preview_player_frame, bg="#000000", width=PREVIEW_W, height=PREVIEW_H
        )
        self.video_canvas_lbl.pack(pady=(2, 4))

        ctrl_row = ttk.Frame(self.preview_player_frame)
        ctrl_row.pack(fill="x", padx=12, pady=(0, 6))

        self.play_pause_btn = ttk.Button(
            ctrl_row, text="Pause", width=7, command=self.toggle_preview_play
        )
        self.play_pause_btn.pack(side="left", padx=(0, 6))

        self.preview_scale_var = tk.DoubleVar(value=0.0)
        self.preview_scale = ttk.Scale(
            ctrl_row,
            from_=0.0,
            to=100.0,
            orient="horizontal",
            variable=self.preview_scale_var,
            command=self.on_preview_scrub_move,
        )
        self.preview_scale.pack(side="left", fill="x", expand=True, padx=4)
        self.preview_scale.bind("<ButtonPress-1>", self.on_preview_scrub_start)
        self.preview_scale.bind("<ButtonRelease-1>", self.on_preview_scrub_end)

        self.preview_time_lbl = ttk.Label(ctrl_row, text="00:00 / 00:00", font=("Consolas", 9))
        self.preview_time_lbl.pack(side="left", padx=(6, 0))

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
        self.qual_frame = ttk.LabelFrame(self.dl_tab, text="3. Video Quality (Uses highest available if video is lower)")
        self.qual_frame.pack(fill="x", **pad)

        qual_row = WrapFrame(self.qual_frame, padx=6, pady=3)
        qual_row.pack(fill="x", padx=8, pady=5)

        qualities = [
            ("best", "Auto (Best)"),
            ("2160", "4K"),
            ("1440", "1440p"),
            ("1080", "1080p"),
            ("720", "720p"),
            ("480", "480p"),
            ("360", "360p"),
        ]
        for val, label in qualities:
            rb = ttk.Radiobutton(
                qual_row, text=label, value=val, variable=self.quality_choice, command=self.save_settings
            )
            self.quality_radios.append(rb)

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

        # Sub-panel: Duration Spinboxes
        self.dur_panel = WrapFrame(scope_frame, padx=3, pady=3)
        ttk.Label(self.dur_panel, text="From (H:M:S):")
        self._make_spinbox(self.dur_panel, self.sh_var, 23)
        self._make_spinbox(self.dur_panel, self.sm_var, 59)
        self._make_spinbox(self.dur_panel, self.ss_var, 59)
        ttk.Label(self.dur_panel, text="   To (H:M:S):")
        self._make_spinbox(self.dur_panel, self.eh_var, 23)
        self._make_spinbox(self.dur_panel, self.em_var, 59)
        self._make_spinbox(self.dur_panel, self.es_var, 59)

        # Sub-panel: Playlist Range Controls
        self.play_panel = ttk.Frame(scope_frame)
        row_p = WrapFrame(self.play_panel, padx=4, pady=2)
        row_p.pack(fill="x", padx=20, pady=2)

        ttk.Checkbutton(row_p, text="Start at video #:", variable=self.use_p_start, command=self.save_settings)
        self._make_spinbox(row_p, self.p_start_var, 999, from_=1, width=4)
        ttk.Checkbutton(row_p, text="   Stop at video #:", variable=self.use_p_end, command=self.save_settings)
        self._make_spinbox(row_p, self.p_end_var, 999, from_=1, width=4)

        subf_row = ttk.Frame(self.play_panel)
        subf_row.pack(anchor="w", padx=24, pady=(2, 6))
        ttk.Checkbutton(
            subf_row,
            text="Put playlist videos in their own folder",
            variable=self.p_folder_var,
            command=self.save_settings,
        ).pack(side="left")
        self.make_help_badge(subf_row, "Playlist Subfolder", EXTRA_HELP["subfolder"]).pack(side="left", padx=4)

        # 5. Extra Options & Save Location
        meta_frame = ttk.LabelFrame(self.dl_tab, text="5. Extras & Save Folder")
        meta_frame.pack(fill="x", **pad)

        meta_row = ttk.Frame(meta_frame)
        meta_row.pack(anchor="w", padx=10, pady=(4, 5))
        ttk.Checkbutton(
            meta_row,
            text="Include cover art and media info (title, artist, date)",
            variable=self.meta_var,
            command=self.save_settings,
        ).pack(side="left")
        self.make_help_badge(meta_row, "Cover Art & Media Info", EXTRA_HELP["meta"]).pack(side="left", padx=4)

        dir_row = ttk.Frame(meta_frame)
        dir_row.pack(fill="x", padx=10, pady=(0, 7))
        ttk.Label(dir_row, text="Save to:").pack(side="left")
        ttk.Entry(dir_row, textvariable=self.save_dir_var, state="readonly").pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(dir_row, text="Change...", command=self.browse_dir).pack(side="left", padx=(0, 4))
        ttk.Button(dir_row, text="Open Folder", command=self.open_save_dir).pack(side="left")

        # 6. Action Button
        btn_frame = ttk.Frame(self.dl_tab)
        btn_frame.pack(fill="x", padx=10, pady=5)

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
            command=self.start_download,
        )
        self.dl_btn.pack(fill="x", expand=True)

        # 7. Progress Log
        log_frame = ttk.LabelFrame(self.dl_tab, text="Progress Log")
        log_frame.pack(fill="both", expand=True, **pad)

        log_inner = ttk.Frame(log_frame)
        log_inner.pack(fill="both", expand=True, padx=6, pady=6)

        self.log_scroll = ttk.Scrollbar(log_inner, orient="vertical")
        self.log_scroll.pack(side="right", fill="y")

        self.log_text = tk.Text(
            log_inner,
            height=7,
            font=("Consolas", 9),
            wrap="word",
            yscrollcommand=self.log_scroll.set,
            relief="flat",
            padx=6,
            pady=6,
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        self.log_scroll.config(command=self.log_text.yview)

    def build_settings_tab(self):
        pad = {"padx": 14, "pady": 6}

        # Appearance / Theme Section
        theme_frame = ttk.LabelFrame(self.settings_tab, text="Appearance")
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

        # App Self-Updater (GitHub)
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

        # yt-dlp Version & Updates Section
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
            height=10,
            font=("Consolas", 9),
            wrap="word",
            yscrollcommand=upd_scroll.set,
            relief="flat",
            padx=6,
            pady=6,
        )
        self.upd_log_text.pack(side="left", fill="both", expand=True)
        upd_scroll.config(command=self.upd_log_text.yview)

    # ========================================================================
    # VIDEO PREVIEW ENGINE
    # ========================================================================
    def start_preview(self):
        url = self.url_var.get().strip().replace('"', "")
        if not url:
            messagebox.showwarning("Missing Link", "Paste a link first before clicking Preview.")
            return

        self.stop_preview_stream()
        self.preview_session_id += 1
        session_id = self.preview_session_id

        self.preview_box.pack(fill="x", padx=8, pady=(0, 8))
        self.preview_player_frame.pack_forget()
        self.preview_title_lbl.config(text="Checking link...")
        self.preview_msg_lbl.config(text="Fetching media info, please wait...")
        self.preview_msg_lbl.pack(fill="x", padx=12, pady=12)
        self.preview_btn.config(state="disabled")

        threading.Thread(target=self._preview_info_worker, args=(url, session_id), daemon=True).start()

    def _preview_info_worker(self, url, session_id):
        try:
            cmd = [self.get_ytdlp_exe(), "--dump-single-json", "--flat-playlist", "--no-warnings"]
            node_exe = self.get_node_exe()
            if node_exe:
                cmd += ["--js-runtimes", f"node:{node_exe}"]
            cmd.append(url)

            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            out = subprocess.check_output(
                cmd, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", creationflags=creation_flags
            )
            json_line = [line for line in out.splitlines() if line.strip().startswith("{")][-1]
            data = json.loads(json_line)
            self.after(0, self._handle_preview_metadata, data, url, session_id)
        except Exception as e:
            self.after(
                0,
                self._show_preview_message,
                "Could not load preview",
                f"Unable to read media info for this link.\n({e})",
                session_id,
            )

    def _handle_preview_metadata(self, data, url, session_id):
        if session_id != self.preview_session_id:
            return
        self.preview_btn.config(state="normal")

        title = data.get("title") or "Untitled Media"

        if data.get("_type") in ("playlist", "multi_video") or "entries" in data:
            entries = data.get("entries") or []
            count = data.get("playlist_count") or len(entries)
            self._show_preview_message(
                f"Playlist: {title}",
                f"Playlist link detected ({count} items).\nVideo preview is not available for playlist links.",
                session_id,
            )
            return

        formats = data.get("formats") or []
        video_formats = [
            f
            for f in formats
            if f.get("vcodec") not in (None, "none", "images") and f.get("url")
        ]
        if data.get("vcodec") == "none" or not video_formats:
            self._show_preview_message(
                f"Audio Track: {title}",
                "This link is audio-only and does not contain a video stream to preview.",
                session_id,
            )
            return

        ffmpeg_exe = self.get_ffmpeg_exe()
        if not ffmpeg_exe:
            self._show_preview_message(
                title,
                "ffmpeg.exe is required to play the video preview, but it was not found.",
                session_id,
            )
            return

        preferred = [
            f for f in video_formats if (f.get("height") or 9999) <= 480 and f.get("ext") in ("mp4", "webm")
        ]
        chosen_fmt = preferred[-1] if preferred else video_formats[0]

        self.preview_stream_url = chosen_fmt["url"]
        self.preview_duration = float(data.get("duration") or 0.0)
        self.preview_pos = 0.0

        self.preview_msg_lbl.pack_forget()
        self.preview_title_lbl.config(text=title)
        self.preview_scale.configure(to=max(1.0, self.preview_duration))
        self.preview_scale_var.set(0.0)
        self.preview_time_lbl.config(text=f"00:00 / {format_seconds(self.preview_duration)}")
        self.preview_player_frame.pack(fill="x")

        self.start_preview_stream_at(0.0)

    def _show_preview_message(self, header_text, body_text, session_id):
        if session_id != self.preview_session_id:
            return
        self.preview_btn.config(state="normal")
        self.preview_player_frame.pack_forget()
        self.preview_title_lbl.config(text=header_text)
        self.preview_msg_lbl.config(text=body_text)
        self.preview_msg_lbl.pack(fill="x", padx=12, pady=12)

    def start_preview_stream_at(self, start_sec):
        self.stop_preview_stream()
        if not self.preview_stream_url:
            return

        self.preview_pos = max(0.0, min(start_sec, self.preview_duration))
        self.preview_playing = True
        self.play_pause_btn.config(text="Pause")
        self.preview_session_id += 1
        session_id = self.preview_session_id

        threading.Thread(
            target=self._ffmpeg_stream_worker,
            args=(self.preview_stream_url, self.preview_pos, session_id),
            daemon=True,
        ).start()

    def _ffmpeg_stream_worker(self, stream_url, start_sec, session_id):
        ffmpeg_exe = self.get_ffmpeg_exe()
        if not ffmpeg_exe:
            return

        vf_str = (
            f"scale={PREVIEW_W}:{PREVIEW_H}:force_original_aspect_ratio=decrease,"
            f"pad={PREVIEW_W}:{PREVIEW_H}:(ow-iw)/2:(oh-ih)/2"
        )
        cmd = [
            ffmpeg_exe,
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
            "quiet",
            "-",
        ]

        try:
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                creationflags=creation_flags,
            )
            self.preview_proc = proc

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

                ppm_frame = magic + dims + maxval + pixel_bytes
                cur_time = start_sec + (1.0 / PREVIEW_FPS)
                start_sec = cur_time
                self.after(0, self._render_preview_frame, ppm_frame, cur_time, session_id)
        except Exception:
            pass

    def _render_preview_frame(self, ppm_frame, cur_time, session_id):
        if session_id != self.preview_session_id or not self.preview_playing:
            return
        try:
            self.preview_photo = tk.PhotoImage(data=ppm_frame)
            self.video_canvas_lbl.configure(image=self.preview_photo)
            self.preview_pos = min(cur_time, self.preview_duration)
            if not self.preview_seeking:
                self.preview_scale_var.set(self.preview_pos)
                self.preview_time_lbl.config(
                    text=f"{format_seconds(self.preview_pos)} / {format_seconds(self.preview_duration)}"
                )
        except Exception:
            pass

    def toggle_preview_play(self):
        if not self.preview_stream_url:
            return
        if self.preview_playing:
            self.stop_preview_stream()
            self.play_pause_btn.config(text="Play")
        else:
            self.start_preview_stream_at(self.preview_pos)

    def on_preview_scrub_start(self, event=None):
        self.preview_seeking = True

    def on_preview_scrub_move(self, val):
        if self.preview_seeking:
            sec = float(val)
            self.preview_time_lbl.config(
                text=f"{format_seconds(sec)} / {format_seconds(self.preview_duration)}"
            )

    def on_preview_scrub_end(self, event=None):
        if not self.preview_seeking:
            return
        self.preview_seeking = False
        target_sec = float(self.preview_scale_var.get())
        self.start_preview_stream_at(target_sec)

    def stop_preview_stream(self):
        self.preview_playing = False
        proc = self.preview_proc
        self.preview_proc = None
        if proc and proc.poll() is None:
            try:
                proc.kill()
            except Exception:
                pass

    def close_preview(self):
        self.preview_session_id += 1
        self.stop_preview_stream()
        self.preview_stream_url = None
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

            self.after(
                0,
                self._prompt_and_install_app_update,
                latest_tag,
                dl_url,
            )
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
    # CORE DOWNLOADER & BINARY RESOLUTION (PREFERS GLOBAL PATH)
    # ========================================================================
    def get_ytdlp_exe(self):
        return YTDLP_PATH if os.path.exists(YTDLP_PATH) else (find_global_binary("yt-dlp.exe") or "yt-dlp")

    def get_ffmpeg_exe(self):
        """Prefers global PATH ffmpeg.exe; falls back to APP_DIR copy."""
        global_ff = find_global_binary("ffmpeg.exe")
        if global_ff:
            return global_ff
        if os.path.exists(FFMPEG_PATH):
            return FFMPEG_PATH
        return None

    def get_node_exe(self):
        """Prefers global PATH node.exe; falls back to APP_DIR copy."""
        global_node = find_global_binary("node.exe")
        if global_node:
            return global_node
        if os.path.exists(NODE_PATH):
            return NODE_PATH
        return None

    def build_command(self, url):
        self.cleanup_redundant_local_binaries()
        cmd = [self.get_ytdlp_exe(), "--progress"]

        ffmpeg_exe = self.get_ffmpeg_exe()
        if ffmpeg_exe:
            cmd += ["--ffmpeg-location", os.path.dirname(ffmpeg_exe)]

        node_exe = self.get_node_exe()
        if node_exe:
            cmd += ["--js-runtimes", f"node:{node_exe}"]

        is_video = self.media_type.get() == "video"
        qual = self.quality_choice.get()

        if is_video:
            vfmt = self.video_fmt.get()
            h_filter = "" if qual == "best" else f"[height<={qual}]"

            if vfmt == "mp4":
                cmd += [
                    "-f",
                    f"bestvideo{h_filter}[ext=mp4]+bestaudio[ext=m4a]/best{h_filter}[ext=mp4]/best{h_filter}",
                    "--merge-output-format",
                    "mp4",
                ]
            elif vfmt == "webm":
                cmd += [
                    "-f",
                    f"bestvideo{h_filter}[ext=webm]+bestaudio[ext=webm]/best{h_filter}[ext=webm]/best{h_filter}",
                ]
            elif vfmt == "mkv":
                cmd += [
                    "-f",
                    f"bestvideo{h_filter}+bestaudio/best{h_filter}",
                    "--merge-output-format",
                    "mkv",
                ]
            elif vfmt == "mov":
                cmd += [
                    "-f",
                    f"bestvideo{h_filter}[ext=mp4]+bestaudio[ext=m4a]/best{h_filter}",
                    "--remux-video",
                    "mov",
                ]
        else:
            afmt = self.audio_fmt.get()
            if afmt == "orig":
                cmd += ["-f", "ba"]
            else:
                cmd += ["-x", "--audio-format", afmt]

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
            if self.p_folder_var.get():
                cmd += ["-o", "%(playlist_title)s/%(playlist_index)s - %(title)s.%(ext)s"]

        if self.meta_var.get():
            cmd += ["--embed-thumbnail", "--embed-metadata"]

        cmd.append(url)
        return cmd

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

        state = "normal" if is_video else "disabled"
        for rb in self.quality_radios:
            rb.configure(state=state)

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
        else:
            bg = "#f4f4f5"
            surface = "#ffffff"
            fg = "#18181b"
            muted_fg = "#a1a1aa"
            border = "#d4d4d8"
            log_bg = "#ffffff"
            log_fg = "#18181b"

        self.configure(bg=bg)
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
        style.map("TEntry", fieldbackground=[("readonly", surface)])

        style.configure("TSpinbox", fieldbackground=surface, foreground=fg, insertcolor=fg, arrowcolor=fg, bordercolor=border)
        style.configure("Vertical.TScrollbar", background=surface, troughcolor=bg, arrowcolor=fg, bordercolor=border)
        style.configure("Horizontal.TScale", background=bg, troughcolor=surface)

        self.log_text.configure(bg=log_bg, fg=log_fg, insertbackground=log_fg)
        self.upd_log_text.configure(bg=log_bg, fg=log_fg, insertbackground=log_fg)

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
            clip = self.clipboard_get().strip().replace('"', "")
            self.url_var.set(clip)
        except tk.TclError:
            pass

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

    def start_download(self):
        url = self.url_var.get().strip().replace('"', "")
        if not url:
            messagebox.showwarning("Missing Link", "Click 'Paste' to insert a video or playlist link first.")
            return

        self.close_preview()
        self.save_settings()
        cmd = self.build_command(url)
        save_dir = self.save_dir_var.get()
        os.makedirs(save_dir, exist_ok=True)

        self.dl_btn.config(state="disabled")
        self.log_text.delete("1.0", "end")
        self._pending_cr = False
        self.log_raw(f"Saving to: {save_dir}\nRunning: {' '.join(cmd)}\n" + "=" * 56 + "\n")

        threading.Thread(target=self._run_process, args=(cmd, save_dir), daemon=True).start()

    def _run_process(self, cmd, save_dir):
        try:
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            proc = subprocess.Popen(
                cmd,
                cwd=save_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=creation_flags,
            )
            while True:
                chunk = proc.stdout.read1(1024)
                if not chunk:
                    break
                text = chunk.decode("utf-8", errors="replace")
                self.after(0, self.log_raw, text)

            proc.wait()
            status = (
                "\n========================================================\nDownload complete!\n"
                if proc.returncode == 0
                else f"\nProcess exited with code {proc.returncode}\n"
            )
            self.after(0, self.log_raw, status)
        except FileNotFoundError:
            self.after(0, self.log_raw, f"\nError: Could not find yt-dlp.exe in {APP_DIR}\n")
        except Exception as e:
            self.after(0, self.log_raw, f"\nError: {e}\n")
        finally:
            self.after(0, self._enable_buttons)

    def _enable_buttons(self):
        self.dl_btn.config(state="normal")

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

        # For ffmpeg, ffprobe, and node: Prefer Global PATH and auto-delete local copy
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
            "quality_choice": self.quality_choice.get(),
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
            "p_folder": self.p_folder_var.get(),
            "meta": self.meta_var.get(),
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
            self.quality_choice.set(data.get("quality_choice", "best"))
            self.range_choice.set(data.get("range_choice", "1"))
            self.sh_var.set(data.get("sh", 0))
            self.sm_var.set(data.get("sm", 1))
            self.ss_var.set(data.get("ss", 15))
            self.eh_var.set(data.get("eh", 0))
            self.em_var.set(data.get("em", 2))
            self.es_var.set(data.get("es", 30))
            self.use_p_start.set(data.get("use_p_start", False))
            self.p_start_var.set(data.get("p_start", 1))
            self.use_p_end.set(data.get("use_p_end", False))
            self.p_end_var.set(data.get("p_end", 5))
            self.p_folder_var.set(data.get("p_folder", False))
            self.meta_var.set(data.get("meta", False))
            self.theme_mode.set(data.get("theme_mode", "system"))
        except Exception:
            pass

    def on_close(self):
        self.stop_preview_stream()
        self.save_settings()
        self.destroy()


if __name__ == "__main__":
    app = YtDlpApp()
    app.mainloop()