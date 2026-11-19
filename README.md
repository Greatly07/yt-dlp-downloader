# yt-dlp-downloader

**[Download Latest Installer (Windows Setup)](https://github.com/Greatly07/yt-dlp-downloader/releases/latest/download/yt-dlp_Downloader_Setup.exe)**

**yt-dlp Downloader** is a lightweight Windows desktop app that makes downloading videos, music, clips, and playlists simpler—no command line required.

<img width="480" alt="Menu Screenshot" src="https://github.com/user-attachments/assets/57d22f43-5569-4b9d-a813-69dfe7322ad8" />

## Features
- **Multiple Formats:** Video (`MP4`, `MKV`, `WebM`, `MOV`) and Audio (`MP3`, `M4A`, `WAV`, `FLAC`, `Opus`, or Original).
- **Built-in Media Preview:** Preview video with audio, controllable volume, album cover art for audio-only links, pause-on-seek scrubbing, and **Set Clip Start / End** buttons.
- **Quality & Custom Resolution:** Auto (Best) up to 4K, strict resolution presets, or custom resolution scaling (e.g., `540` or `1280x720`).
- **Batch Queue & Cancel:** Queue multiple links at once and stop/cancel active downloads anytime.
- **Smart Playlist Controls:** Pick specific playlist ranges, auto-number tracks (`1 - Title`), and organize playlists into their own folder (automatically skipped for single files).
- **Subtitles, Metadata & Clean Titles:** Embed cover art, tags, and subtitles (multiple language presets or custom), set custom titles, or strip URLs from titles.
- **Browser Cookies:** Supports Firefox, Chrome, Edge, Brave, Opera, and Vivaldi sessions for login-walled or age-restricted links.
- **Download History:** View past downloads with clickable links and right-click to open the downloaded file in File Explorer.
- **One-Click Updates:** Update both the app (from GitHub) and `yt-dlp` directly from the **Settings & Updates** tab, with automatic Windows light/dark theme syncing.

## How It Works

### 1. Downloader Tab
<img width="480" alt="Downloader Tab" src="https://github.com/user-attachments/assets/eb0e4c27-8f33-43e3-8dc3-a7603f32bd00" />

1. **Paste & Preview:** Click **Paste** to insert a video, audio, or playlist link—or use **+ Queue** (or paste multiple links at once) to batch download. Click **Preview** to play the stream with audio, scrub to a timestamp, and optionally mark **Set Clip Start** / **Set Clip End**.
2. **Choose Type, Format & Quality:** Pick **Video** (`MP4`, `MKV`, `WebM`, `MOV`) or **Audio Only** (`MP3`, `M4A`, `WAV`, `FLAC`, `Opus`, or `Original`). Hover or click any **`(?)`** badge for format details. For videos, select a resolution from the dropdown or enable **Custom Resolution** to scale with FFmpeg.
3. **Select Scope & Naming:** Download the full video/playlist, cut a specific time clip, or pick a playlist index range. You can also set a one-time **Custom Title**, strip URLs from titles, auto-number playlist files, and automatically organize playlists into subfolders.
4. **Extras, Cookies & Download:** Toggle cover art/media tags, embedded subtitles (with language selection), or **Browser Cookies** for restricted links. Pick your save folder and click **Download** (which turns into **Stop / Cancel** while running) while watching live output in the **Progress Log**. All preferences are saved automatically for next time.

### 2. History Tab
<img width="480" alt="History Tab" src="https://github.com/user-attachments/assets/ca0b4aac-9df1-452c-85e7-edfb070cb663" />

Every completed download (including individual tracks from playlists) is automatically recorded with its **Date & Time**, **Original Title**, **Link**, and **Author / Creator / Artist**.
- **Click any link** (or click **Open in Browser**) to reopen the source page in your default browser.
- **Right-click any row** (or click **Open File Location**) to jump straight to the downloaded file highlighted in Windows File Explorer, copy the link, or remove an entry.
- Click **Clear History** to wipe the log whenever you want.

### 3. Settings & Updates Tab
<img width="480" alt="Settings & Updates Tab" src="https://github.com/user-attachments/assets/9c234621-9eab-4c50-9cdc-9d8ac5b00323" />

- **Appearance & Reset:** Syncs automatically with your Windows Light/Dark theme, or lets you force **Always Dark Mode** / **Always Light Mode**. Click **Reset All Settings / Options to Default** to restore factory options without erasing your Download History.
- **App Updates:** Shows your current app version and checks this GitHub repository's latest release when you click **Check & Update App from GitHub**, downloading and restarting automatically if a newer version is available.
- **yt-dlp Engine & Dependencies:** Displays your installed `yt-dlp` version, updates it in place via **Update yt-dlp Now**, and checks where `yt-dlp.exe`, `ffmpeg.exe`, `ffprobe.exe`, and `node.exe` are loaded from—automatically preferring your PC's global `PATH` installations if present and falling back to the bundled copies if not.

## Built With
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [FFmpeg](https://ffmpeg.org/)
- [Node.js](https://nodejs.org/)
