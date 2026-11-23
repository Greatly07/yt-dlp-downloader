import os
import sys
import json
import shutil
import threading
import subprocess
import webbrowser
import urllib.request
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

from .config import (
    APP_VERSION,
    GITHUB_REPO,
    APP_DIR,
    DEFAULT_SAVE_DIR,
    FFMPEG_PATH,
    FFPROBE_PATH,
    NODE_PATH,
    ICON_PATH,
    SETTINGS_FILE,
    HISTORY_FILE,
    PRESETS_FILE,
    PREVIEW_W,
    PREVIEW_H,
    LOG_MIN_HEIGHT,
    LOG_MAX_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    DEFAULT_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    MIN_WINDOW_HEIGHT,
    DEFAULT_PRESETS,
    QUALITY_PRESETS,
    QUALITY_LABEL_TO_VAL,
    QUALITY_VAL_TO_LABEL,
    AUDIO_QUALITY_PRESETS,
    AUDIO_QUALITY_LABEL_TO_VAL,
    AUDIO_QUALITY_VAL_TO_LABEL,
    SUB_LANG_PRESETS,
    SUB_LABEL_TO_VAL,
    SUB_VAL_TO_LABEL,
    COOKIE_BROWSERS,
    COOKIE_LABEL_TO_VAL,
    COOKIE_VAL_TO_LABEL,
    DEPENDENCY_PREF_MODES,
    DEP_PREF_LABEL_TO_VAL,
    DEP_PREF_VAL_TO_LABEL,
    THEME_MODES,
    THEME_LABEL_TO_VAL,
    THEME_VAL_TO_LABEL,
    VIDEO_FORMATS,
    AUDIO_FORMATS,
    EXTRA_HELP,
)
from .utils import (
    is_windows_dark_mode,
    set_windows_titlebar_dark,
    apply_high_dpi_window_icon,
    find_downloaded_file_fallback,
    find_global_binary,
)
from .audio_player import WaveOutPlayer
from .widgets import (
    get_palette,
    ModernScrollbar,
    RoundedCard,
    RoundedButton,
    TopNavButton,
    SongPulseDropdown,
    SongPulseCheckbox,
    SongPulseRadio,
    ModernSlider,
    HelpBadge,
    WrapFrame,
)
from .dependencies import (
    resolve_ytdlp_exe,
    resolve_binary,
    describe_binary_status,
    download_ffmpeg_to_app_dir,
    download_nodejs_to_app_dir,
    cleanup_local_dependencies,
    register_songpulse_protocol,
    is_songpulse_protocol_registered,
)
from .preview import PreviewMixin
from .downloader import DownloaderMixin

# Format Lookup Maps for the Format Dropdown
VIDEO_FMT_LABEL_TO_VAL = {lbl: val for val, lbl, _ in VIDEO_FORMATS}
VIDEO_FMT_VAL_TO_LABEL = {val: lbl for val, lbl, _ in VIDEO_FORMATS}
VIDEO_FMT_DESC_MAP = {lbl: desc for _, lbl, desc in VIDEO_FORMATS}

AUDIO_FMT_LABEL_TO_VAL = {lbl: val for val, lbl, _ in AUDIO_FORMATS}
AUDIO_FMT_VAL_TO_LABEL = {val: lbl for val, lbl, _ in AUDIO_FORMATS}
AUDIO_FMT_DESC_MAP = {lbl: desc for _, lbl, desc in AUDIO_FORMATS}


class YtDlpApp(tk.Tk, PreviewMixin, DownloaderMixin):
    def __init__(self, startup_job=None):
        super().__init__()
        self.startup_job = startup_job
        self.title("yt-dlp Downloader")
        self.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.resizable(True, True)

        try:
            if os.path.exists(ICON_PATH):
                self.iconbitmap(ICON_PATH)
                apply_high_dpi_window_icon(self, ICON_PATH)
            elif getattr(sys, "frozen", False):
                self.iconbitmap(sys.executable)
        except Exception:
            pass

        # Active Navbar Tab Index (0: Downloader, 1: History, 2: Settings, 3: About / Info)
        self.active_page_idx = 0
        self.advanced_mode_open = False

        # Window Size Persistence State
        self.remember_win_size_var = tk.BooleanVar(value=False)
        self.saved_win_width = DEFAULT_WINDOW_WIDTH
        self.saved_win_height = DEFAULT_WINDOW_HEIGHT

        # Downloader Variables (Saved Options)
        self.url_var = tk.StringVar()
        self.save_dir_var = tk.StringVar(value=DEFAULT_SAVE_DIR)
        self.media_type = tk.StringVar(value="video")
        self.video_fmt = tk.StringVar(value="mp4")
        self.audio_fmt = tk.StringVar(value="mp3")
        self.format_label_var = tk.StringVar(value="MP4 (Standard)")
        self.quality_label_var = tk.StringVar(value="Auto (Best)")
        self.audio_quality_label_var = tk.StringVar(value="Auto (Best Audio)")
        self.range_choice = tk.StringVar(value="1")

        # Non-Saved Session Defaults (Playlist defaults to False for single Video/Music until Playlist preset is toggled on)
        self.custom_title_var = tk.StringVar(value="")
        self.use_custom_res_var = tk.BooleanVar(value=False)
        self.custom_res_var = tk.StringVar(value="")
        self.playlist_folder_var = tk.BooleanVar(value=False)
        self.custom_playlist_folder_var = tk.StringVar(value="")
        self.batch_as_playlist_var = tk.BooleanVar(value=False)

        # Saved Naming, Subtitles & Metadata Options (meta_var and remove_link_title_var default to True)
        self.remove_link_title_var = tk.BooleanVar(value=True)
        self.playlist_numbering_var = tk.BooleanVar(value=False)
        self.meta_var = tk.BooleanVar(value=True)
        self.subs_var = tk.BooleanVar(value=False)
        self.sub_lang_label_var = tk.StringVar(value="English (en)")
        self.custom_sub_lang_var = tk.StringVar(value="en,id")

        # Authentication / Cookies (In Settings)
        self.cookie_browser_label_var = tk.StringVar(value="None (Disabled)")
        self.use_cookie_file_var = tk.BooleanVar(value=False)
        self.cookie_file_path_var = tk.StringVar(value="")

        # Dependency Preference (Global PATH vs App Folder)
        self.dep_pref_label_var = tk.StringVar(
            value="Prefer System Global PATH (Fallback to App Folder)"
        )

        # Presets State (custom_presets holds ONLY user-saved custom presets; built-in presets are on the 3 quick buttons)
        self.custom_presets = {}
        self.custom_preset_var = tk.StringVar(value="None")
        self.preset_desc_var = tk.StringVar(value="")

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
        self.theme_label_var = tk.StringVar(value="Match Windows")
        self.version_var = tk.StringVar(value="yt-dlp version: Checking...")
        self.app_ver_var = tk.StringVar(value=f"App Version: v{APP_VERSION}")
        self.protocol_status_var = tk.StringVar(value="Checking ytdlp:// protocol...")

        # Download Process, Queue & Failed Downloads State
        self.download_queue = []
        self.failed_downloads = []
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
        self._applying_preset = False
        self._resize_after_id = None
        self._dl_cfg_after_id = None
        self._set_cfg_after_id = None
        self._abt_cfg_after_id = None
        self._dl_bbox_after_id = None
        self._set_bbox_after_id = None
        self._abt_bbox_after_id = None
        self._last_dl_canvas_w = -1
        self._last_set_canvas_w = -1
        self._last_abt_canvas_w = -1

        self.help_badges = []
        self.rounded_cards = []
        self.rounded_buttons = []
        self.sp_dropdowns = []
        self.sp_checkboxes = []
        self.sp_radios = []
        self.pill_scrollbars = []
        self.themed_frames = []
        self.themed_labels = []
        self.preset_pill_btns = {}
        self.history_items = []

        # Auto-register SongPulse ytdlp:// protocol quietly on Windows startup
        register_songpulse_protocol()

        self.load_presets()
        self.load_settings()

        # Apply saved window geometry if "Remember window size" is enabled, otherwise default size
        if self.remember_win_size_var.get():
            w = max(MIN_WINDOW_WIDTH, int(self.saved_win_width or DEFAULT_WINDOW_WIDTH))
            h = max(MIN_WINDOW_HEIGHT, int(self.saved_win_height or DEFAULT_WINDOW_HEIGHT))
            self.geometry(f"{w}x{h}")
        else:
            self.geometry(f"{DEFAULT_WINDOW_WIDTH}x{DEFAULT_WINDOW_HEIGHT}")

        self.load_history()
        self.build_ui()
        self.refresh_format_options()
        self.update_dependency_feature_states()
        self.update_quality_controls()
        self.update_subtitle_controls()
        self.update_playlist_folder_controls()
        self.update_scope_visibility()
        self.sync_active_preset_from_options()
        self.refresh_queue_ui()
        self.refresh_failed_ui()
        self.refresh_history_tree()
        self.apply_theme(force=True)
        self.poll_system_theme()
        self.after(250, self.check_ytdlp_version)
        if self.startup_job:
            self.after(450, lambda: self.handle_startup_job(self.startup_job))
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ========================================================================
    # WIDGET FACTORY HELPERS (Tracks widgets for instant SongPulse theme updates)
    # ========================================================================
    def make_card(self, parent, title="", pad_x=16, pad_y=12):
        card = RoundedCard(parent, title=title, app_ref=self, pad_x=pad_x, pad_y=pad_y)
        self.rounded_cards.append(card)
        return card

    def make_btn(
        self,
        parent,
        text="",
        command=None,
        variant="secondary",
        icon_kind=None,
        tooltip=None,
        width=None,
        height=30,
        font=("Segoe UI", 9),
        padx=13,
    ):
        btn = RoundedButton(
            parent,
            text=text,
            command=command,
            app_ref=self,
            variant=variant,
            icon_kind=icon_kind,
            tooltip=tooltip,
            width=width,
            height=height,
            font=font,
            padx=padx,
        )
        self.rounded_buttons.append(btn)
        return btn

    def make_chk(self, parent, text="", variable=None, command=None):
        chk = SongPulseCheckbox(
            parent, text=text, variable=variable, command=command, app_ref=self
        )
        self.sp_checkboxes.append(chk)
        return chk

    def make_radio(self, parent, text="", value="", variable=None, command=None):
        rb = SongPulseRadio(
            parent, text=text, value=value, variable=variable, command=command, app_ref=self
        )
        self.sp_radios.append(rb)
        return rb

    def make_dropdown(
        self,
        parent,
        textvariable=None,
        values=None,
        item_descriptions=None,
        state="readonly",
        width=20,
        command=None,
    ):
        dd = SongPulseDropdown(
            parent,
            textvariable=textvariable,
            values=values,
            item_descriptions=item_descriptions,
            state=state,
            width=width,
            command=command,
            app_ref=self,
        )
        self.sp_dropdowns.append(dd)
        return dd

    def make_scrollbar(self, parent, orient="vertical", command=None, thickness=10):
        sb = ModernScrollbar(
            parent, orient=orient, command=command, app_ref=self, thickness=thickness
        )
        self.pill_scrollbars.append(sb)
        return sb

    def make_card_frame(self, parent):
        f = tk.Frame(parent)
        self.themed_frames.append(f)
        return f

    def make_card_wrap(self, parent, padx=5, pady=3):
        wf = WrapFrame(parent, padx=padx, pady=pady)
        self.themed_frames.append(wf)
        return wf

    def make_card_label(
        self, parent, text="", textvariable=None, font=("Segoe UI", 9), muted=False, **kwargs
    ):
        lbl = tk.Label(parent, text=text, textvariable=textvariable, font=font, **kwargs)
        self.themed_labels.append((lbl, muted))
        return lbl

    def make_help_badge(self, parent, title, description):
        badge = HelpBadge(parent, title, description, self)
        self.help_badges.append(badge)
        return badge

    # ========================================================================
    # TOP STICKY NAVBAR PAGE SWITCHING & COLLAPSIBLE ADVANCED MODE
    # ========================================================================
    def select_page(self, idx):
        self.active_page_idx = idx
        for i, nav_btn in enumerate(self.nav_buttons):
            nav_btn.set_active(i == idx)
        for i, page in enumerate(self.pages):
            if i == idx:
                page.pack(fill="both", expand=True)
            else:
                page.pack_forget()

    def toggle_advanced_mode(self):
        self.advanced_mode_open = not self.advanced_mode_open
        if self.advanced_mode_open:
            self.adv_toggle_btn.configure(
                text="▾  Hide Advanced Mode (Format, Quality, Clip, Naming & Subtitles)",
                selected=True,
            )
            self.advanced_container.pack(fill="x", before=self.btn_wrap)
        else:
            self.adv_toggle_btn.configure(
                text="▸  Advanced Mode (Format, Quality, Clip, Naming & Subtitles)",
                selected=False,
            )
            self.advanced_container.pack_forget()
        self._schedule_dl_scrollregion()

    # ========================================================================
    # DEPENDENCY RESOLUTION & FEATURE GATING
    # ========================================================================
    def get_dep_pref_mode(self):
        return DEP_PREF_LABEL_TO_VAL.get(self.dep_pref_label_var.get(), "global")

    def get_ytdlp_exe(self):
        return resolve_ytdlp_exe(self.get_dep_pref_mode())

    def get_ffmpeg_exe(self):
        return resolve_binary("ffmpeg.exe", FFMPEG_PATH, self.get_dep_pref_mode())

    def get_node_exe(self):
        return resolve_binary("node.exe", NODE_PATH, self.get_dep_pref_mode())

    def update_dependency_feature_states(self):
        has_ffmpeg = bool(self.get_ffmpeg_exe())
        has_node = bool(self.get_node_exe())

        if hasattr(self, "dep_warn_banner"):
            if not has_ffmpeg or not has_node:
                missing_parts = []
                if not has_ffmpeg:
                    missing_parts.append(
                        "FFmpeg not installed (Preview, audio conversion, time-clipping, custom resolution, and cover art are disabled)"
                    )
                if not has_node:
                    missing_parts.append(
                        "Node.js not installed (YouTube downloads have a higher chance of being blocked)"
                    )
                msg = "⚠ " + " | ".join(missing_parts)
                self.dep_warn_lbl.config(text=msg)
                if not self.dep_warn_banner.winfo_ismapped():
                    self.dep_warn_banner.pack(
                        fill="x", padx=20, pady=(8, 4), before=self.preset_card
                    )
            else:
                self.dep_warn_banner.pack_forget()

        if hasattr(self, "preview_btn"):
            self.preview_btn.config(state="normal" if has_ffmpeg else "disabled")
        if hasattr(self, "clip_scope_rb"):
            if not has_ffmpeg and self.range_choice.get() == "2":
                self.range_choice.set("1")
                self.update_scope_visibility()
            self.clip_scope_rb.config(state="normal" if has_ffmpeg else "disabled")
        if hasattr(self, "meta_chk"):
            self.meta_chk.config(state="normal" if has_ffmpeg else "disabled")

        if not has_ffmpeg and self.media_type.get() == "audio" and self.audio_fmt.get() != "orig":
            self.audio_fmt.set("orig")
            self.format_label_var.set(AUDIO_FMT_VAL_TO_LABEL.get("orig", "Original (No FFmpeg)"))

        self.update_quality_controls()
        self.update_subtitle_controls()

    # ========================================================================
    # PRESET MANAGEMENT
    # - Quick Presets: Video / Music (media mode) + independent Playlist toggle
    # - Custom Preset Dropdown: ONLY user-saved custom presets (no built-in presets inside)
    # ========================================================================
    def load_presets(self):
        self.custom_presets = {}
        if os.path.exists(PRESETS_FILE):
            try:
                with open(PRESETS_FILE, "r", encoding="utf-8") as f:
                    custom_data = json.load(f)
                if isinstance(custom_data, dict):
                    for name, cfg in custom_data.items():
                        if name not in DEFAULT_PRESETS and isinstance(cfg, dict):
                            self.custom_presets[name] = cfg
            except Exception:
                pass

    def save_presets_file(self):
        try:
            with open(PRESETS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.custom_presets, f, indent=2)
        except OSError:
            pass

    def apply_quick_media_preset(self, mode):
        """
        Applies the 'video' or 'music' quick preset while preserving the current
        Playlist toggle state so Playlist can stay ON with either Video or Music!
        """
        self._applying_preset = True
        try:
            if mode == "video":
                self.media_type.set("video")
                self.video_fmt.set("mp4")
                self.quality_label_var.set("Auto (Best)")
                self.use_custom_res_var.set(False)
                self.custom_res_var.set("")
                self.range_choice.set("1")
                self.meta_var.set(True)
                self.subs_var.set(False)
            elif mode == "music":
                self.media_type.set("audio")
                self.audio_fmt.set("mp3")
                self.audio_quality_label_var.set("Auto (Best Audio)")
                self.range_choice.set("1")
                self.meta_var.set(True)

            self.refresh_format_options()
            self.update_dependency_feature_states()
            self.update_quality_controls()
            self.update_subtitle_controls()
            self.update_scope_visibility()
        finally:
            self._applying_preset = False

        self.save_settings()

    def toggle_quick_playlist_preset(self):
        """
        Toggles the Playlist quick preset ON or OFF independently of whether
        Video or Music is selected, enabling ordered playlist subfolder downloads
        for either Video or Music!
        """
        self._applying_preset = True
        try:
            currently_on = self._is_playlist_preset_active()
            new_state = not currently_on
            self.playlist_folder_var.set(new_state)
            self.batch_as_playlist_var.set(new_state)
            self.playlist_numbering_var.set(new_state)
            if new_state:
                self.range_choice.set("1")
            self.update_playlist_folder_controls()
            self.update_scope_visibility()
        finally:
            self._applying_preset = False

        self.save_settings()

    def apply_preset(self, preset_name):
        """
        Applies a preset by name (supports both built-in names from SongPulse/CLI
        and user-saved custom presets from the Custom Preset dropdown).
        """
        if preset_name == "Preset 1: Video":
            self.apply_quick_media_preset("video")
            return
        if preset_name == "Preset 2: Music":
            self.apply_quick_media_preset("music")
            return
        if preset_name == "Preset 3: Playlist":
            # SongPulse / Preset 3: Music + Playlist ON
            self.apply_quick_media_preset("music")
            if not self._is_playlist_preset_active():
                self.toggle_quick_playlist_preset()
            return

        if preset_name not in self.custom_presets:
            return

        self._applying_preset = True
        try:
            cfg = self.custom_presets[preset_name]
            self.custom_preset_var.set(preset_name)

            self.media_type.set(cfg.get("media_type", "video"))
            self.video_fmt.set(cfg.get("video_fmt", "mp4"))
            self.audio_fmt.set(cfg.get("audio_fmt", "mp3"))
            self.quality_label_var.set(
                QUALITY_VAL_TO_LABEL.get(cfg.get("quality_choice", "best"), "Auto (Best)")
            )
            self.audio_quality_label_var.set(
                AUDIO_QUALITY_VAL_TO_LABEL.get(
                    cfg.get("audio_quality_choice", "best"), "Auto (Best Audio)"
                )
            )
            self.use_custom_res_var.set(bool(cfg.get("use_custom_res", False)))
            self.custom_res_var.set(cfg.get("custom_res", ""))
            self.range_choice.set(str(cfg.get("range_choice", "1")))
            self.playlist_folder_var.set(bool(cfg.get("playlist_folder", False)))
            self.playlist_numbering_var.set(bool(cfg.get("playlist_numbering", False)))
            self.batch_as_playlist_var.set(bool(cfg.get("batch_as_playlist", False)))
            self.meta_var.set(bool(cfg.get("meta", True)))
            self.subs_var.set(bool(cfg.get("subs", False)))

            self.refresh_format_options()
            self.update_dependency_feature_states()
            self.update_quality_controls()
            self.update_subtitle_controls()
            self.update_playlist_folder_controls()
            self.update_scope_visibility()
        finally:
            self._applying_preset = False

        self.save_settings()

    def _is_video_preset_active(self):
        """Returns True if media/format/quality/clip/metadata match the Video quick preset."""
        return (
            self.media_type.get() == "video"
            and self.video_fmt.get() == "mp4"
            and QUALITY_LABEL_TO_VAL.get(self.quality_label_var.get(), "best") == "best"
            and not self.use_custom_res_var.get()
            and self.range_choice.get() == "1"
            and bool(self.meta_var.get()) is True
            and bool(self.subs_var.get()) is False
        )

    def _is_music_preset_active(self):
        """Returns True if media/format/quality/clip/metadata match the Music quick preset."""
        return (
            self.media_type.get() == "audio"
            and self.audio_fmt.get() == "mp3"
            and AUDIO_QUALITY_LABEL_TO_VAL.get(self.audio_quality_label_var.get(), "best") == "best"
            and self.range_choice.get() == "1"
            and bool(self.meta_var.get()) is True
        )

    def _is_playlist_preset_active(self):
        """Returns True if Playlist folder + track numbering + batch playlist folder are active."""
        return (
            bool(self.playlist_folder_var.get())
            and bool(self.playlist_numbering_var.get())
            and bool(self.batch_as_playlist_var.get())
        )

    def _does_current_state_match_custom_preset(self, cfg):
        cur_type = self.media_type.get()
        if cur_type != cfg.get("media_type", "video"):
            return False
        if cur_type == "video":
            if self.video_fmt.get() != cfg.get("video_fmt", "mp4"):
                return False
            cur_q = QUALITY_LABEL_TO_VAL.get(self.quality_label_var.get(), "best")
            if cur_q != cfg.get("quality_choice", "best"):
                return False
            if bool(self.use_custom_res_var.get()) != bool(cfg.get("use_custom_res", False)):
                return False
            if self.use_custom_res_var.get():
                if self.custom_res_var.get().strip() != (cfg.get("custom_res", "") or "").strip():
                    return False
            if bool(self.subs_var.get()) != bool(cfg.get("subs", False)):
                return False
        else:
            if self.audio_fmt.get() != cfg.get("audio_fmt", "mp3"):
                return False
            cur_aq = AUDIO_QUALITY_LABEL_TO_VAL.get(
                self.audio_quality_label_var.get(), "best"
            )
            if cur_aq != cfg.get("audio_quality_choice", "best"):
                return False

        if str(self.range_choice.get()) != str(cfg.get("range_choice", "1")):
            return False
        if bool(self.playlist_folder_var.get()) != bool(cfg.get("playlist_folder", False)):
            return False
        if bool(self.playlist_numbering_var.get()) != bool(cfg.get("playlist_numbering", False)):
            return False
        if bool(self.batch_as_playlist_var.get()) != bool(cfg.get("batch_as_playlist", False)):
            return False
        if bool(self.meta_var.get()) != bool(cfg.get("meta", True)):
            return False
        return True

    def sync_active_preset_from_options(self):
        """
        Updates the 3 Quick Preset pill buttons (Video, Music, and independent Playlist)
        and the Custom Preset dropdown whenever any setting changes.
        """
        if getattr(self, "_applying_preset", False):
            return

        vid_on = self._is_video_preset_active()
        mus_on = self._is_music_preset_active()
        pl_on = self._is_playlist_preset_active()

        if "video" in self.preset_pill_btns:
            self.preset_pill_btns["video"].configure(selected=vid_on)
        if "music" in self.preset_pill_btns:
            self.preset_pill_btns["music"].configure(selected=mus_on)
        if "playlist" in self.preset_pill_btns:
            self.preset_pill_btns["playlist"].configure(selected=pl_on)

        # Match against user-saved custom presets
        matched_custom = None
        cur_c = self.custom_preset_var.get()
        check_order = []
        if cur_c in self.custom_presets:
            check_order.append(cur_c)
        for k in self.custom_presets:
            if k not in check_order:
                check_order.append(k)

        for name in check_order:
            if self._does_current_state_match_custom_preset(self.custom_presets[name]):
                matched_custom = name
                break

        if matched_custom:
            self.custom_preset_var.set(matched_custom)
        else:
            self.custom_preset_var.set("None")

        self.refresh_preset_ui()

    def save_current_as_preset(self):
        name = simpledialog.askstring(
            "Save as Preset",
            "Enter a name for your custom preset:",
            parent=self,
        )
        if not name:
            return
        name = name.strip()
        if not name or name.lower() == "none":
            return

        is_vid = self.media_type.get() == "video"
        fmt_str = self.video_fmt.get().upper() if is_vid else self.audio_fmt.get().upper()
        q_str = (
            self.quality_label_var.get()
            if is_vid
            else self.audio_quality_label_var.get()
        )
        desc = f"Custom Preset '{name}': {fmt_str}, {q_str}, {'Playlist Folder ON' if self.playlist_folder_var.get() else 'Single File'}"

        self.custom_presets[name] = {
            "description": desc,
            "media_type": self.media_type.get(),
            "video_fmt": self.video_fmt.get(),
            "audio_fmt": self.audio_fmt.get(),
            "quality_choice": QUALITY_LABEL_TO_VAL.get(self.quality_label_var.get(), "best"),
            "audio_quality_choice": AUDIO_QUALITY_LABEL_TO_VAL.get(
                self.audio_quality_label_var.get(), "best"
            ),
            "use_custom_res": self.use_custom_res_var.get(),
            "custom_res": self.custom_res_var.get(),
            "range_choice": self.range_choice.get(),
            "playlist_folder": self.playlist_folder_var.get(),
            "playlist_numbering": self.playlist_numbering_var.get(),
            "batch_as_playlist": self.batch_as_playlist_var.get(),
            "meta": self.meta_var.get(),
            "subs": self.subs_var.get(),
        }
        self.save_presets_file()
        self.custom_preset_var.set(name)
        self.refresh_preset_ui()
        self.save_settings()

    def delete_selected_preset(self):
        cur = self.custom_preset_var.get()
        if cur not in self.custom_presets:
            messagebox.showinfo(
                "No Custom Preset Selected",
                "Select a saved custom preset from the 'Custom Preset' dropdown first.",
            )
            return
        if messagebox.askyesno("Delete Custom Preset", f"Delete custom preset '{cur}'?"):
            del self.custom_presets[cur]
            self.save_presets_file()
            self.custom_preset_var.set("None")
            self.refresh_preset_ui()
            self.save_settings()

    def refresh_preset_ui(self):
        if not hasattr(self, "preset_combo"):
            return
        custom_names = list(self.custom_presets.keys())
        dropdown_vals = custom_names if custom_names else ["None"]
        self.preset_combo.configure(values=dropdown_vals)

        cur_c = self.custom_preset_var.get()
        has_valid_custom = cur_c in self.custom_presets
        self.del_preset_btn.configure(state="normal" if has_valid_custom else "disabled")

        # Build human-readable summary description of active preset state
        vid_on = self._is_video_preset_active()
        mus_on = self._is_music_preset_active()
        pl_on = self._is_playlist_preset_active()

        if has_valid_custom:
            self.preset_desc_var.set(self.custom_presets[cur_c].get("description", ""))
        elif vid_on and pl_on:
            self.preset_desc_var.set(
                "Video + Playlist: Downloads MP4 video with best resolution available, adds playlist/queued links to a new folder"
            )
        elif mus_on and pl_on:
            self.preset_desc_var.set(
                "Music + Playlist: Downloads MP3 music with best quality, adds playlist/queued links to a new folder"
            )
        elif vid_on:
            self.preset_desc_var.set(DEFAULT_PRESETS["Preset 1: Video"]["description"])
        elif mus_on:
            self.preset_desc_var.set(DEFAULT_PRESETS["Preset 2: Music"]["description"])
        elif pl_on:
            self.preset_desc_var.set(DEFAULT_PRESETS["Preset 3: Playlist"]["description"])
        else:
            self.preset_desc_var.set(
                "Custom modified settings — click 'Save as Preset' to save this configuration."
            )

    def quick_download(self):
        """
        Quick Download button handler: downloads immediately with the selected preset/options
        using the link pasted in the URL box (or queued links), falling back to the clipboard link.
        """
        if self.is_downloading:
            messagebox.showinfo(
                "Download in Progress",
                "A download is already running. Please wait or click Stop / Cancel below.",
            )
            return

        url_box_txt = self.url_var.get().strip()
        if not url_box_txt and not self.download_queue:
            try:
                clip = self.clipboard_get().strip()
            except tk.TclError:
                clip = ""
            clip_links = [
                ln.strip().replace('"', "")
                for ln in clip.splitlines()
                if ln.strip().startswith(("http://", "https://"))
            ]
            if not clip_links and clip and "." in clip and " " not in clip:
                clip_links = [clip.strip().replace('"', "")]

            if not clip_links:
                messagebox.showwarning(
                    "No Link Found",
                    "Paste a link in the Media Link box or copy an http/https link to your clipboard first.",
                )
                return

            if len(clip_links) == 1:
                self.url_var.set(clip_links[0])
            else:
                for ln in clip_links:
                    if ln not in self.download_queue:
                        self.download_queue.append(ln)
                self.refresh_queue_ui()

        self.start_download()

    # ========================================================================
    # SONGPULSE AUTOMATIC BATCH TRIGGER
    # ========================================================================
    def handle_startup_job(self, job):
        if not job:
            return
        preset_name = job.get("preset") or "Preset 3: Playlist"
        self.apply_preset(preset_name)

        pl_name = (job.get("playlist_name") or "").strip()
        if pl_name:
            self.playlist_folder_var.set(True)
            self.batch_as_playlist_var.set(True)
            self.playlist_numbering_var.set(True)
            self.custom_playlist_folder_var.set(pl_name)
            self.update_playlist_folder_controls()

        urls = job.get("urls") or []
        if len(urls) == 1 and not pl_name:
            self.url_var.set(urls[0])
        elif urls:
            for u in urls:
                if u not in self.download_queue:
                    self.download_queue.append(u)
            self.refresh_queue_ui()

        self.select_page(0)
        if job.get("auto_start", True) and (urls or self.url_var.get().strip()):
            self.start_download()

    # ========================================================================
    # MAIN UI LAYOUT (Sticky SongPulse Top Navbar + 4 Scrollable Pages)
    # ========================================================================
    def build_ui(self):
        # --------------------------------------------------------------------
        # STICKY TOP NAVBAR (Stays pinned at top while content scrolls below)
        # --------------------------------------------------------------------
        self.navbar = tk.Frame(self, padx=18, pady=7)
        self.navbar.pack(side="top", fill="x")

        self.navbar_divider = tk.Frame(self, height=1)
        self.navbar_divider.pack(side="top", fill="x")

        self.nav_buttons = []
        nav_items = [
            ("downloader", "Downloader", 0),
            ("history", "History", 1),
            ("settings", "Settings", 2),
            ("about", "About / Info", 3),
        ]
        for icon_kind, label, idx in nav_items:
            nbtn = TopNavButton(
                self.navbar,
                icon_kind=icon_kind,
                label=label,
                command=lambda i=idx: self.select_page(i),
                app_ref=self,
            )
            nbtn.pack(side="left", padx=(0, 6))
            self.nav_buttons.append(nbtn)

        # --------------------------------------------------------------------
        # MAIN PAGE AREA (4 Pages: Downloader, History, Settings, About/Info)
        # --------------------------------------------------------------------
        self.main_area = tk.Frame(self)
        self.main_area.pack(side="top", fill="both", expand=True)

        self.dl_page = tk.Frame(self.main_area)
        self.history_page = tk.Frame(self.main_area)
        self.settings_page = tk.Frame(self.main_area)
        self.about_page = tk.Frame(self.main_area)
        self.pages = [self.dl_page, self.history_page, self.settings_page, self.about_page]

        self.build_downloader_tab()
        self.build_history_tab()
        self.build_settings_tab()
        self.build_about_tab()

        self.select_page(0)
        self.bind_all("<Button-1>", self._on_global_click, add="+")
        self.bind_all("<MouseWheel>", self._on_global_mousewheel)
        self.bind("<Configure>", self._on_root_window_configure)

    def _on_global_click(self, event):
        w = getattr(event, "widget", None)
        if not isinstance(w, tk.Widget):
            return
        if isinstance(w, (tk.Entry, ttk.Entry, tk.Text, ttk.Spinbox, tk.Spinbox)):
            return
        try:
            focused = self.focus_get()
        except Exception:
            focused = None
        if isinstance(focused, (tk.Entry, ttk.Entry, tk.Text, ttk.Spinbox, tk.Spinbox)):
            self.focus_set()

    def _on_global_mousewheel(self, event):
        w = event.widget
        if isinstance(w, (tk.Text, tk.Listbox, ttk.Spinbox, ttk.Combobox, ttk.Treeview)):
            return
        if self.active_page_idx == 0:
            self.dl_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        elif self.active_page_idx == 2 and hasattr(self, "settings_canvas"):
            self.settings_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        elif self.active_page_idx == 3 and hasattr(self, "about_canvas"):
            self.about_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_root_window_configure(self, event):
        if event.widget is not self:
            return
        if self._resize_after_id:
            self.after_cancel(self._resize_after_id)
        self._resize_after_id = self.after(90, self._on_resize_settled)

    def _on_resize_settled(self):
        self._resize_after_id = None
        w = self.winfo_width()
        h = self.winfo_height()
        if w >= MIN_WINDOW_WIDTH and h >= MIN_WINDOW_HEIGHT:
            self.saved_win_width = w
            self.saved_win_height = h
        target = int(h * 0.20)
        clamped = max(LOG_MIN_HEIGHT, min(LOG_MAX_HEIGHT, target))
        cur_h = self.log_box_container.cget("height")
        if abs(cur_h - clamped) >= 8:
            self.log_box_container.configure(height=clamped)

    def _schedule_dl_scrollregion(self, event=None):
        if self._dl_bbox_after_id:
            self.after_cancel(self._dl_bbox_after_id)
        self._dl_bbox_after_id = self.after(
            20,
            lambda: self.dl_canvas.configure(scrollregion=self.dl_canvas.bbox("all"))
            if self.dl_canvas.winfo_exists()
            else None,
        )

    # ========================================================================
    # PAGE 1: DOWNLOADER
    # ========================================================================
    def build_downloader_tab(self):
        self.dl_canvas = tk.Canvas(self.dl_page, highlightthickness=0, bd=0)
        self.dl_vscroll = self.make_scrollbar(
            self.dl_page, orient="vertical", command=self.dl_canvas.yview
        )
        self.dl_canvas.configure(yscrollcommand=self.dl_vscroll.set)

        self.dl_vscroll.pack(side="right", fill="y", padx=(0, 2), pady=4)
        self.dl_canvas.pack(side="left", fill="both", expand=True)

        self.dl_tab = tk.Frame(self.dl_canvas)
        self.dl_canvas_window = self.dl_canvas.create_window(
            (0, 0), window=self.dl_tab, anchor="nw"
        )

        self.dl_tab.bind("<Configure>", self._schedule_dl_scrollregion)

        def _apply_dl_w(width):
            self._dl_cfg_after_id = None
            if self.dl_canvas.winfo_exists():
                self.dl_canvas.itemconfig(self.dl_canvas_window, width=width)

        def _on_dl_canvas_cfg(e):
            if abs(e.width - self._last_dl_canvas_w) >= 3:
                if self._last_dl_canvas_w == -1:
                    self._last_dl_canvas_w = e.width
                    self.dl_canvas.itemconfig(self.dl_canvas_window, width=e.width)
                else:
                    self._last_dl_canvas_w = e.width
                    if self._dl_cfg_after_id:
                        self.after_cancel(self._dl_cfg_after_id)
                    self._dl_cfg_after_id = self.after(16, lambda w=e.width: _apply_dl_w(w))

        self.dl_canvas.bind("<Configure>", _on_dl_canvas_cfg)

        card_pad = {"padx": 20, "pady": 5}

        # Dependency Warning Banner (Auto-shown only when FFmpeg or Node.js is missing)
        self.dep_warn_banner = tk.Frame(
            self.dl_tab,
            bg="#2e1c08",
            highlightbackground="#d97706",
            highlightthickness=1,
            padx=12,
            pady=8,
        )
        self.dep_warn_lbl = tk.Label(
            self.dep_warn_banner,
            text="",
            bg="#2e1c08",
            fg="#fde68a",
            font=("Segoe UI", 8, "bold"),
            justify="left",
            anchor="w",
            wraplength=540,
        )
        self.dep_warn_lbl.pack(side="left", fill="x", expand=True)
        self.make_btn(
            self.dep_warn_banner,
            text="Install in Settings →",
            variant="warning",
            height=26,
            command=lambda: self.select_page(2),
        ).pack(side="right", padx=(8, 0))

        # --------------------------------------------------------------------
        # CARD 1: QUICK PRESETS
        # - Video / Music + Independent Playlist Toggle
        # - Playlist Folder Name Textbox
        # - Custom Preset Dropdown (Only custom presets) + Save as Preset + Delete
        # --------------------------------------------------------------------
        self.preset_card = self.make_card(self.dl_tab, title="Quick Presets")
        self.preset_card.pack(fill="x", padx=20, pady=(12, 5))

        # Row 1: Video, Music, Playlist (independent toggle), (?)
        p_row1 = self.make_card_wrap(self.preset_card.body, padx=4, pady=2)
        p_row1.pack(fill="x", pady=(0, 4))

        self.preset_pill_btns["video"] = self.make_btn(
            p_row1,
            text="Video",
            icon_kind="video",
            variant="pill",
            height=31,
            font=("Segoe UI", 9, "bold"),
            command=lambda: self.apply_quick_media_preset("video"),
        )
        self.preset_pill_btns["music"] = self.make_btn(
            p_row1,
            text="Music",
            icon_kind="music",
            variant="pill",
            height=31,
            font=("Segoe UI", 9, "bold"),
            command=lambda: self.apply_quick_media_preset("music"),
        )
        self.preset_pill_btns["playlist"] = self.make_btn(
            p_row1,
            text="Playlist",
            icon_kind="playlist",
            variant="pill",
            height=31,
            font=("Segoe UI", 9, "bold"),
            tooltip="Toggle ON alongside Video or Music to download into a new ordered playlist folder.",
            command=self.toggle_quick_playlist_preset,
        )

        self.make_help_badge(p_row1, "Download Presets", EXTRA_HELP["presets"])

        # Row 2: Playlist Folder Name Textbox (Right under the quick presets!)
        p_folder_row = self.make_card_frame(self.preset_card.body)
        p_folder_row.pack(fill="x", pady=(2, 6))
        self.make_card_label(
            p_folder_row, text="Playlist Folder Name:", font=("Segoe UI", 9, "bold")
        ).pack(side="left")
        self.make_help_badge(
            p_folder_row, "Playlist & Batch Folder", EXTRA_HELP["playlist_folder"]
        ).pack(side="right")
        self.quick_pl_folder_entry = ttk.Entry(
            p_folder_row, textvariable=self.custom_playlist_folder_var
        )
        self.quick_pl_folder_entry.pack(
            side="left", fill="x", expand=True, padx=8, ipady=2
        )

        # Row 3: Custom Preset Dropdown (Only user-saved custom presets) + Save as Preset + Delete
        p_row2 = self.make_card_wrap(self.preset_card.body, padx=4, pady=2)
        p_row2.pack(fill="x", pady=(0, 4))

        self.make_card_label(
            p_row2, text="Custom Preset:", font=("Segoe UI", 9, "bold")
        )
        self.preset_combo = self.make_dropdown(
            p_row2,
            textvariable=self.custom_preset_var,
            values=["None"],
            state="readonly",
            width=18,
        )
        self.preset_combo.bind(
            "<<ComboboxSelected>>",
            lambda e: self.apply_preset(self.custom_preset_var.get()),
        )

        self.make_btn(
            p_row2, text="Save as Preset", height=30, command=self.save_current_as_preset
        )
        self.del_preset_btn = self.make_btn(
            p_row2, text="Delete", height=30, command=self.delete_selected_preset
        )

        # Row 4: Preset Description Summary
        p_sub = self.make_card_frame(self.preset_card.body)
        p_sub.pack(fill="x", pady=(2, 0))
        self.preset_desc_lbl = self.make_card_label(
            p_sub,
            textvariable=self.preset_desc_var,
            font=("Segoe UI", 8),
            muted=True,
            justify="left",
            anchor="w",
            wraplength=520,
        )
        self.preset_desc_lbl.pack(side="left", fill="x", expand=True)

        # --------------------------------------------------------------------
        # CARD 2: MEDIA LINK, QUEUE, FAILED DOWNLOADS & PREVIEW
        # --------------------------------------------------------------------
        self.url_card = self.make_card(
            self.dl_tab, title="Media Link, Batch Queue & Live Preview"
        )
        self.url_card.pack(fill="x", **card_pad)
        self.url_frame = self.url_card.body

        url_top_row = self.make_card_frame(self.url_frame)
        url_top_row.pack(fill="x", pady=(0, 2))

        self.preview_btn = self.make_btn(
            url_top_row, text="▶ Preview", variant="primary", command=self.start_preview
        )
        self.preview_btn.pack(side="right", padx=(4, 0))
        self.make_btn(url_top_row, text="Clear", command=self.clear_url).pack(
            side="right", padx=2
        )
        self.make_btn(url_top_row, text="+ Queue", command=self.add_to_queue).pack(
            side="right", padx=2
        )
        self.make_btn(url_top_row, text="Paste", command=self.paste_url).pack(
            side="right", padx=2
        )

        self.url_entry = ttk.Entry(url_top_row, textvariable=self.url_var, font=("Segoe UI", 10))
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=3)
        self.url_placeholder = tk.Label(
            self.url_entry,
            text="Paste link here",
            font=("Segoe UI", 10),
            bd=0,
            padx=0,
            pady=0,
            cursor="xterm",
        )
        self.url_placeholder.bind("<Button-1>", lambda e: self.url_entry.focus_set())
        self.url_entry.bind("<FocusIn>", self._update_url_placeholder, add="+")
        self.url_entry.bind("<FocusOut>", self._update_url_placeholder, add="+")
        self.url_var.trace_add("write", lambda *args: self._update_url_placeholder())
        self._update_url_placeholder()

        # Collapsible Batch Queue Box
        self.queue_frame = self.make_card_frame(self.url_frame)
        q_head = self.make_card_wrap(self.queue_frame, padx=3, pady=2)
        q_head.pack(fill="x", pady=(6, 4))
        self.queue_lbl = self.make_card_label(
            q_head, text="Batch Queue (0):", font=("Segoe UI", 9, "bold")
        )
        self.make_chk(
            q_head,
            text="Save batch to new playlist folder",
            variable=self.batch_as_playlist_var,
            command=self.on_batch_playlist_toggle,
        )
        self.make_btn(
            q_head, text="Paste Multi-Links", height=26, command=self.paste_multiple_to_queue
        )
        self.make_btn(
            q_head, text="Remove", height=26, command=self.remove_selected_queue
        )
        self.make_btn(q_head, text="Clear Queue", height=26, command=self.clear_queue)

        q_list_wrap = self.make_card_frame(self.queue_frame)
        q_list_wrap.pack(fill="x", pady=(0, 6))
        q_scroll = self.make_scrollbar(q_list_wrap, orient="vertical", thickness=8)
        q_scroll.pack(side="right", fill="y", padx=(2, 0))
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

        # Collapsible Failed Downloads Box
        self.failed_frame = self.make_card_frame(self.url_frame)
        f_head = self.make_card_wrap(self.failed_frame, padx=3, pady=2)
        f_head.pack(fill="x", pady=(6, 4))
        self.failed_lbl = self.make_card_label(
            f_head, text="⚠ Failed Songs / Downloads (0):", font=("Segoe UI", 9, "bold")
        )
        self.retry_all_btn = self.make_btn(
            f_head,
            text="↻ Retry All Failed",
            variant="warning",
            height=26,
            font=("Segoe UI", 8, "bold"),
            command=self.retry_all_failed_downloads,
        )
        self.make_btn(
            f_head, text="Retry Selected", height=26, command=self.retry_selected_failed_downloads
        )
        self.make_btn(
            f_head, text="Dismiss", height=26, command=self.clear_failed_downloads
        )

        f_list_wrap = self.make_card_frame(self.failed_frame)
        f_list_wrap.pack(fill="x", pady=(0, 6))
        f_scroll = self.make_scrollbar(f_list_wrap, orient="vertical", thickness=8)
        f_scroll.pack(side="right", fill="y", padx=(2, 0))
        self.failed_listbox = tk.Listbox(
            f_list_wrap,
            height=3,
            font=("Consolas", 9),
            yscrollcommand=f_scroll.set,
            selectmode="extended",
            relief="flat",
            highlightthickness=1,
        )
        self.failed_listbox.pack(side="left", fill="x", expand=True)
        f_scroll.config(command=self.failed_listbox.yview)

        # Collapsible Live Preview Box
        self.preview_box = self.make_card_frame(self.url_frame)

        self.preview_header = self.make_card_frame(self.preview_box)
        self.preview_header.pack(fill="x", pady=(4, 4))
        self.preview_title_lbl = self.make_card_label(
            self.preview_header, text="", font=("Segoe UI", 9, "bold"), wraplength=460
        )
        self.preview_title_lbl.pack(side="left", fill="x", expand=True)
        self.make_btn(
            self.preview_header, text="✕ Close Preview", height=26, command=self.close_preview
        ).pack(side="right")

        self.preview_loading_frame = self.make_card_frame(self.preview_box)
        self.preview_loading_lbl = self.make_card_label(
            self.preview_loading_frame, text="Loading preview...", font=("Segoe UI", 9)
        )
        self.preview_loading_lbl.pack(pady=(4, 4))
        self.preview_progress = ttk.Progressbar(
            self.preview_loading_frame, mode="indeterminate", length=280
        )
        self.preview_progress.pack(pady=(0, 8))

        self.preview_msg_lbl = self.make_card_label(
            self.preview_box,
            text="",
            font=("Segoe UI", 9),
            justify="center",
            anchor="center",
            wraplength=500,
        )

        self.preview_player_frame = self.make_card_frame(self.preview_box)
        self.video_canvas_lbl = tk.Label(
            self.preview_player_frame, bg="#000000", width=PREVIEW_W, height=PREVIEW_H
        )
        self.video_canvas_lbl.pack(pady=(2, 6))

        ctrl_row1 = self.make_card_frame(self.preview_player_frame)
        ctrl_row1.pack(fill="x", pady=(0, 4))
        self.play_pause_btn = self.make_btn(
            ctrl_row1, text="Pause", width=8, height=28, command=self.toggle_preview_play
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
        self.preview_time_lbl = self.make_card_label(
            ctrl_row1, text="00:00 / 00:00", font=("Consolas", 9), muted=True
        )
        self.preview_time_lbl.pack(side="left", padx=(8, 0))

        ctrl_row2 = self.make_card_wrap(self.preview_player_frame, padx=3, pady=2)
        ctrl_row2.pack(fill="x", pady=(0, 4))
        self.mute_btn = self.make_btn(
            ctrl_row2, text="Vol:", width=6, height=26, command=self.toggle_mute
        )
        self.vol_slider = ModernSlider(
            ctrl_row2,
            from_=0.0,
            to=100.0,
            value=70.0,
            height=20,
            width=110,
            on_move=self.on_volume_change,
            on_end=self.on_volume_change,
        )
        self.vol_pct_lbl = self.make_card_label(
            ctrl_row2, text="70%", font=("Consolas", 9), width=4, muted=True
        )
        self.make_btn(
            ctrl_row2,
            text="Set Clip Start",
            height=26,
            command=lambda: self.set_clip_marker(True),
        )
        self.make_btn(
            ctrl_row2,
            text="Set Clip End",
            height=26,
            command=lambda: self.set_clip_marker(False),
        )
        self.preview_mode_badge = self.make_card_label(
            ctrl_row2, text="", font=("Segoe UI", 8), muted=True
        )

        # --------------------------------------------------------------------
        # CARD 3: SAVE FOLDER DIRECTORY (Moved above Format, Video Res & Sound Quality!)
        # --------------------------------------------------------------------
        save_dir_card = self.make_card(self.dl_tab, title="Save Folder Directory")
        save_dir_card.pack(fill="x", **card_pad)

        dir_row = self.make_card_frame(save_dir_card.body)
        dir_row.pack(fill="x")
        self.make_card_label(
            dir_row, text="Save Folder:", font=("Segoe UI", 9, "bold")
        ).pack(side="left")
        self.make_btn(dir_row, text="Open Folder", command=self.open_save_dir).pack(
            side="right"
        )
        self.make_btn(dir_row, text="Change...", command=self.browse_dir).pack(
            side="right", padx=(0, 6)
        )
        ttk.Entry(dir_row, textvariable=self.save_dir_var, state="readonly").pack(
            side="left", fill="x", expand=True, padx=8, ipady=2
        )

        # --------------------------------------------------------------------
        # ADVANCED MODE TOGGLE BAR (Collapses everything under it until Download / Progress Log)
        # --------------------------------------------------------------------
        self.adv_bar_wrap = tk.Frame(self.dl_tab)
        self.adv_bar_wrap.pack(fill="x", padx=20, pady=(4, 4))

        self.adv_toggle_btn = self.make_btn(
            self.adv_bar_wrap,
            text="▸  Advanced Mode (Format, Quality, Clip, Naming & Subtitles)",
            variant="pill",
            height=33,
            font=("Segoe UI", 9, "bold"),
            command=self.toggle_advanced_mode,
        )
        self.adv_toggle_btn.pack(fill="x", expand=True)

        # Collapsible Container holding all Advanced Cards
        self.advanced_container = tk.Frame(self.dl_tab)

        # --------------------------------------------------------------------
        # ADVANCED CARD A: FORMAT (Dropdown with Hover Info), VIDEO RES & SOUND QUALITY
        # --------------------------------------------------------------------
        fmt_qual_card = self.make_card(
            self.advanced_container, title="Format, Video Resolution & Sound Quality"
        )
        fmt_qual_card.pack(fill="x", **card_pad)

        type_row = self.make_card_frame(fmt_qual_card.body)
        type_row.pack(fill="x", pady=(0, 6))
        self.make_card_label(
            type_row, text="Media Type:", font=("Segoe UI", 9, "bold")
        ).pack(side="left", padx=(0, 10))
        self.make_radio(
            type_row,
            text="Video",
            value="video",
            variable=self.media_type,
            command=self.on_media_type_change,
        ).pack(side="left", padx=(0, 14))
        self.make_radio(
            type_row,
            text="Audio Only",
            value="audio",
            variable=self.media_type,
            command=self.on_media_type_change,
        ).pack(side="left")

        # Format Dropdown Row (Hovering over format items explains what each format is!)
        fmt_row = self.make_card_wrap(fmt_qual_card.body, padx=4, pady=2)
        fmt_row.pack(fill="x", pady=(0, 6))
        self.make_card_label(
            fmt_row, text="File Format:", font=("Segoe UI", 9, "bold")
        )
        self.format_combo = self.make_dropdown(
            fmt_row,
            textvariable=self.format_label_var,
            values=[lbl for _, lbl, _ in VIDEO_FORMATS],
            item_descriptions=VIDEO_FMT_DESC_MAP,
            state="readonly",
            width=22,
        )
        self.format_combo.bind("<<ComboboxSelected>>", self.on_format_dropdown_change)
        self.format_help_badge = self.make_help_badge(
            fmt_row,
            "File Format",
            VIDEO_FORMATS[0][2],
        )

        # Video Resolution Row
        v_qual_row = self.make_card_wrap(fmt_qual_card.body, padx=4, pady=2)
        v_qual_row.pack(fill="x", pady=(0, 4))

        self.make_card_label(
            v_qual_row, text="Video Quality:", font=("Segoe UI", 9, "bold")
        )
        self.quality_combo = self.make_dropdown(
            v_qual_row,
            textvariable=self.quality_label_var,
            values=[lbl for lbl, _ in QUALITY_PRESETS],
            state="readonly",
            width=15,
        )
        self.quality_combo.bind("<<ComboboxSelected>>", lambda e: self.save_settings())

        self.custom_res_chk = self.make_chk(
            v_qual_row,
            text="Custom Resolution:",
            variable=self.use_custom_res_var,
            command=self.update_quality_controls,
        )
        self.custom_res_entry = ttk.Entry(
            v_qual_row, textvariable=self.custom_res_var, width=10
        )
        self.custom_res_entry.bind("<KeyRelease>", lambda e: self.sync_active_preset_from_options())
        self.custom_res_entry.bind("<FocusOut>", lambda e: self.save_settings())
        self.make_help_badge(v_qual_row, "Video Quality", EXTRA_HELP["quality"])

        # Sound Quality Row (Directly under Video Quality)
        a_qual_row = self.make_card_wrap(fmt_qual_card.body, padx=4, pady=2)
        a_qual_row.pack(fill="x")

        self.make_card_label(
            a_qual_row, text="Sound Quality:", font=("Segoe UI", 9, "bold")
        )
        self.audio_quality_combo = self.make_dropdown(
            a_qual_row,
            textvariable=self.audio_quality_label_var,
            values=[lbl for lbl, _ in AUDIO_QUALITY_PRESETS],
            state="readonly",
            width=19,
        )
        self.audio_quality_combo.bind("<<ComboboxSelected>>", lambda e: self.save_settings())
        self.make_help_badge(
            a_qual_row, "Sound Quality", EXTRA_HELP["audio_quality"]
        )

        # --------------------------------------------------------------------
        # ADVANCED CARD B: SCOPE, NAMING & PLAYLIST / BATCH ORGANIZATION
        # --------------------------------------------------------------------
        org_card = self.make_card(
            self.advanced_container, title="Scope, Naming & Playlist / Batch Organization"
        )
        org_card.pack(fill="x", **card_pad)

        scope_row = self.make_card_wrap(org_card.body, padx=5, pady=2)
        scope_row.pack(fill="x", pady=(0, 4))
        self.make_card_label(
            scope_row, text="Scope:", font=("Segoe UI", 9, "bold")
        )
        self.make_radio(
            scope_row,
            text="Full Video / Song / Playlist",
            value="1",
            variable=self.range_choice,
            command=self.on_scope_change,
        )
        self.clip_scope_rb = self.make_radio(
            scope_row,
            text="Cut Time Clip (Start–End)",
            value="2",
            variable=self.range_choice,
            command=self.on_scope_change,
        )
        self.make_radio(
            scope_row,
            text="Playlist Item Range",
            value="3",
            variable=self.range_choice,
            command=self.on_scope_change,
        )

        self.dur_panel = self.make_card_wrap(org_card.body, padx=3, pady=2)
        self.make_card_label(self.dur_panel, text="From (H:M:S):")
        self._make_spinbox(self.dur_panel, self.sh_var, 23)
        self._make_spinbox(self.dur_panel, self.sm_var, 59)
        self._make_spinbox(self.dur_panel, self.ss_var, 59)
        self.make_card_label(self.dur_panel, text="   To (H:M:S):")
        self._make_spinbox(self.dur_panel, self.eh_var, 23)
        self._make_spinbox(self.dur_panel, self.em_var, 59)
        self._make_spinbox(self.dur_panel, self.es_var, 59)

        self.play_panel = self.make_card_wrap(org_card.body, padx=4, pady=2)
        self.make_chk(
            self.play_panel,
            text="Start at item #:",
            variable=self.use_p_start,
            command=self.save_settings,
        )
        self._make_spinbox(self.play_panel, self.p_start_var, 999, from_=1, width=4)
        self.make_chk(
            self.play_panel,
            text="Stop at item #:",
            variable=self.use_p_end,
            command=self.save_settings,
        )
        self._make_spinbox(self.play_panel, self.p_end_var, 999, from_=1, width=4)

        self.title_row = self.make_card_frame(org_card.body)
        self.title_row.pack(fill="x", pady=4)
        self.make_card_label(self.title_row, text="Custom Title:").pack(
            side="left"
        )
        self.make_help_badge(
            self.title_row, "Custom Title", EXTRA_HELP["custom_title"]
        ).pack(side="right")
        ttk.Entry(self.title_row, textvariable=self.custom_title_var).pack(
            side="left", fill="x", expand=True, padx=8, ipady=2
        )

        strip_row = self.make_card_frame(org_card.body)
        strip_row.pack(fill="x", pady=(0, 4))
        self.make_chk(
            strip_row,
            text="Strip URLs from video / song titles",
            variable=self.remove_link_title_var,
            command=self.save_settings,
        ).pack(side="left")
        self.make_help_badge(
            strip_row, "Remove Links from Titles", EXTRA_HELP["remove_links"]
        ).pack(side="left", padx=6)

        pl_folder_row = self.make_card_frame(org_card.body)
        pl_folder_row.pack(fill="x", pady=(2, 2))
        self.make_chk(
            pl_folder_row,
            text="Create playlist subfolder (Playlist / Batch Name):",
            variable=self.playlist_folder_var,
            command=self.update_playlist_folder_controls,
        ).pack(side="left")
        self.make_help_badge(
            pl_folder_row, "Playlist & Batch Folder", EXTRA_HELP["playlist_folder"]
        ).pack(side="right")
        self.custom_pl_entry = ttk.Entry(
            pl_folder_row, textvariable=self.custom_playlist_folder_var
        )
        self.custom_pl_entry.pack(side="left", fill="x", expand=True, padx=8, ipady=2)

        batch_pl_row = self.make_card_frame(org_card.body)
        batch_pl_row.pack(fill="x", pady=(2, 2))
        self.make_chk(
            batch_pl_row,
            text="Put batch-downloaded songs into a new playlist folder",
            variable=self.batch_as_playlist_var,
            command=self.on_batch_playlist_toggle,
        ).pack(side="left")

        order_pl_row = self.make_card_frame(org_card.body)
        order_pl_row.pack(fill="x", pady=(2, 0))
        self.make_chk(
            order_pl_row,
            text="Order playlist / batch tracks with numbers (1 - Title)",
            variable=self.playlist_numbering_var,
            command=self.save_settings,
        ).pack(side="left")
        self.make_help_badge(
            order_pl_row, "Playlist Numbering", EXTRA_HELP["playlist_numbers"]
        ).pack(side="left", padx=6)

        # --------------------------------------------------------------------
        # ADVANCED CARD C: COVER ART & SUBTITLES
        # --------------------------------------------------------------------
        meta_card = self.make_card(
            self.advanced_container, title="Cover Art, Metadata & Subtitles"
        )
        meta_card.pack(fill="x", **card_pad)

        cover_row = self.make_card_frame(meta_card.body)
        cover_row.pack(fill="x", pady=(0, 4))
        self.meta_chk = self.make_chk(
            cover_row,
            text="Include cover art & media info",
            variable=self.meta_var,
            command=self.save_settings,
        )
        self.meta_chk.pack(side="left")
        self.make_help_badge(
            cover_row, "Cover Art & Media Info", EXTRA_HELP["meta"]
        ).pack(side="left", padx=6)

        subs_row = self.make_card_wrap(meta_card.body, padx=4, pady=2)
        subs_row.pack(fill="x")
        self.subs_chk = self.make_chk(
            subs_row,
            text="Include subtitles:",
            variable=self.subs_var,
            command=self.on_subs_toggle,
        )
        self.sub_lang_combo = self.make_dropdown(
            subs_row,
            textvariable=self.sub_lang_label_var,
            values=[lbl for lbl, _ in SUB_LANG_PRESETS],
            state="readonly",
            width=18,
        )
        self.sub_lang_combo.bind("<<ComboboxSelected>>", self.on_sub_lang_change)
        self.custom_sub_entry = ttk.Entry(
            subs_row, textvariable=self.custom_sub_lang_var, width=10
        )
        self.custom_sub_entry.bind("<FocusOut>", lambda e: self.save_settings())
        self.make_help_badge(subs_row, "Subtitles", EXTRA_HELP["subtitles"])

        # --------------------------------------------------------------------
        # ACTION BUTTON & PROGRESS LOG CARD (Always visible below Advanced Mode)
        # --------------------------------------------------------------------
        self.btn_wrap = tk.Frame(self.dl_tab)
        self.btn_wrap.pack(fill="x", padx=20, pady=6)

        self.dl_btn = self.make_btn(
            self.btn_wrap,
            text="Download",
            variant="primary",
            height=40,
            font=("Segoe UI", 11, "bold"),
            command=self.on_download_or_cancel,
        )
        self.dl_btn.pack(fill="x", expand=True)

        log_card = self.make_card(self.dl_tab, title="Progress Log")
        log_card.pack(fill="x", padx=20, pady=(4, 16))

        self.log_box_container = self.make_card_frame(log_card.body)
        self.log_box_container.configure(height=145)
        self.log_box_container.pack(fill="x")
        self.log_box_container.pack_propagate(False)

        self.log_scroll = self.make_scrollbar(
            self.log_box_container, orient="vertical", thickness=8
        )
        self.log_scroll.pack(side="right", fill="y", padx=(2, 0))

        self.log_text = tk.Text(
            self.log_box_container,
            font=("Consolas", 9),
            wrap="word",
            yscrollcommand=self.log_scroll.set,
            relief="flat",
            padx=8,
            pady=8,
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        self.log_scroll.config(command=self.log_text.yview)

    # ========================================================================
    # DOWNLOAD QUEUE & FAILED DOWNLOADS UI
    # ========================================================================
    def on_batch_playlist_toggle(self):
        if self.batch_as_playlist_var.get():
            self.playlist_folder_var.set(True)
            self.update_playlist_folder_controls()
        self.save_settings()

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
        links = [
            ln.strip().replace('"', "")
            for ln in clip.splitlines()
            if ln.strip().startswith(("http://", "https://"))
        ]
        if not links:
            messagebox.showwarning(
                "No Links Found",
                "Copy one or more http/https links (one per line) to your clipboard first.",
            )
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
        if not hasattr(self, "queue_listbox"):
            return
        self.queue_listbox.delete(0, "end")
        for i, url in enumerate(self.download_queue, start=1):
            self.queue_listbox.insert("end", f"{i}. {url}")
        count = len(self.download_queue)
        self.queue_lbl.config(text=f"Batch Queue ({count}):")
        if count > 0:
            if not self.queue_frame.winfo_ismapped():
                before_widget = (
                    self.failed_frame
                    if self.failed_frame.winfo_ismapped()
                    else (self.preview_box if self.preview_box.winfo_ismapped() else None)
                )
                self.queue_frame.pack(fill="x", before=before_widget)
        else:
            self.queue_frame.pack_forget()

    def refresh_failed_ui(self):
        if not hasattr(self, "failed_listbox"):
            return
        self.failed_listbox.delete(0, "end")
        for i, item in enumerate(self.failed_downloads, start=1):
            title = item.get("title") or item.get("url") or "Unknown"
            url = item.get("url") or ""
            reason = item.get("reason") or "Failed"
            display = f"{i}. {title} ({url}) — {reason}"
            self.failed_listbox.insert("end", display)
        count = len(self.failed_downloads)
        self.failed_lbl.config(text=f"⚠ Failed Songs / Downloads ({count}):")
        if count > 0:
            self.retry_all_btn.config(text=f"↻ Retry All Failed ({count})")
            if not self.failed_frame.winfo_ismapped():
                before_widget = self.preview_box if self.preview_box.winfo_ismapped() else None
                self.failed_frame.pack(fill="x", before=before_widget)
        else:
            self.failed_frame.pack_forget()

    def clear_url(self):
        self.url_var.set("")
        self.close_preview()

    # ========================================================================
    # PAGE 2: DOWNLOAD HISTORY
    # ========================================================================
    def build_history_tab(self):
        hist_card = self.make_card(self.history_page, title="Downloaded Media Library")
        hist_card.pack(fill="both", expand=True, padx=20, pady=(12, 16))

        top_bar = self.make_card_wrap(hist_card.body, padx=4, pady=2)
        top_bar.pack(fill="x", pady=(0, 6))

        self.hist_count_lbl = self.make_card_label(
            top_bar, text="Downloads: 0", font=("Segoe UI", 10, "bold")
        )
        self.make_btn(
            top_bar,
            text="Open in Browser",
            variant="primary",
            command=self.open_selected_history_link,
        )
        self.make_btn(
            top_bar, text="Open File Location", command=self.open_selected_history_file
        )
        self.make_btn(top_bar, text="Clear History", command=self.clear_history)

        self.make_card_label(
            hist_card.body,
            text="Tip: Click a link to open in browser, or right-click any row to open the file location or re-queue.",
            font=("Segoe UI", 8),
            muted=True,
            justify="left",
            anchor="w",
            wraplength=500,
        ).pack(anchor="w", pady=(0, 8))

        tree_frame = self.make_card_frame(hist_card.body)
        tree_frame.pack(fill="both", expand=True)

        yscroll = self.make_scrollbar(tree_frame, orient="vertical", thickness=8)
        yscroll.pack(side="right", fill="y", padx=(2, 0))
        xscroll = self.make_scrollbar(tree_frame, orient="horizontal", thickness=8)
        xscroll.pack(side="bottom", fill="x", pady=(2, 0))

        cols = ("date", "title", "link", "author")
        self.history_tree = ttk.Treeview(
            tree_frame,
            columns=cols,
            show="headings",
            height=17,
            yscrollcommand=yscroll.set,
            xscrollcommand=xscroll.set,
        )
        self.history_tree.heading("date", text="Date & Time")
        self.history_tree.heading("title", text="Original Title")
        self.history_tree.heading("link", text="Link (Click to Open)")
        self.history_tree.heading("author", text="Author / Creator / Artist")

        self.history_tree.column("date", width=115, minwidth=100, stretch=False)
        self.history_tree.column("title", width=190, minwidth=120)
        self.history_tree.column("link", width=180, minwidth=120)
        self.history_tree.column("author", width=120, minwidth=90)

        self.history_tree.pack(side="left", fill="both", expand=True)
        yscroll.config(command=self.history_tree.yview)
        xscroll.config(command=self.history_tree.xview)

        self.history_tree.bind("<Motion>", self._on_history_hover)
        self.history_tree.bind("<ButtonRelease-1>", self._on_history_click)
        self.history_tree.bind("<Double-1>", lambda e: self.open_selected_history_link())
        self.history_tree.bind("<Button-3>", self._on_history_right_click)

        self.hist_menu = tk.Menu(self, tearoff=0)
        self.hist_menu.add_command(
            label="Open Downloaded File Location", command=self.open_selected_history_file
        )
        self.hist_menu.add_command(
            label="Re-download / Add to Queue", command=self.requeue_selected_history_entry
        )
        self.hist_menu.add_command(
            label="Open Link in Browser", command=self.open_selected_history_link
        )
        self.hist_menu.add_command(label="Copy Link", command=self.copy_selected_history_link)
        self.hist_menu.add_separator()
        self.hist_menu.add_command(
            label="Remove Entry", command=self.remove_selected_history_entry
        )

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

    def open_selected_history_file(self):
        idx = self._get_selected_history_index()
        if idx is None or not (0 <= idx < len(self.history_items)):
            return
        entry = self.history_items[idx]
        filepath = entry.get("filepath", "")

        target_path = filepath if (filepath and os.path.exists(filepath)) else None
        if not target_path:
            found = find_downloaded_file_fallback(entry, self.save_dir_var.get())
            if found and os.path.exists(found):
                target_path = found
                entry["filepath"] = os.path.normpath(found)
                self.save_history()

        if target_path:
            abs_path = os.path.normpath(os.path.abspath(target_path))
            if os.name == "nt":
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

    def requeue_selected_history_entry(self):
        idx = self._get_selected_history_index()
        if idx is None or not (0 <= idx < len(self.history_items)):
            return
        link = self.history_items[idx].get("link", "")
        if link:
            if link not in self.download_queue:
                self.download_queue.append(link)
                self.refresh_queue_ui()
            self.select_page(0)

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
    # PAGE 3: SETTINGS & UPDATES (Exact SongPulse Settings Card Layout)
    # ========================================================================
    def build_settings_tab(self):
        self.settings_canvas = tk.Canvas(self.settings_page, highlightthickness=0, bd=0)
        self.settings_vscroll = self.make_scrollbar(
            self.settings_page, orient="vertical", command=self.settings_canvas.yview
        )
        self.settings_canvas.configure(yscrollcommand=self.settings_vscroll.set)

        self.settings_vscroll.pack(side="right", fill="y", padx=(0, 2), pady=4)
        self.settings_canvas.pack(side="left", fill="both", expand=True)

        self.settings_tab = tk.Frame(self.settings_canvas)
        self.settings_canvas_win = self.settings_canvas.create_window(
            (0, 0), window=self.settings_tab, anchor="nw"
        )

        def _sched_set_bbox(e=None):
            if self._set_bbox_after_id:
                self.after_cancel(self._set_bbox_after_id)
            self._set_bbox_after_id = self.after(
                20,
                lambda: self.settings_canvas.configure(
                    scrollregion=self.settings_canvas.bbox("all")
                )
                if self.settings_canvas.winfo_exists()
                else None,
            )

        self.settings_tab.bind("<Configure>", _sched_set_bbox)

        def _apply_set_w(width):
            self._set_cfg_after_id = None
            if self.settings_canvas.winfo_exists():
                self.settings_canvas.itemconfig(self.settings_canvas_win, width=width)

        def _on_set_canvas_cfg(e):
            if abs(e.width - self._last_set_canvas_w) >= 3:
                if self._last_set_canvas_w == -1:
                    self._last_set_canvas_w = e.width
                    self.settings_canvas.itemconfig(self.settings_canvas_win, width=e.width)
                else:
                    self._last_set_canvas_w = e.width
                    if self._set_cfg_after_id:
                        self.after_cancel(self._set_cfg_after_id)
                    self._set_cfg_after_id = self.after(16, lambda w=e.width: _apply_set_w(w))

        self.settings_canvas.bind("<Configure>", _on_set_canvas_cfg)

        pad = {"padx": 20, "pady": 6}

        # 1. Look, Theme, Window Size & SongPulse Integration
        look_card = self.make_card(
            self.settings_tab, title="Look, Theme & SongPulse Integration"
        )
        look_card.pack(fill="x", padx=20, pady=(12, 6))

        theme_row = self.make_card_wrap(look_card.body, padx=5, pady=3)
        theme_row.pack(fill="x", pady=(0, 4))
        self.make_card_label(
            theme_row, text="Theme:", font=("Segoe UI", 9, "bold")
        )
        self.theme_combo = self.make_dropdown(
            theme_row,
            textvariable=self.theme_label_var,
            values=[lbl for lbl, _ in THEME_MODES],
            state="readonly",
            width=24,
        )
        self.theme_combo.bind("<<ComboboxSelected>>", lambda e: self.on_theme_change())

        # Remember Window Size Row
        win_size_row = self.make_card_frame(look_card.body)
        win_size_row.pack(fill="x", pady=(0, 6))
        self.make_chk(
            win_size_row,
            text=f"Remember window size (Default: {DEFAULT_WINDOW_WIDTH}×{DEFAULT_WINDOW_HEIGHT})",
            variable=self.remember_win_size_var,
            command=self.on_remember_win_size_toggle,
        ).pack(side="left")

        # SongPulse Protocol Row
        sp_row = self.make_card_wrap(look_card.body, padx=4, pady=3)
        sp_row.pack(fill="x", pady=(0, 6))
        self.update_protocol_status_label()
        self.make_card_label(
            sp_row, textvariable=self.protocol_status_var, font=("Segoe UI", 9, "bold")
        )
        self.make_help_badge(sp_row, "SongPulse Integration", EXTRA_HELP["songpulse"])
        self.make_btn(
            sp_row,
            text="Register / Repair ytdlp:// Protocol",
            height=29,
            command=self.on_register_protocol_click,
        )

        # Reset All Settings Button at the bottom of Look, Theme & SongPulse Integration
        reset_row = self.make_card_frame(look_card.body)
        reset_row.pack(fill="x", pady=(2, 0))
        self.make_btn(
            reset_row,
            text="Reset All Settings",
            variant="danger",
            height=29,
            command=self.reset_all_settings,
        ).pack(side="left")

        # 2. Browser Cookies & Authentication
        cookie_card = self.make_card(
            self.settings_tab,
            title="Browser Cookies & Authentication (Preview & Download)",
        )
        cookie_card.pack(fill="x", **pad)

        c_row1 = self.make_card_wrap(cookie_card.body, padx=4, pady=3)
        c_row1.pack(fill="x", pady=(0, 6))
        self.make_card_label(
            c_row1, text="Browser Cookies:", font=("Segoe UI", 9, "bold")
        )
        self.cookie_combo = self.make_dropdown(
            c_row1,
            textvariable=self.cookie_browser_label_var,
            values=[lbl for lbl, _ in COOKIE_BROWSERS],
            state="readonly",
            width=32,
        )
        self.cookie_combo.bind("<<ComboboxSelected>>", lambda e: self.save_settings())
        self.make_help_badge(
            c_row1, "Browser Cookies & Chrome Fix", EXTRA_HELP["cookies"]
        )

        c_row2 = self.make_card_frame(cookie_card.body)
        c_row2.pack(fill="x")
        self.make_chk(
            c_row2,
            text="Use cookies.txt (Chrome / Brave):",
            variable=self.use_cookie_file_var,
            command=self.save_settings,
        ).pack(side="left")
        self.make_help_badge(
            c_row2, "How to Use Chrome Cookies", EXTRA_HELP["cookies"]
        ).pack(side="right", padx=(4, 0))
        self.make_btn(
            c_row2, text="Browse...", height=29, command=self.browse_cookie_file
        ).pack(side="right", padx=2)
        ttk.Entry(c_row2, textvariable=self.cookie_file_path_var).pack(
            side="left", fill="x", expand=True, padx=6, ipady=2
        )

        # 3. yt-dlp Engine, Preferred Dependencies & On-Demand Install/Cleanup
        upd_card = self.make_card(
            self.settings_tab,
            title="yt-dlp Engine, FFmpeg & Node.js Dependencies",
        )
        upd_card.pack(fill="both", expand=True, padx=20, pady=(6, 18))

        pref_row = self.make_card_wrap(upd_card.body, padx=4, pady=3)
        pref_row.pack(fill="x", pady=(0, 4))
        self.make_card_label(
            pref_row, text="Preferred Dependency Source:", font=("Segoe UI", 9, "bold")
        )
        self.dep_pref_combo = self.make_dropdown(
            pref_row,
            textvariable=self.dep_pref_label_var,
            values=[lbl for lbl, _ in DEPENDENCY_PREF_MODES],
            state="readonly",
            width=40,
        )
        self.dep_pref_combo.bind("<<ComboboxSelected>>", self.on_dep_pref_change)

        ver_row = self.make_card_wrap(upd_card.body, padx=6, pady=2)
        ver_row.pack(fill="x", pady=2)
        self.make_card_label(
            ver_row, textvariable=self.version_var, font=("Segoe UI", 10, "bold")
        )
        self.make_card_label(
            ver_row, textvariable=self.app_ver_var, font=("Segoe UI", 9), muted=True
        )

        btn_row1 = self.make_card_wrap(upd_card.body, padx=4, pady=3)
        btn_row1.pack(fill="x", pady=2)

        self.chk_ver_btn = self.make_btn(
            btn_row1, text="Check Status & Versions", command=self.check_ytdlp_version
        )
        self.upd_btn = self.make_btn(
            btn_row1, text="Update yt-dlp Now", variant="primary", command=self.update_ytdlp
        )
        self.app_upd_btn = self.make_btn(
            btn_row1,
            text=f"Update App ({GITHUB_REPO})",
            command=self.check_and_update_app,
        )

        btn_row2 = self.make_card_wrap(upd_card.body, padx=4, pady=3)
        btn_row2.pack(fill="x", pady=2)

        self.dl_ffmpeg_btn = self.make_btn(
            btn_row2,
            text="⬇ Download / Redownload FFmpeg",
            command=self.on_download_ffmpeg_click,
        )
        self.dl_node_btn = self.make_btn(
            btn_row2,
            text="⬇ Download / Redownload Node.js",
            command=self.on_download_node_click,
        )
        self.cleanup_dep_btn = self.make_btn(
            btn_row2,
            text="🗑 Clean Up Local Files",
            command=self.on_cleanup_dependencies_click,
        )

        self.make_card_label(
            upd_card.body, text="Dependency Status & Update Log:", muted=True
        ).pack(anchor="w", pady=(6, 4))

        upd_log_inner = self.make_card_frame(upd_card.body)
        upd_log_inner.pack(fill="both", expand=True)

        upd_scroll = self.make_scrollbar(
            upd_log_inner, orient="vertical", thickness=8
        )
        upd_scroll.pack(side="right", fill="y", padx=(2, 0))

        self.upd_log_text = tk.Text(
            upd_log_inner,
            height=9,
            font=("Consolas", 9),
            wrap="word",
            yscrollcommand=upd_scroll.set,
            relief="flat",
            padx=8,
            pady=8,
        )
        self.upd_log_text.pack(side="left", fill="both", expand=True)
        upd_scroll.config(command=self.upd_log_text.yview)

    def on_remember_win_size_toggle(self):
        if self.remember_win_size_var.get():
            self.saved_win_width = max(MIN_WINDOW_WIDTH, self.winfo_width())
            self.saved_win_height = max(MIN_WINDOW_HEIGHT, self.winfo_height())
        self.save_settings()

    # ========================================================================
    # PAGE 4: ABOUT / INFO (What yt-dlp is, Supported Sites & How to Use)
    # ========================================================================
    def build_about_tab(self):
        self.about_canvas = tk.Canvas(self.about_page, highlightthickness=0, bd=0)
        self.about_vscroll = self.make_scrollbar(
            self.about_page, orient="vertical", command=self.about_canvas.yview
        )
        self.about_canvas.configure(yscrollcommand=self.about_vscroll.set)

        self.about_vscroll.pack(side="right", fill="y", padx=(0, 2), pady=4)
        self.about_canvas.pack(side="left", fill="both", expand=True)

        self.about_tab = tk.Frame(self.about_canvas)
        self.about_canvas_win = self.about_canvas.create_window(
            (0, 0), window=self.about_tab, anchor="nw"
        )

        def _sched_abt_bbox(e=None):
            if self._abt_bbox_after_id:
                self.after_cancel(self._abt_bbox_after_id)
            self._abt_bbox_after_id = self.after(
                20,
                lambda: self.about_canvas.configure(
                    scrollregion=self.about_canvas.bbox("all")
                )
                if self.about_canvas.winfo_exists()
                else None,
            )

        self.about_tab.bind("<Configure>", _sched_abt_bbox)

        def _apply_abt_w(width):
            self._abt_cfg_after_id = None
            if self.about_canvas.winfo_exists():
                self.about_canvas.itemconfig(self.about_canvas_win, width=width)

        def _on_abt_canvas_cfg(e):
            if abs(e.width - self._last_abt_canvas_w) >= 3:
                if self._last_abt_canvas_w == -1:
                    self._last_abt_canvas_w = e.width
                    self.about_canvas.itemconfig(self.about_canvas_win, width=e.width)
                else:
                    self._last_abt_canvas_w = e.width
                    if self._abt_cfg_after_id:
                        self.after_cancel(self._abt_cfg_after_id)
                    self._abt_cfg_after_id = self.after(16, lambda w=e.width: _apply_abt_w(w))

        self.about_canvas.bind("<Configure>", _on_abt_canvas_cfg)

        pad = {"padx": 20, "pady": 6}

        # Card 1: What is yt-dlp & How the Engine Works
        what_card = self.make_card(
            self.about_tab,
            title=f"What is yt-dlp Media Downloader? (v{APP_VERSION})",
        )
        what_card.pack(fill="x", padx=20, pady=(12, 6))

        what_text = (
            "yt-dlp is a fast, open-source media downloader engine capable of downloading video and audio streams "
            "from thousands of websites at their highest native quality.\n\n"
            "This app wraps yt-dlp in a clean desktop interface and pairs it with two companion tools:\n"
            "• FFmpeg & FFprobe — Merges separate 1080p/4K video and audio streams, converts music to MP3/FLAC/WAV/M4A, "
            "embeds album cover art & metadata tags, cuts time clips, and powers the built-in live preview player.\n"
            "• Node.js — Executes JavaScript signature challenges required by YouTube so downloads aren't throttled or blocked."
        )
        self.make_card_label(
            what_card.body,
            text=what_text,
            justify="left",
            anchor="w",
            wraplength=540,
        ).pack(fill="x", pady=(0, 8))

        links_row = self.make_card_wrap(what_card.body, padx=4, pady=3)
        links_row.pack(fill="x")
        self.make_btn(
            links_row,
            text="App GitHub Repository",
            variant="primary",
            height=29,
            command=lambda: webbrowser.open(f"https://github.com/{GITHUB_REPO}"),
        )
        self.make_btn(
            links_row,
            text="SongPulse Repository",
            height=29,
            command=lambda: webbrowser.open("https://github.com/Greatly07/songpulse"),
        )
        self.make_btn(
            links_row,
            text="Official yt-dlp Project",
            height=29,
            command=lambda: webbrowser.open("https://github.com/yt-dlp/yt-dlp"),
        )

        # Card 2: Which Site Links Work?
        sites_card = self.make_card(
            self.about_tab,
            title="Which Website Links Work? (1,000+ Supported Sites)",
        )
        sites_card.pack(fill="x", **pad)

        sites_text = (
            "You can paste direct links from over 1,000 video, music, and social platforms, including:\n\n"
            "• YouTube & YouTube Music — Single videos, Shorts, songs, albums, channels, and full playlists\n"
            "• SoundCloud & Bandcamp — Single tracks, albums, sets, and artist pages\n"
            "• TikTok & Instagram — Videos, Reels, and public posts (use Cookies in Settings for login-walled posts)\n"
            "• Twitter / X & Reddit — Embedded video and audio clips (enable 'Strip URLs from titles' for clean filenames)\n"
            "• Twitch & Kick — VODs and Clips\n"
            "• Vimeo, Dailymotion, Bilibili, Facebook, Pinterest, Tumblr, and direct media streams (.mp4 / .m3u8)"
        )
        self.make_card_label(
            sites_card.body,
            text=sites_text,
            justify="left",
            anchor="w",
            wraplength=540,
        ).pack(fill="x", pady=(0, 8))

        self.make_btn(
            sites_card.body,
            text="View Full List of Supported Sites (yt-dlp Docs) ↗",
            height=28,
            command=lambda: webbrowser.open(
                "https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md"
            ),
        ).pack(anchor="w")

        # Card 3: How to Use yt-dlp Downloader
        guide_card = self.make_card(
            self.about_tab,
            title="How to Use yt-dlp Downloader",
        )
        guide_card.pack(fill="x", padx=20, pady=(6, 18))

        guide_text = (
            "1. Pick a Quick Preset (or Open Advanced Mode)\n"
            "   • Video: Downloads MP4 at the highest available resolution with cover art & metadata.\n"
            "   • Music: Extracts MP3 at Best Audio quality with embedded cover art & song metadata.\n"
            "   • Playlist: Can be toggled ON alongside either Video or Music to save tracks into a new playlist folder with numbered filenames (1 - Title).\n"
            "   • Click 'Save as Preset' anytime to save your own custom configuration into the 'Custom Preset' dropdown.\n\n"
            "2. Download, Batch Queue, or Launch from SongPulse\n"
            "   • Paste a link in the Media Link box and click 'Download', or click '+ Queue' / 'Paste Multi-Links' to batch download multiple songs into a playlist folder.\n\n"
            "3. Preview & Cut Time Clips\n"
            "   • Click '▶ Preview' to stream the video or song before downloading, and use 'Set Clip Start' / 'Set Clip End' to cut a clip.\n\n"
            "4. Retry Failed Songs & Fix Restricted Links\n"
            "   • Failed songs appear automatically in the '⚠ Failed Songs' box — click '↻ Retry All Failed' to redownload them."
        )
        self.make_card_label(
            guide_card.body,
            text=guide_text,
            justify="left",
            anchor="w",
            wraplength=540,
        ).pack(fill="x")

    def browse_cookie_file(self):
        chosen = filedialog.askopenfilename(
            title="Select Netscape cookies.txt File",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )
        if chosen:
            self.cookie_file_path_var.set(os.path.normpath(chosen))
            self.use_cookie_file_var.set(True)
            self.save_settings()

    def update_protocol_status_label(self):
        ok = is_songpulse_protocol_registered()
        self.protocol_status_var.set(
            "✔ SongPulse Protocol (ytdlp://): Registered"
            if ok
            else "⚠ SongPulse Protocol (ytdlp://): Not Registered"
        )

    def on_register_protocol_click(self):
        ok, msg = register_songpulse_protocol()
        self.update_protocol_status_label()
        self._append_upd_log(msg + "\n")
        if ok:
            messagebox.showinfo("SongPulse Protocol", msg)
        else:
            messagebox.showwarning("SongPulse Protocol", msg)

    def on_dep_pref_change(self, event=None):
        self.save_settings()
        self.update_dependency_feature_states()
        self.check_ytdlp_version()

    def on_download_ffmpeg_click(self):
        self.dl_ffmpeg_btn.config(state="disabled")
        self.upd_log_text.delete("1.0", "end")
        self._append_upd_log("Starting FFmpeg & FFprobe download into App Folder...\n")

        def worker():
            try:
                download_ffmpeg_to_app_dir(
                    progress_cb=lambda msg: self.after(0, self._append_upd_log, msg)
                )
                self.after(0, self.update_dependency_feature_states)
                self.after(0, self.check_ytdlp_version)
            except Exception as e:
                self.after(0, self._append_upd_log, f"\n✖ FFmpeg download failed: {e}\n")
            finally:
                self.after(0, lambda: self.dl_ffmpeg_btn.config(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def on_download_node_click(self):
        self.dl_node_btn.config(state="disabled")
        self.upd_log_text.delete("1.0", "end")
        self._append_upd_log("Starting Node.js download into App Folder...\n")

        def worker():
            try:
                download_nodejs_to_app_dir(
                    progress_cb=lambda msg: self.after(0, self._append_upd_log, msg)
                )
                self.after(0, self.update_dependency_feature_states)
                self.after(0, self.check_ytdlp_version)
            except Exception as e:
                self.after(0, self._append_upd_log, f"\n✖ Node.js download failed: {e}\n")
            finally:
                self.after(0, lambda: self.dl_node_btn.config(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def on_cleanup_dependencies_click(self):
        local_present = [
            name
            for name, p in (
                ("ffmpeg.exe", FFMPEG_PATH),
                ("ffprobe.exe", FFPROBE_PATH),
                ("node.exe", NODE_PATH),
            )
            if os.path.isfile(p)
        ]
        if not local_present:
            messagebox.showinfo(
                "No Local Files to Clean Up",
                "There are no local ffmpeg.exe, ffprobe.exe, or node.exe files in the App Folder.",
            )
            return

        missing_global = [name for name in local_present if not find_global_binary(name)]
        warn_extra = ""
        if missing_global:
            warn_extra = (
                f"\n\n⚠ Warning: {', '.join(missing_global)} is NOT on your system Global PATH. "
                "Deleting the local copy will disable features that depend on it until you download it again."
            )

        if not messagebox.askyesno(
            "Clean Up Local Dependencies",
            f"Delete local {', '.join(local_present)} from the App Folder?{warn_extra}",
        ):
            return

        removed, skipped, errors = cleanup_local_dependencies(only_if_global=False)
        self.upd_log_text.delete("1.0", "end")
        if removed:
            self._append_upd_log(f"✔ Removed from App Folder: {', '.join(removed)}\n")
        if skipped:
            self._append_upd_log(f"Skipped: {', '.join(skipped)}\n")
        if errors:
            self._append_upd_log(f"✖ Errors: {', '.join(errors)}\n")
        self.update_dependency_feature_states()
        self.check_ytdlp_version()

    def reset_all_settings(self):
        if not messagebox.askyesno(
            "Reset Settings",
            "Reset all format, quality, clip, subtitle, cookie, folder, window size, and theme options back to default?\n\n"
            "(Your Download History and Custom Presets will NOT be deleted.)",
        ):
            return
        try:
            if os.path.exists(SETTINGS_FILE):
                os.remove(SETTINGS_FILE)
        except OSError:
            pass

        self.save_dir_var.set(DEFAULT_SAVE_DIR)
        self.custom_title_var.set("")
        self.remove_link_title_var.set(True)
        self.custom_playlist_folder_var.set("")
        self.playlist_folder_var.set(False)
        self.playlist_numbering_var.set(False)
        self.batch_as_playlist_var.set(False)
        self.sub_lang_label_var.set("English (en)")
        self.custom_sub_lang_var.set("en,id")
        self.cookie_browser_label_var.set("None (Disabled)")
        self.use_cookie_file_var.set(False)
        self.cookie_file_path_var.set("")
        self.dep_pref_label_var.set("Prefer System Global PATH (Fallback to App Folder)")
        self.theme_mode.set("system")
        self.theme_label_var.set(THEME_VAL_TO_LABEL["system"])
        self.remember_win_size_var.set(False)
        self.saved_win_width = DEFAULT_WINDOW_WIDTH
        self.saved_win_height = DEFAULT_WINDOW_HEIGHT
        self.geometry(f"{DEFAULT_WINDOW_WIDTH}x{DEFAULT_WINDOW_HEIGHT}")

        self.apply_quick_media_preset("video")
        self.apply_theme(force=True)
        self.save_settings()
        messagebox.showinfo(
            "Settings Reset", "All settings have been restored to their default values."
        )

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
        msg = (
            f"A new version (v{latest_tag}) is available on GitHub!\n\n"
            f"Current version: v{APP_VERSION}\n\nUpdate and restart now?"
        )
        if not messagebox.askyesno("Update Available", msg):
            self._append_upd_log("Update cancelled by user.\n")
            return

        self.app_upd_btn.config(state="disabled")
        self._append_upd_log(f"Downloading v{latest_tag} from GitHub...\n")
        threading.Thread(target=self._download_and_swap_app, args=(dl_url,), daemon=True).start()

    def _download_and_swap_app(self, dl_url):
        try:
            is_frozen = getattr(sys, "frozen", False)
            current_file = (
                sys.executable
                if is_frozen
                else os.path.join(APP_DIR, "yt_dlp_app.pyw")
            )
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
                # Strip PyInstaller's bootloader env vars so the relaunched exe
                # extracts its own fresh temp dir instead of reusing this
                # (soon-to-be-deleted) _MEIxxxx folder -> "Failed to load Python DLL".
                clean_env = {
                    k: v for k, v in os.environ.items()
                    if not (k.startswith("_PYI") or k.startswith("_MEIPASS"))
                }
                subprocess.Popen(
                    ["cmd.exe", "/c", bat_path],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    env=clean_env,
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
    # UI CONTROL STATE HELPERS & SONGPULSE THEME ENGINE
    # ========================================================================
    def refresh_format_options(self):
        if not hasattr(self, "format_combo"):
            return
        is_video = self.media_type.get() == "video"
        has_ffmpeg = bool(self.get_ffmpeg_exe())

        if is_video:
            labels = [lbl for _, lbl, _ in VIDEO_FORMATS]
            desc_map = VIDEO_FMT_DESC_MAP
            cur_val = self.video_fmt.get()
            cur_lbl = VIDEO_FMT_VAL_TO_LABEL.get(cur_val, labels[0])
            self.format_combo.configure(values=labels, item_descriptions=desc_map)
            self.format_label_var.set(cur_lbl)
            self.format_help_badge.title = cur_lbl
            self.format_help_badge.description = desc_map.get(cur_lbl, "")
        else:
            if not has_ffmpeg:
                self.audio_fmt.set("orig")
                labels = [AUDIO_FMT_VAL_TO_LABEL["orig"]]
            else:
                labels = [lbl for _, lbl, _ in AUDIO_FORMATS]
            desc_map = AUDIO_FMT_DESC_MAP
            cur_val = self.audio_fmt.get()
            cur_lbl = AUDIO_FMT_VAL_TO_LABEL.get(cur_val, labels[0])
            self.format_combo.configure(values=labels, item_descriptions=desc_map)
            self.format_label_var.set(cur_lbl)
            self.format_help_badge.title = cur_lbl
            self.format_help_badge.description = desc_map.get(cur_lbl, "")

        self.update_quality_controls()
        self.update_subtitle_controls()

    def on_format_dropdown_change(self, event=None):
        chosen_lbl = self.format_label_var.get()
        if self.media_type.get() == "video":
            val = VIDEO_FMT_LABEL_TO_VAL.get(chosen_lbl, "mp4")
            self.video_fmt.set(val)
            self.format_help_badge.title = chosen_lbl
            self.format_help_badge.description = VIDEO_FMT_DESC_MAP.get(chosen_lbl, "")
        else:
            val = AUDIO_FMT_LABEL_TO_VAL.get(chosen_lbl, "mp3")
            self.audio_fmt.set(val)
            self.format_help_badge.title = chosen_lbl
            self.format_help_badge.description = AUDIO_FMT_DESC_MAP.get(chosen_lbl, "")
        self.save_settings()

    def update_quality_controls(self):
        if not hasattr(self, "quality_combo"):
            return
        is_video = self.media_type.get() == "video"
        has_ffmpeg = bool(self.get_ffmpeg_exe())
        use_custom = self.use_custom_res_var.get() and has_ffmpeg

        if not is_video:
            self.quality_combo.configure(state="disabled")
            self.custom_res_chk.configure(state="disabled")
            self.custom_res_entry.configure(state="disabled")
            self.audio_quality_combo.configure(state="readonly" if has_ffmpeg else "disabled")
        else:
            self.custom_res_chk.configure(state="normal" if has_ffmpeg else "disabled")
            self.quality_combo.configure(state="disabled" if use_custom else "readonly")
            self.custom_res_entry.configure(state="normal" if use_custom else "disabled")
            self.audio_quality_combo.configure(state="readonly")
        self.sync_active_preset_from_options()

    def on_subs_toggle(self):
        self.update_subtitle_controls()
        self.save_settings()

    def on_sub_lang_change(self, event=None):
        self.update_subtitle_controls()
        self.save_settings()

    def update_subtitle_controls(self):
        if not hasattr(self, "subs_chk"):
            return
        is_video = self.media_type.get() == "video"
        has_ffmpeg = bool(self.get_ffmpeg_exe())
        can_sub = is_video and has_ffmpeg
        enabled = can_sub and self.subs_var.get()
        is_custom = SUB_LABEL_TO_VAL.get(self.sub_lang_label_var.get()) == "custom"

        self.subs_chk.configure(state="normal" if can_sub else "disabled")
        self.sub_lang_combo.configure(state="readonly" if enabled else "disabled")
        self.custom_sub_entry.configure(state="normal" if (enabled and is_custom) else "disabled")

    def update_playlist_folder_controls(self):
        state = "normal" if self.playlist_folder_var.get() else "disabled"
        if hasattr(self, "custom_pl_entry"):
            self.custom_pl_entry.configure(state=state)
        if hasattr(self, "quick_pl_folder_entry"):
            self.quick_pl_folder_entry.configure(state=state)
        self.save_settings()

    def on_media_type_change(self):
        self.refresh_format_options()
        self.save_settings()

    def on_theme_change(self):
        self.theme_mode.set(
            THEME_LABEL_TO_VAL.get(self.theme_label_var.get(), "system")
        )
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
        pal = get_palette(is_dark)

        style = ttk.Style(self)
        style.theme_use("clam")

        bg = pal["bg"]
        nav_bg = pal["sidebar_bg"]
        card_bg = pal["card_bg"]
        input_bg = pal["input_bg"]
        border = pal["input_border"]
        fg = pal["fg"]
        fg_sec = pal["fg_secondary"]
        muted_fg = pal["fg_muted"]

        self.configure(bg=bg)
        self.main_area.configure(bg=bg)
        set_windows_titlebar_dark(self, is_dark)

        # Sticky Top Navbar Styling
        self.navbar.configure(bg=nav_bg)
        self.navbar_divider.configure(bg=pal["sidebar_border"])
        for nav_btn in self.nav_buttons:
            nav_btn.redraw()

        # Page Backgrounds
        for page in self.pages:
            page.configure(bg=bg)
        self.dl_canvas.configure(bg=bg)
        self.dl_tab.configure(bg=bg)
        self.adv_bar_wrap.configure(bg=bg)
        self.advanced_container.configure(bg=bg)
        self.btn_wrap.configure(bg=bg)
        if hasattr(self, "settings_canvas"):
            self.settings_canvas.configure(bg=bg)
            self.settings_tab.configure(bg=bg)
        if hasattr(self, "about_canvas"):
            self.about_canvas.configure(bg=bg)
            self.about_tab.configure(bg=bg)

        # Update all Cards, Frames, Labels, Checkboxes, Radios, Buttons, Dropdowns, Pill Scrollbars & Badges
        self.themed_frames = [f for f in self.themed_frames if f.winfo_exists()]
        for f in self.themed_frames:
            f.configure(bg=card_bg)

        self.themed_labels = [(l, m) for l, m in self.themed_labels if l.winfo_exists()]
        for lbl, is_muted in self.themed_labels:
            lbl.configure(bg=card_bg, fg=muted_fg if is_muted else fg_sec)

        self.rounded_cards = [c for c in self.rounded_cards if c.winfo_exists()]
        for card in self.rounded_cards:
            card.update_theme()

        self.sp_checkboxes = [c for c in self.sp_checkboxes if c.winfo_exists()]
        for chk in self.sp_checkboxes:
            chk.redraw()

        self.sp_radios = [r for r in self.sp_radios if r.winfo_exists()]
        for rb in self.sp_radios:
            rb.redraw()

        self.rounded_buttons = [b for b in self.rounded_buttons if b.winfo_exists()]
        for btn in self.rounded_buttons:
            btn.redraw()

        self.sp_dropdowns = [d for d in self.sp_dropdowns if d.winfo_exists()]
        for dd in self.sp_dropdowns:
            dd.redraw()

        self.pill_scrollbars = [s for s in self.pill_scrollbars if s.winfo_exists()]
        for sb in self.pill_scrollbars:
            sb.redraw()

        # TTK Entry, Spinbox & Treeview styling
        style.configure(
            ".",
            background=card_bg,
            foreground=fg,
            bordercolor=border,
            darkcolor=input_bg,
            lightcolor=input_bg,
            font=("Segoe UI", 9),
        )
        style.configure("TFrame", background=card_bg)
        style.configure("TLabel", background=card_bg, foreground=fg_sec)

        style.configure(
            "TEntry",
            fieldbackground=input_bg,
            background=card_bg,
            foreground=fg,
            insertcolor=fg,
            bordercolor=border,
            lightcolor=border,
            darkcolor=border,
            padding=4,
        )
        style.map(
            "TEntry",
            background=[("readonly", card_bg), ("disabled", card_bg)],
            fieldbackground=[("readonly", input_bg), ("disabled", card_bg)],
            foreground=[("disabled", pal["fg_disabled"])],
        )

        style.configure(
            "TSpinbox",
            fieldbackground=input_bg,
            background=input_bg,
            foreground=fg,
            insertcolor=fg,
            arrowcolor=fg_sec,
            bordercolor=border,
            lightcolor=border,
            darkcolor=border,
            padding=3,
        )
        style.configure(
            "Horizontal.TProgressbar",
            background=pal["accent"],
            troughcolor=input_bg,
            bordercolor=border,
        )

        style.configure(
            "Treeview",
            background=input_bg,
            fieldbackground=input_bg,
            foreground=fg,
            bordercolor=border,
            rowheight=26,
        )
        style.configure(
            "Treeview.Heading",
            background=card_bg,
            foreground=fg,
            bordercolor=border,
            font=("Segoe UI", 9, "bold"),
        )
        style.map(
            "Treeview",
            background=[("selected", pal["primary"])],
            foreground=[("selected", "#ffffff")],
        )

        if hasattr(self, "url_placeholder"):
            self.url_placeholder.configure(bg=input_bg, fg=muted_fg)

        self.log_text.configure(
            bg=pal["log_bg"],
            fg=pal["log_fg"],
            insertbackground=pal["log_fg"],
            highlightbackground=border,
            highlightthickness=1,
        )
        self.upd_log_text.configure(
            bg=pal["log_bg"],
            fg=pal["log_fg"],
            insertbackground=pal["log_fg"],
            highlightbackground=border,
            highlightthickness=1,
        )
        self.queue_listbox.configure(
            bg=input_bg,
            fg=fg,
            selectbackground=pal["primary"],
            selectforeground="#ffffff",
            highlightbackground=border,
        )
        self.failed_listbox.configure(
            bg=pal["fail_bg"],
            fg=pal["fail_fg"],
            selectbackground="#e11d48",
            selectforeground="#ffffff",
            highlightbackground="#e11d48",
        )

        self.preview_slider.set_theme(
            card_bg, pal["slider_track"], pal["accent"], pal["slider_thumb"]
        )
        self.vol_slider.set_theme(
            card_bg, pal["slider_track"], pal["accent"], pal["slider_thumb"]
        )

        self.help_badges = [b for b in self.help_badges if b.winfo_exists()]
        for badge in self.help_badges:
            badge.update_colors()

        self.update_dependency_feature_states()

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

    def _update_url_placeholder(self, event=None):
        if not hasattr(self, "url_placeholder"):
            return
        try:
            focused = self.focus_get()
        except Exception:
            focused = None
        if self.url_var.get() or focused is self.url_entry:
            self.url_placeholder.place_forget()
        else:
            self.url_placeholder.place(relx=0.0, rely=0.5, x=7, anchor="w")

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
            self.dur_panel.pack(fill="x", padx=4, pady=3, before=self.title_row)
            self.dur_panel.rearrange()
        elif choice == "3":
            self.play_panel.pack(fill="x", padx=4, pady=3, before=self.title_row)
            self.play_panel.rearrange()

    # ========================================================================
    # DEPENDENCY & YT-DLP VERSION CHECKS
    # ========================================================================
    def check_ytdlp_version(self):
        self.update_dependency_feature_states()
        self.update_protocol_status_label()
        self.version_var.set("yt-dlp version: Checking...")
        pref_mode = self.get_dep_pref_mode()
        if hasattr(self, "upd_log_text"):
            self.upd_log_text.delete("1.0", "end")
            mode_title = (
                "System Global PATH Preferred"
                if pref_mode == "global"
                else "App Folder (Local) Preferred"
            )
            self.upd_log_text.insert(
                "end", f"=== Dependency Source Check ({mode_title}) ===\n"
            )
            for bin_name, local_p in (
                ("yt-dlp.exe", os.path.join(APP_DIR, "yt-dlp.exe")),
                ("ffmpeg.exe", FFMPEG_PATH),
                ("ffprobe.exe", FFPROBE_PATH),
                ("node.exe", NODE_PATH),
            ):
                self.upd_log_text.insert(
                    "end", describe_binary_status(bin_name, local_p, pref_mode) + "\n"
                )
            self.upd_log_text.insert(
                "end", "===============================================================\n\n"
            )
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
        self.sync_active_preset_from_options()
        if self.remember_win_size_var.get():
            cur_w = self.winfo_width()
            cur_h = self.winfo_height()
            if cur_w >= MIN_WINDOW_WIDTH and cur_h >= MIN_WINDOW_HEIGHT:
                self.saved_win_width = cur_w
                self.saved_win_height = cur_h

        data = {
            "custom_preset": self.custom_preset_var.get(),
            "save_dir": self.save_dir_var.get(),
            "media_type": self.media_type.get(),
            "video_fmt": self.video_fmt.get(),
            "audio_fmt": self.audio_fmt.get(),
            "quality_choice": QUALITY_LABEL_TO_VAL.get(self.quality_label_var.get(), "best"),
            "audio_quality_choice": AUDIO_QUALITY_LABEL_TO_VAL.get(
                self.audio_quality_label_var.get(), "best"
            ),
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
            "playlist_folder": self.playlist_folder_var.get(),
            "playlist_numbering": self.playlist_numbering_var.get(),
            "batch_as_playlist": self.batch_as_playlist_var.get(),
            "meta": self.meta_var.get(),
            "subs": self.subs_var.get(),
            "sub_lang": SUB_LABEL_TO_VAL.get(self.sub_lang_label_var.get(), "en.*,en"),
            "custom_sub_lang": self.custom_sub_lang_var.get(),
            "cookie_browser": COOKIE_LABEL_TO_VAL.get(
                self.cookie_browser_label_var.get(), "none"
            ),
            "use_cookie_file": self.use_cookie_file_var.get(),
            "cookie_file_path": self.cookie_file_path_var.get(),
            "dependency_pref": self.get_dep_pref_mode(),
            "theme_mode": self.theme_mode.get(),
            "remember_window_size": self.remember_win_size_var.get(),
            "window_width": self.saved_win_width,
            "window_height": self.saved_win_height,
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
            c_preset = data.get("custom_preset", "None")
            if c_preset in self.custom_presets:
                self.custom_preset_var.set(c_preset)
            self.save_dir_var.set(data.get("save_dir", DEFAULT_SAVE_DIR))
            self.media_type.set(data.get("media_type", "video"))
            self.video_fmt.set(data.get("video_fmt", "mp4"))
            self.audio_fmt.set(data.get("audio_fmt", "mp3"))
            q_val = data.get("quality_choice", "best")
            self.quality_label_var.set(QUALITY_VAL_TO_LABEL.get(q_val, "Auto (Best)"))
            aq_val = data.get("audio_quality_choice", "best")
            self.audio_quality_label_var.set(
                AUDIO_QUALITY_VAL_TO_LABEL.get(aq_val, "Auto (Best Audio)")
            )
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
            self.remove_link_title_var.set(data.get("remove_link_title", True))
            self.playlist_folder_var.set(data.get("playlist_folder", False))
            self.playlist_numbering_var.set(data.get("playlist_numbering", False))
            self.batch_as_playlist_var.set(data.get("batch_as_playlist", False))
            self.meta_var.set(data.get("meta", True))
            self.subs_var.set(data.get("subs", False))
            sub_val = data.get("sub_lang", "en.*,en")
            self.sub_lang_label_var.set(SUB_VAL_TO_LABEL.get(sub_val, "English (en)"))
            self.custom_sub_lang_var.set(data.get("custom_sub_lang", "en,id"))
            ck_val = data.get("cookie_browser", "none")
            self.cookie_browser_label_var.set(
                COOKIE_VAL_TO_LABEL.get(ck_val, "None (Disabled)")
            )
            self.use_cookie_file_var.set(data.get("use_cookie_file", False))
            self.cookie_file_path_var.set(data.get("cookie_file_path", ""))
            dep_val = data.get("dependency_pref", "global")
            self.dep_pref_label_var.set(
                DEP_PREF_VAL_TO_LABEL.get(
                    dep_val, "Prefer System Global PATH (Fallback to App Folder)"
                )
            )
            self.theme_mode.set(data.get("theme_mode", "system"))
            self.theme_label_var.set(
                THEME_VAL_TO_LABEL.get(self.theme_mode.get(), "Match Windows")
            )
            self.remember_win_size_var.set(bool(data.get("remember_window_size", False)))
            self.saved_win_width = int(data.get("window_width", DEFAULT_WINDOW_WIDTH))
            self.saved_win_height = int(data.get("window_height", DEFAULT_WINDOW_HEIGHT))
        except Exception:
            pass

    def on_close(self):
        if self.is_downloading:
            self.cancel_download()
        self.stop_preview_streams()
        self.save_settings()
        self.destroy()
