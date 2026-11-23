import os
import sys

# ============================================================================
# APP VERSION & GITHUB REPOSITORY CONFIG
# ============================================================================
APP_VERSION = "2.0.0"
GITHUB_REPO = "Greatly07/yt-dlp-downloader"
SONGPULSE_REPO = "Greatly07/songpulse"
URI_SCHEME = "ytdlp"

# Resolve paths matching "%~dp0" and "%~dp0.."
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    # config.py lives in <root>/ytdlp_app/config.py, so root is one level up
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_SAVE_DIR = os.path.join(os.path.expanduser("~"), "Downloads")

YTDLP_PATH = os.path.join(APP_DIR, "yt-dlp.exe")
FFMPEG_PATH = os.path.join(APP_DIR, "ffmpeg.exe")
FFPROBE_PATH = os.path.join(APP_DIR, "ffprobe.exe")
NODE_PATH = os.path.join(APP_DIR, "node.exe")
ICON_PATH = os.path.join(APP_DIR, "yt-dlp.ico")
SETTINGS_FILE = os.path.join(APP_DIR, "yt_dlp_settings.json")
HISTORY_FILE = os.path.join(APP_DIR, "yt_dlp_history.json")
PRESETS_FILE = os.path.join(APP_DIR, "yt_dlp_presets.json")

# Official Binary Download URLs (Windows x64)
NODE_WIN64_URL = "https://nodejs.org/dist/latest-v22.x/win-x64/node.exe"
FFMPEG_WIN64_ZIP_URL = (
    "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/"
    "ffmpeg-master-latest-win64-gpl.zip"
)

PREVIEW_W = 360
PREVIEW_H = 202
PREVIEW_FPS = 15
LOG_MIN_HEIGHT = 125
LOG_MAX_HEIGHT = 210

# ============================================================================
# DEFAULT WINDOW DIMENSIONS (Change DEFAULT_WINDOW_WIDTH / HEIGHT here)
# ============================================================================
DEFAULT_WINDOW_WIDTH = 650
DEFAULT_WINDOW_HEIGHT = 720
MIN_WINDOW_WIDTH = 450
MIN_WINDOW_HEIGHT = 500

# ============================================================================
# PRESETS CONFIGURATION (3 Built-in Default Presets)
# ============================================================================
DEFAULT_PRESETS = {
    "Preset 1: Video": {
        "builtin": True,
        "badge": "Video",
        "icon": "video",
        "description": "Downloads MP4 video with best resolution available",
        "media_type": "video",
        "video_fmt": "mp4",
        "audio_fmt": "mp3",
        "quality_choice": "best",
        "audio_quality_choice": "best",
        "use_custom_res": False,
        "custom_res": "",
        "range_choice": "1",
        "playlist_folder": False,
        "playlist_numbering": False,
        "batch_as_playlist": False,
        "meta": True,
        "subs": False,
    },
    "Preset 2: Music": {
        "builtin": True,
        "badge": "Music",
        "icon": "music",
        "description": "Downloads MP3 music with best quality",
        "media_type": "audio",
        "video_fmt": "mp4",
        "audio_fmt": "mp3",
        "quality_choice": "best",
        "audio_quality_choice": "best",
        "use_custom_res": False,
        "custom_res": "",
        "range_choice": "1",
        "playlist_folder": False,
        "playlist_numbering": False,
        "batch_as_playlist": False,
        "meta": True,
        "subs": False,
    },
    "Preset 3: Playlist": {
        "builtin": True,
        "badge": "Playlist",
        "icon": "playlist",
        "description": "Add playlist/queued links to a new folder",
        "media_type": "audio",
        "video_fmt": "mp4",
        "audio_fmt": "mp3",
        "quality_choice": "best",
        "audio_quality_choice": "best",
        "use_custom_res": False,
        "custom_res": "",
        "range_choice": "1",
        "playlist_folder": True,
        "playlist_numbering": True,
        "batch_as_playlist": True,
        "meta": True,
        "subs": False,
    },
}

QUALITY_PRESETS = [
    ("Auto (Best)", "best"),
    ("2160p (4K)", "2160"),
    ("1440p (2K)", "1440"),
    ("1080p (FHD)", "1080"),
    ("720p (HD)", "720"),
    ("480p", "480"),
    ("360p", "360"),
]
QUALITY_LABEL_TO_VAL = {lbl: val for lbl, val in QUALITY_PRESETS}
QUALITY_VAL_TO_LABEL = {val: lbl for lbl, val in QUALITY_PRESETS}

AUDIO_QUALITY_PRESETS = [
    ("Auto (Best Audio)", "best"),
    ("320 kbps (Highest)", "320K"),
    ("256 kbps (High)", "256K"),
    ("192 kbps (Standard)", "192K"),
    ("128 kbps (Compact)", "128K"),
    ("64 kbps (Voice/Low)", "64K"),
]
AUDIO_QUALITY_LABEL_TO_VAL = {lbl: val for lbl, val in AUDIO_QUALITY_PRESETS}
AUDIO_QUALITY_VAL_TO_LABEL = {val: lbl for lbl, val in AUDIO_QUALITY_PRESETS}

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
    ("None (Disabled)", "none"),
    ("Firefox (Recommended)", "firefox"),
    ("Edge", "edge"),
    ("Brave", "brave"),
    ("Opera", "opera"),
    ("Vivaldi", "vivaldi"),
    ("Chrome (Requires browser closed / v126)", "chrome"),
]
COOKIE_LABEL_TO_VAL = {lbl: val for lbl, val in COOKIE_BROWSERS}
COOKIE_VAL_TO_LABEL = {val: lbl for lbl, val in COOKIE_BROWSERS}

DEPENDENCY_PREF_MODES = [
    ("Prefer System Global PATH (Fallback to App Folder)", "global"),
    ("Prefer App Folder (Bundled / Downloaded Local Files)", "local"),
]
DEP_PREF_LABEL_TO_VAL = {lbl: val for lbl, val in DEPENDENCY_PREF_MODES}
DEP_PREF_VAL_TO_LABEL = {val: lbl for lbl, val in DEPENDENCY_PREF_MODES}

THEME_MODES = [
    ("Match Windows", "system"),
    ("Dark Mode (SongPulse)", "dark"),
    ("Light Mode", "light"),
]
THEME_LABEL_TO_VAL = {lbl: val for lbl, val in THEME_MODES}
THEME_VAL_TO_LABEL = {val: lbl for lbl, val in THEME_MODES}

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
        "Original (No FFmpeg)",
        "Original Audio Stream\n\n"
        "• Saves the raw audio file (.webm or .m4a) straight from the server without converting it.\n"
        "• Works even if FFmpeg is not installed!",
    ),
]

EXTRA_HELP = {
    "presets": (
        "Download Presets\n\n"
        "• Preset 1 (Video): Downloads MP4 video with best resolution available.\n"
        "• Preset 2 (Music): Downloads MP3 music with best quality.\n"
        "• Preset 3 (Playlist): Add playlist/queued links to a new folder.\n"
        "• You can also save your current configuration as a custom preset!"
    ),
    "quality": (
        "Strict Video Resolution & Custom Scaling\n\n"
        "• Auto (Best): Downloads the highest available video quality.\n"
        "• Preset (e.g., 1080p): Forces yt-dlp to select that exact resolution stream.\n"
        "• Custom Resolution: Downloads the best stream and rescales it via FFmpeg to your exact height (e.g., 540) or dimensions (e.g., 1280x720)."
    ),
    "audio_quality": (
        "Sound Quality (Audio Stream & Bitrate)\n\n"
        "• Auto (Best Audio): Selects the highest quality source stream ('bestaudio') and VBR quality 0.\n"
        "• Specific Bitrate (e.g., 320 kbps, 192 kbps): Sets target encoding bitrate via FFmpeg when converting to MP3/M4A/Opus."
    ),
    "custom_title": (
        "Custom File Title\n\n"
        "• Leave blank to keep the video/song's original title.\n"
        "• Always resets to empty when the app starts so you don't accidentally overwrite future downloads."
    ),
    "remove_links": (
        "Remove Links from Titles\n\n"
        "• Automatically strips http:// and https:// URLs out of titles (very useful for Twitter/X, TikTok, and Instagram posts)."
    ),
    "playlist_folder": (
        "Playlist & Batch Subfolder\n\n"
        "• Creates a subfolder inside your Save Directory when downloading a YouTube playlist OR when batch-downloading multiple songs (including from SongPulse).\n"
        "• Leave the folder name box blank to use the playlist's real title (or 'Batch Playlist' for multi-link queues), or enter your own folder name."
    ),
    "playlist_numbers": (
        "Order Playlist with Numbers\n\n"
        "• Adds the track/video number in front of playlist or batch filenames (e.g., '1 - Song Title.mp3', '2 - Song Title.mp3').\n"
        "• Has no effect when downloading a single video or song."
    ),
    "meta": (
        "Cover Art & Media Info (Default: ON)\n\n"
        "• Embeds the thumbnail as the song/video cover image.\n"
        "• Writes title, artist/channel name, upload date, and description into the file tags.\n"
        "• Requires FFmpeg."
    ),
    "subtitles": (
        "Include Subtitles & Language\n\n"
        "• Downloads and embeds available subtitles (including auto-generated captions) directly into video files.\n"
        "• Pick a language preset or choose Custom and enter comma-separated language codes (e.g., en,id,ja,ko)."
    ),
    "cookies": (
        "Browser Cookies & cookies.txt (Authentication)\n\n"
        "• Why Chrome fails on Windows: Chrome v127+ introduced App-Bound Encryption and locks its cookie database while running, preventing external tools like yt-dlp from reading Chrome cookies directly.\n"
        "• Solution 1 (Recommended): Use a Netscape 'cookies.txt' file exported from Chrome/Brave/Edge using an extension like 'Get cookies.txt LOCALLY'.\n"
        "• Solution 2: Select Firefox (which works seamlessly even while open)."
    ),
    "songpulse": (
        "SongPulse Automatic Batch Integration\n\n"
        "• Registers the 'ytdlp://' protocol handler in Windows so clicking 'Download Playlist' in SongPulse launches yt-dlp Downloader and automatically downloads all tracks into a new playlist folder.\n"
        "• URI Format: ytdlp://download?playlist=My%20Playlist&urls=https://...,https://...\n"
        "• CLI Format: yt_dlp_app.exe --songpulse --playlist \"My Playlist\" --urls <url1> <url2> ..."
    ),
}
