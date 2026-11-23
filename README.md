# yt-dlp-downloader v2.0.0

**[Download Latest Installer (Windows Setup)](https://github.com/Greatly07/yt-dlp-downloader/releases/latest/download/yt-dlp_Downloader_Setup.exe)**

**yt-dlp Downloader** is a lightweight Windows desktop app that makes downloading videos, music, clips, and playlists simpler—no command line required.

<img width="480" alt="yt-dlp Downloader" src="https://github.com/user-attachments/assets/ce542a66-d2e5-44fb-aaed-7cf33bc110b5" />

## What's New in v2.0.0

- **Quick Presets & Custom Preset Saving:**
  - **Preset 1 (Video):** MP4, Auto (Best) resolution, full video, cover art & metadata included.
  - **Preset 2 (Music):** MP3, best audio quality, full song, cover art & metadata included.
  - **Preset 3 (Playlist):** MP3, best audio quality, full playlist, creates a new folder with the playlist name and numbered tracks (`1 - Title`), cover art & metadata included.
  - Save and manage your own custom presets.
- **SongPulse Automatic Batch Integration (`ytdlp://`):**
  - One-click batch playlist downloads straight from [SongPulse](https://github.com/Greatly07/songpulse) via the `ytdlp://` custom URI protocol or CLI flags (`--songpulse --playlist "My Playlist" --urls ...`).
  - Automatically groups batch-downloaded songs into a new playlist subfolder inside your chosen Save Directory.
- **Failed Song Detection & One-Click Retry:** Detects failed songs in playlists or batch queues and lets you retry all or selected items in one click. You can also re-queue entries from History.
- **Sound Quality Selector:** Choose `Auto (Best Audio)` or a target bitrate (`320`, `256`, `192`, `128`, or `64 kbps`).
- **On-Demand FFmpeg & Node.js Dependency Manager:**
  - Optional FFmpeg & Node.js installation in Setup. If skipped, dependent features are disabled with a warning.
  - Choose the preferred dependency source (`System Global PATH` or `App Folder`), download or redownload FFmpeg & Node.js in Settings, or clean up local copies.
- **Improved Browser Cookies & `cookies.txt` Support:** Dedicated cookie settings with `cookies.txt` support to bypass Chrome v127+ App-Bound Encryption on Windows.
- **Redesigned Interface & Modular Codebase:** New rounded modern widgets, top navigation, and an About tab. The code is split into the `ytdlp_app` package for easier maintenance.

## Features
- **Multiple Formats:** Video (`MP4`, `MKV`, `WebM`, `MOV`) and Audio (`MP3`, `M4A`, `WAV`, `FLAC`, `Opus`, or Original).
- **Built-in Media Preview:** Preview video with audio, controllable volume, album cover art for audio-only links, pause-on-seek scrubbing, and **Set Clip Start / End** buttons.
- **Quality & Custom Resolution:** Auto (Best) up to 4K, strict resolution presets, or custom resolution scaling (e.g., `540` or `1280x720`).
- **Batch Queue & Cancel:** Queue multiple links at once and stop/cancel active downloads anytime.
- **Smart Playlist Controls:** Pick specific playlist ranges, auto-number tracks (`1 - Title`), and organize playlists into their own folder (automatically skipped for single files).
- **Subtitles, Metadata & Clean Titles:** Embed cover art, tags, and subtitles (multiple language presets or custom), set custom titles, or strip URLs from titles.
- **Browser Cookies:** Supports Firefox, Chrome, Edge, Brave, Opera, and Vivaldi sessions, plus `cookies.txt`, for login-walled or age-restricted links.
- **Download History:** View past downloads with clickable links and right-click to open the downloaded file in File Explorer.
- **One-Click Updates:** Update both the app (from GitHub) and `yt-dlp` directly from the **Settings & Updates** tab, with automatic Windows light/dark theme syncing.

<img width="480" alt="Advanced Options" src="https://github.com/user-attachments/assets/2f81e872-0d7a-4885-99b1-b8d1f6595fa0" />

## How It Works

### 1. Downloader Tab
<img width="480" alt="Downloader Tab" src="https://github.com/user-attachments/assets/240e9db3-0277-4604-9e69-f22e2d323094" />

1. **Paste & Preview:** Click **Paste** to insert a video, audio, or playlist link—or use **+ Queue** (or paste multiple links at once) to batch download. Click **Preview** to play the stream with audio, scrub to a timestamp, and optionally mark **Set Clip Start** / **Set Clip End**.
2. **Choose Type, Format & Quality:** Pick **Video** (`MP4`, `MKV`, `WebM`, `MOV`) or **Audio Only** (`MP3`, `M4A`, `WAV`, `FLAC`, `Opus`, or `Original`). Hover or click any **`(?)`** badge for format details. For videos, select a resolution from the dropdown or enable **Custom Resolution** to scale with FFmpeg. For audio, pick a sound quality or bitrate.
3. **Select Scope & Naming:** Download the full video/playlist, cut a specific time clip, or pick a playlist index range. You can also set a one-time **Custom Title**, strip URLs from titles, auto-number playlist files, and automatically organize playlists into subfolders.
4. **Extras, Cookies & Download:** Toggle cover art/media tags, embedded subtitles (with language selection), or **Browser Cookies** for restricted links. Pick your save folder and click **Download** (which turns into **Stop / Cancel** while running) while watching live output in the **Progress Log**. All preferences are saved automatically for next time.
5. **Quick Presets:** Apply the built-in Video, Music, or Playlist preset in one click, or save your current options as your own preset.

### 2. History Tab
<img width="480" alt="History Tab" src="https://github.com/user-attachments/assets/923acdaf-160d-4fd5-8fb3-cb6ba3430bf7" />

Every completed download (including individual tracks from playlists) is automatically recorded with its **Date & Time**, **Original Title**, **Link**, and **Author / Creator / Artist**.
- **Click any link** (or click **Open in Browser**) to reopen the source page in your default browser.
- **Right-click any row** (or click **Open File Location**) to jump straight to the downloaded file highlighted in Windows File Explorer, copy the link, re-queue it, or remove an entry.
- Click **Clear History** to wipe the log whenever you want.

### 3. Settings & Updates Tab
<img width="480" alt="Settings & Updates Tab" src="https://github.com/user-attachments/assets/8b580c01-f338-408d-a1b3-79787c322c72" />

- **Appearance & Reset:** Syncs automatically with your Windows Light/Dark theme, or lets you force **Always Dark Mode** / **Always Light Mode**. Click **Reset All Settings / Options to Default** to restore factory options without erasing your Download History.
- **App Updates:** Shows your current app version and checks this GitHub repository's latest release when you click **Check & Update App from GitHub**, downloading and restarting automatically if a newer version is available.
- **yt-dlp Engine & Dependencies:** Displays your installed `yt-dlp` version, updates it in place via **Update yt-dlp Now**, and shows where `yt-dlp.exe`, `ffmpeg.exe`, `ffprobe.exe`, and `node.exe` are loaded from. Choose whether to prefer your PC's global `PATH` installations or the App Folder copies, download or redownload FFmpeg & Node.js on demand, and clean up local copies.
- **SongPulse Integration:** Register or check the `ytdlp://` protocol for automatic playlist batch downloads from SongPulse.

## Built With
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [FFmpeg](https://ffmpeg.org/)
- [Node.js](https://nodejs.org/)
