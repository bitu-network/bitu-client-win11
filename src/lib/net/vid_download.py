# file: src/lib/net/vid_download.py

import os
import sys
import json
import base64
from pathlib import Path

from lib.f.url_utils import remove_url_params_if_has_params
from lib.fs.rename import append_prefix_tag

import yt_dlp

from lib.file_types.video_and_audio import (
    get_duration_seconds,
    get_duration_tag,
)


def extract_url_from_url_file(url_file_path: Path) -> str | None:
    """
    Extract URL from a Windows .url file.
    """
    if not url_file_path.exists():
        return None

    with open(url_file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
        for line in f:
            if line.strip().lower().startswith("url="):
                return line.strip()[4:]

    return None


def download_urls(urls: list[str], outdir: Path) -> bool:
    """
    Download URLs serially using the yt-dlp Python library.

    After yt-dlp finishes downloading and post-processing each file,
    applies local video processing.
    """

    if not urls:
        return True

    final_video_path = None

    def yt_dlp_postprocessor_hook(data):
        nonlocal final_video_path

        if data["status"] == "finished":
            final_video_path = Path(data["info_dict"]["filepath"])

    options = {
        "outtmpl": str(
            outdir / "[%(upload_date>%Y.%m.%d)s~] %(title)s [%(id)s].%(ext)s"
        ),
        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "postprocessor_hooks": [
            yt_dlp_postprocessor_hook,
        ],
    }

    for url in urls:
        url = url.strip()

        if not url:
            continue

        try:
            with yt_dlp.YoutubeDL(options) as ydl:  # type: ignore[arg-type]
                info = ydl.extract_info(
                    url,
                    download=True,
                )

                video_path = final_video_path

            if video_path and video_path.exists():
                apply_video_tags(video_path)
            else:
                print(
                    f"Downloaded file not found: {video_path}",
                    flush=True,
                )
                return False

        except Exception as e:
            print(f"Download failed: {url}")
            print(e)
            return False

    return True


def download_url_files(url_files: list[Path], outdir: Path) -> bool:
    """
    Download videos referenced by .url files.
    """

    url_map = {}

    for file_path in url_files:
        url = extract_url_from_url_file(file_path)

        print(f"EXTRACTED URL: {url!r}")

        if url:
            clean_url = remove_url_params_if_has_params(
                url,
                "list",
                "v",
            )

            url_map[clean_url] = file_path.resolve()

    if not url_map:
        return True

    urls = list(url_map.keys())

    success = download_urls(urls, outdir)
    if success is False:
        return False

    for _, url_path in url_map.items():
        try:
            url_path.unlink()
        except Exception:
            pass

    return True


def apply_video_tags(video_path: Path) -> Path:

    duration_seconds = get_duration_seconds(video_path)

    duration_tag = get_duration_tag(duration_seconds)

    video_path = append_prefix_tag(video_path, duration_tag)

    return video_path


if __name__ == "__main__":
    if os.name == "nt":
        import ctypes

        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.SetForegroundWindow(hwnd)
    b64_str = os.environ.get("BITU_URL_FILES_B64", "")
    if b64_str:
        paths = [Path(p) for p in json.loads(base64.b64decode(b64_str).decode("utf-8"))]
        has_errors = False
        for f in paths:
            print(f"  -> downloading url: {f}")
            try:
                if download_url_files([f], f.parent) is False:
                    has_errors = True
            except Exception as e:
                print(f"[ERROR] Failed to download {f.name}: {e}")
                has_errors = True

        if has_errors:
            print("\n[!] Completed with errors.")
            if os.name == "nt":
                input("Press Enter to close...")
            sys.exit(1)
        else:
            sys.exit(0)
