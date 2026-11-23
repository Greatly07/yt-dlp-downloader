import os
import json
import threading
import subprocess
import urllib.request
import tkinter as tk
from tkinter import messagebox
from .config import PREVIEW_W, PREVIEW_H, PREVIEW_FPS
from .utils import format_seconds


class PreviewMixin:
    """Mixin for YtDlpApp providing video & audio stream preview and single-frame scrubbing."""

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

    def start_preview(self):
        if not self.get_ffmpeg_exe():
            messagebox.showwarning(
                "FFmpeg Required",
                "FFmpeg is required for media preview playback.\n\n"
                "Go to the 'Settings & Updates' tab to download FFmpeg.",
            )
            return

        url = self.url_var.get().strip().replace('"', "")
        if not url:
            messagebox.showwarning("Missing Link", "Paste a link first before clicking Preview.")
            return

        self.stop_preview_streams()
        self.preview_session_id += 1
        session_id = self.preview_session_id

        self.preview_box.pack(fill="x", padx=10, pady=(4, 8))
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
        if ("could not copy" in low and "cookie" in low) or "dpapi" in low or "app-bound" in low:
            return (
                "Chrome/Chromium locked or encrypted its cookie database (App-Bound Encryption). "
                "Open 'Settings & Updates' -> 'Browser Cookies' and use a cookies.txt file or Firefox."
            )
        if any(k in low for k in ("sign in", "login", "cookies", "confirm your age", "age-restricted", "not a bot")):
            return (
                "This media requires authentication or a bot check. "
                "Configure Browser Cookies or a cookies.txt file in the 'Settings & Updates' tab."
            )
        if "403" in low or "forbidden" in low:
            return "Access forbidden (HTTP 403). Ensure Node.js is installed in Settings or configure Cookies."
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
                f"Playlist link detected ({count} items).\n"
                "Preview playback is skipped for playlists, but you can download all or selected items below.",
                session_id,
            )
            return

        ffmpeg_exe = self.get_ffmpeg_exe()
        if not ffmpeg_exe:
            self._show_preview_message(
                "Preview Unavailable",
                "ffmpeg.exe is required for preview playback. Download it in the Settings tab.",
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
            self.video_canvas_lbl.config(
                image="", text="Buffering video...", fg="#a1a1aa", width=PREVIEW_W, height=PREVIEW_H
            )
            self.preview_player_frame.pack(fill="x")
        else:
            self.preview_mode_badge.config(text="Audio Only")
            self.video_canvas_lbl.config(
                image="", text="Loading album cover...", fg="#a1a1aa", width=PREVIEW_W, height=PREVIEW_H
            )
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
        self.preview_btn.config(state="normal" if self.get_ffmpeg_exe() else "disabled")
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
        self.preview_btn.config(state="normal" if self.get_ffmpeg_exe() else "disabled")
