import os
import re
import threading
import subprocess
from datetime import datetime
from tkinter import messagebox
from .config import (
    APP_DIR,
    QUALITY_LABEL_TO_VAL,
    AUDIO_QUALITY_LABEL_TO_VAL,
    SUB_LABEL_TO_VAL,
    COOKIE_LABEL_TO_VAL,
)
from .utils import sanitize_filename, sanitize_folder_name, json_unquote


YT_ERROR_ID_RE = re.compile(r"ERROR:\s*\[youtube[^\]]*\]\s*([A-Za-z0-9_-]{11}):\s*(.+)")


class DownloaderMixin:
    """Mixin for YtDlpApp handling command generation, batch playlist folders, and failed download tracking."""

    def get_cookie_args(self):
        args = []
        # 1. Netscape cookies.txt file (Best for Chrome v127+ App-Bound Encryption bypass)
        if self.use_cookie_file_var.get():
            cfile = self.cookie_file_path_var.get().strip()
            if cfile and os.path.isfile(cfile):
                args += ["--cookies", cfile]
                return args

        # 2. Browser Cookies
        browser = COOKIE_LABEL_TO_VAL.get(self.cookie_browser_label_var.get(), "none")
        if browser and browser != "none":
            args += ["--cookies-from-browser", browser]
        return args

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

    def build_command(self, url, batch_index=None, is_batch_playlist=False, target_subfolder=None):
        """
        Builds the yt-dlp CLI command for a single URL or playlist URL.
        If is_batch_playlist is True, files are placed in target_subfolder (or directly in save_dir if already resolved)
        and numbered with batch_index if playlist_numbering_var is enabled.
        """
        ffmpeg_exe = self.get_ffmpeg_exe()
        has_ffmpeg = bool(ffmpeg_exe)

        cmd = [
            self.get_ytdlp_exe(),
            "--progress",
            "--no-quiet",
            "--no-simulate",
            "--ignore-errors",
            "--print",
            "before_dl:__ITEM__\t%(fulltitle,title)j\t%(webpage_url)j",
            "--print",
            "after_move:__HIST__\t%(fulltitle,title)j\t%(webpage_url)j\t%(artist,uploader,channel,creator|Unknown)j\t%(filepath)j",
        ]

        cmd += self.get_cookie_args()

        if has_ffmpeg:
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
        audio_qual_val = AUDIO_QUALITY_LABEL_TO_VAL.get(self.audio_quality_label_var.get(), "best")

        if is_video:
            vfmt = self.video_fmt.get()
            use_custom_res = self.use_custom_res_var.get() and has_ffmpeg
            custom_scale = self._parse_custom_res_filter(self.custom_res_var.get()) if use_custom_res else None
            qual_val = QUALITY_LABEL_TO_VAL.get(self.quality_label_var.get(), "best")

            if not has_ffmpeg:
                # Without FFmpeg, yt-dlp cannot merge separate video+audio streams; select best pre-merged stream
                if qual_val == "best":
                    cmd += ["-f", f"best[ext={vfmt}]/best"]
                else:
                    cmd += ["-f", f"best[height<={qual_val}][ext={vfmt}]/best[height<={qual_val}]/best"]
            elif use_custom_res and custom_scale:
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

            if self.subs_var.get() and has_ffmpeg:
                sub_val = SUB_LABEL_TO_VAL.get(self.sub_lang_label_var.get(), "en.*,en")
                if sub_val == "custom":
                    sub_langs = self.custom_sub_lang_var.get().strip() or "en.*,en"
                else:
                    sub_langs = sub_val
                cmd += ["--write-subs", "--write-auto-subs", "--sub-langs", sub_langs, "--embed-subs"]
        else:
            afmt = self.audio_fmt.get()
            if afmt == "orig" or not has_ffmpeg:
                cmd += ["-f", "bestaudio/best"]
            else:
                cmd += ["-f", "bestaudio/best", "-x", "--audio-format", afmt]
                if audio_qual_val == "best":
                    cmd += ["--audio-quality", "0"]
                else:
                    cmd += ["--audio-quality", audio_qual_val]

        # Scope Arguments
        scope = self.range_choice.get()
        if scope == "2" and has_ffmpeg:
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

        # Output Template & Playlist Folder Handling
        folder_part = ""
        if target_subfolder:
            # We are already running inside or targeting a specific batch/custom playlist subfolder
            folder_part = ""
        elif self.playlist_folder_var.get():
            custom_pl = sanitize_filename(self.custom_playlist_folder_var.get())
            if custom_pl:
                folder_part = f"./%(playlist_title&{custom_pl}|{custom_pl})s/"
            else:
                folder_part = "./%(playlist_title&{}|)s/"

        if self.playlist_numbering_var.get():
            if is_batch_playlist and batch_index is not None:
                # If the item is part of a batch queue, use playlist_index if it's a playlist or batch_index if single song
                num_part = f"%(playlist_index&{{}} - |{batch_index} - )s"
            else:
                num_part = "%(playlist_index&{} - |)s"
        else:
            num_part = ""

        custom_title = sanitize_filename(self.custom_title_var.get())
        if custom_title and not is_batch_playlist:
            suffix = "" if self.playlist_numbering_var.get() else "%(playlist_index& ({})|)s"
            title_part = f"{custom_title}{suffix}"
        else:
            title_part = "%(title)s"

        out_tmpl = f"{folder_part}{num_part}{title_part}.%(ext)s"
        cmd += ["-o", out_tmpl]

        if self.meta_var.get() and has_ffmpeg:
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

    def start_download(self, override_urls=None, is_retry=False):
        if override_urls is not None:
            urls = list(override_urls)
        else:
            entry_raw = self.url_var.get().strip()
            entry_links = [ln.strip().replace('"', "") for ln in entry_raw.splitlines() if ln.strip()]

            urls = list(self.download_queue)
            for ln in entry_links:
                if ln not in urls:
                    urls.append(ln)

        if not urls:
            messagebox.showwarning("Missing Link", "Paste a link or add links to the queue first.")
            return

        if self.media_type.get() == "video" and self.use_custom_res_var.get() and self.get_ffmpeg_exe():
            if not self._parse_custom_res_filter(self.custom_res_var.get()):
                messagebox.showwarning(
                    "Invalid Custom Resolution",
                    "Enter a valid height (e.g., 540 or 720) or dimensions (e.g., 1280x720).",
                )
                return

        self.close_preview()
        self.save_settings()
        base_save_dir = self.save_dir_var.get()
        os.makedirs(base_save_dir, exist_ok=True)

        # Determine if we should create a dedicated playlist subfolder inside base_save_dir
        is_batch = len(urls) > 1
        custom_folder_raw = sanitize_folder_name(self.custom_playlist_folder_var.get())
        create_batch_subfolder = False
        target_save_dir = base_save_dir

        if self.playlist_folder_var.get():
            if custom_folder_raw:
                create_batch_subfolder = True
                target_save_dir = os.path.join(base_save_dir, custom_folder_raw)
            elif is_batch and self.batch_as_playlist_var.get():
                create_batch_subfolder = True
                auto_name = f"Batch Playlist ({datetime.now().strftime('%Y-%m-%d %H-%M')})"
                target_save_dir = os.path.join(base_save_dir, auto_name)

        os.makedirs(target_save_dir, exist_ok=True)

        self.is_downloading = True
        self.cancel_requested = False
        if not is_retry:
            # Clear previous failed items at the start of a fresh download session
            self.failed_downloads.clear()
            self.refresh_failed_ui()

        self.dl_btn.config(
            text="Stop / Cancel" if len(urls) == 1 else f"Stop / Cancel (1/{len(urls)})",
            bg="#dc2626",
            activebackground="#b91c1c",
            state="normal",
        )
        self.log_text.delete("1.0", "end")
        self._pending_cr = False

        if not self.get_node_exe() or not self.get_ffmpeg_exe():
            missing = []
            if not self.get_ffmpeg_exe():
                missing.append("FFmpeg")
            if not self.get_node_exe():
                missing.append("Node.js")
            self.log_raw(
                f"⚠ Note: {', '.join(missing)} not detected. Some features are disabled and "
                "YouTube downloads have a higher chance of being blocked.\n"
                "You can install them anytime in Settings & Updates.\n\n"
            )

        threading.Thread(
            target=self._run_queue_worker,
            args=(urls, target_save_dir, is_batch, create_batch_subfolder),
            daemon=True,
        ).start()

    def _run_queue_worker(self, urls, save_dir, is_batch, has_dedicated_subfolder):
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
                    self.after(0, self.log_raw, f"\n>>> Track / Item {idx}/{total}: {url}\n")

                cmd = self.build_command(
                    url,
                    batch_index=idx if is_batch else None,
                    is_batch_playlist=is_batch,
                    target_subfolder=save_dir if has_dedicated_subfolder else None,
                )
                self.after(
                    0,
                    self.log_raw,
                    f"Saving to: {save_dir}\nRunning: {' '.join(cmd)}\n" + "=" * 56 + "\n",
                )

                ok = self._run_single_process(cmd, save_dir, url)
                if ok and not self.cancel_requested:
                    self.after(0, self._remove_url_from_queue, url)
                    self.after(0, self._remove_url_from_failed, url)

            if self.cancel_requested:
                self.after(
                    0,
                    self.log_raw,
                    "\n========================================================\nDownload cancelled by user.\n",
                )
            else:
                def _on_all_done():
                    fail_cnt = len(self.failed_downloads)
                    if fail_cnt > 0:
                        self.log_raw(
                            f"\n========================================================\n"
                            f"Finished with {fail_cnt} failed song(s)/video(s). "
                            f"Click 'Retry Failed Downloads' above to try redownloading them.\n"
                        )
                    else:
                        self.log_raw(
                            "\n========================================================\n"
                            "All downloads complete!\n"
                        )
                self.after(0, _on_all_done)
        finally:
            self.after(0, self._finish_download_ui)

    def _remove_url_from_queue(self, url):
        if url in self.download_queue:
            self.download_queue.remove(url)
            self.refresh_queue_ui()

    def _remove_url_from_failed(self, url):
        before = len(self.failed_downloads)
        self.failed_downloads = [item for item in self.failed_downloads if item.get("url") != url]
        if len(self.failed_downloads) != before:
            self.refresh_failed_ui()

    def record_failed_download(self, url, title="", reason=""):
        url = (url or "").strip()
        if not url:
            return
        for existing in self.failed_downloads:
            if existing.get("url") == url:
                if title and existing.get("title") == url:
                    existing["title"] = title
                if reason:
                    existing["reason"] = reason
                self.refresh_failed_ui()
                return
        self.failed_downloads.append(
            {
                "url": url,
                "title": (title or url).strip(),
                "reason": (reason or "Download failed").strip(),
            }
        )
        self.refresh_failed_ui()

    def retry_all_failed_downloads(self):
        if self.is_downloading or not self.failed_downloads:
            return
        retry_urls = [item["url"] for item in self.failed_downloads if item.get("url")]
        if not retry_urls:
            return
        self.start_download(override_urls=retry_urls, is_retry=True)

    def retry_selected_failed_downloads(self):
        if self.is_downloading or not self.failed_downloads:
            return
        sel = list(self.failed_listbox.curselection())
        if not sel:
            self.retry_all_failed_downloads()
            return
        retry_urls = [
            self.failed_downloads[idx]["url"]
            for idx in sel
            if 0 <= idx < len(self.failed_downloads)
        ]
        if retry_urls:
            self.start_download(override_urls=retry_urls, is_retry=True)

    def clear_failed_downloads(self):
        self.failed_downloads.clear()
        self.refresh_failed_ui()

    def _run_single_process(self, cmd, save_dir, root_url):
        stream_buf = ""
        current_item_title = ""
        current_item_url = root_url
        succeeded_count = 0
        item_errors = []

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
                text = stream_buf + chunk.decode("utf-8", errors="replace").replace("\r\n", "\n")
                stream_buf = ""

                # Process complete lines or trailing partial markers
                out_parts = []
                idx = 0
                while idx < len(text):
                    # Find earliest special marker (__HIST__ or __ITEM__)
                    h_pos = text.find("__HIST__\t", idx)
                    i_pos = text.find("__ITEM__\t", idx)
                    candidates = [p for p in (h_pos, i_pos) if p != -1]
                    marker_pos = min(candidates) if candidates else -1

                    if marker_pos == -1:
                        tail = text[idx:]
                        for marker_prefix in ("__HIST__\t", "__ITEM__\t"):
                            for prefix_len in range(min(8, len(tail)), 0, -1):
                                if marker_prefix.startswith(tail[-prefix_len:]):
                                    stream_buf = tail[-prefix_len:]
                                    tail = tail[:-prefix_len]
                                    break
                            if stream_buf:
                                break
                        out_parts.append(tail)
                        break

                    out_parts.append(text[idx:marker_pos])
                    nl_pos = text.find("\n", marker_pos)
                    if nl_pos == -1:
                        stream_buf = text[marker_pos:]
                        break

                    marker_line = text[marker_pos:nl_pos]
                    parts = marker_line.split("\t")
                    if parts[0] == "__ITEM__" and len(parts) >= 3:
                        current_item_title = json_unquote(parts[1]) or current_item_title
                        current_item_url = json_unquote(parts[2]) or root_url
                    elif parts[0] == "__HIST__" and len(parts) >= 4:
                        h_title = json_unquote(parts[1])
                        h_url = json_unquote(parts[2])
                        h_author = json_unquote(parts[3])
                        h_fpath = json_unquote(parts[4]) if len(parts) >= 5 else ""
                        succeeded_count += 1
                        self.after(0, self.record_history_entry, h_title, h_url, h_author, h_fpath)
                    idx = nl_pos + 1

                visible_text = "".join(out_parts)
                if visible_text:
                    # Inspect visible text for yt-dlp ERROR: lines to detect failed songs automatically
                    for line in visible_text.splitlines():
                        if "ERROR:" in line:
                            err_clean = line.strip()
                            item_errors.append(err_clean)
                            m = YT_ERROR_ID_RE.search(err_clean)
                            if m:
                                vid_id, err_reason = m.group(1), m.group(2)
                                fail_url = f"https://www.youtube.com/watch?v={vid_id}"
                                fail_title = (
                                    current_item_title
                                    if (current_item_url and vid_id in current_item_url and current_item_title)
                                    else f"YouTube Track ({vid_id})"
                                )
                                self.after(0, self.record_failed_download, fail_url, fail_title, err_reason)
                            elif current_item_url:
                                reason_short = err_clean.split("ERROR:", 1)[-1].strip()
                                self.after(
                                    0,
                                    self.record_failed_download,
                                    current_item_url,
                                    current_item_title or current_item_url,
                                    reason_short,
                                )
                    self.after(0, self.log_raw, visible_text)

            if stream_buf and not stream_buf.startswith(("__HIST__\t", "__ITEM__\t")):
                self.after(0, self.log_raw, stream_buf)

            proc.wait()
            if not self.cancel_requested:
                if proc.returncode != 0 or (succeeded_count == 0 and item_errors):
                    reason = item_errors[-1] if item_errors else f"Process exited with code {proc.returncode}"
                    self.after(
                        0,
                        self.record_failed_download,
                        current_item_url or root_url,
                        current_item_title or root_url,
                        reason,
                    )
                    if proc.returncode != 0:
                        self.after(0, self.log_raw, f"\nProcess exited with code {proc.returncode}\n")
                    return False
                if item_errors:
                    # Playlist partially succeeded, but some songs failed
                    return False
            return True
        except FileNotFoundError:
            self.after(0, self.log_raw, f"\nError: Could not find yt-dlp.exe in {APP_DIR}\n")
            self.after(0, self.record_failed_download, root_url, root_url, "yt-dlp.exe not found")
            return False
        except Exception as e:
            if not self.cancel_requested:
                self.after(0, self.log_raw, f"\nError: {e}\n")
                self.after(0, self.record_failed_download, root_url, root_url, str(e))
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
