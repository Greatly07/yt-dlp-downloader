"""
yt-dlp Media Downloader v2.0.0 — Main Entry Point
Supports direct GUI launch, CLI batch arguments, and SongPulse 'ytdlp://' protocol links.
"""
import sys
from ytdlp_app.app import YtDlpApp
from ytdlp_app.dependencies import parse_launch_arguments


def main():
    startup_job = parse_launch_arguments(sys.argv[1:])
    app = YtDlpApp(startup_job=startup_job)
    app.mainloop()


if __name__ == "__main__":
    main()
