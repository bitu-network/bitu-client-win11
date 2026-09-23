# file: src/hotkeys/i_ctrl_alt.py

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, cast
from urllib.parse import quote

from bs4 import BeautifulSoup
import requests
import yt_dlp
from yt_dlp.utils import DownloadError

from lib.hotkey_context import get_context_fields  # type: ignore[import-not-found]

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        cast(Any, stream).reconfigure(encoding="utf-8", errors="replace")

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
BRACKET_ID_REGEX = re.compile(r"\[([a-zA-Z0-9_-]{11})\]")
FALLBACK_ID_REGEX = re.compile(r"([a-zA-Z0-9_-]{11})")
BRACKET_TAGS_REGEX = re.compile(r"\[.*?\]")


def parse_iso8601_duration(duration_str: str) -> int:
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_str)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def extract_video_id(text: str) -> str | None:
    match = BRACKET_ID_REGEX.search(text)
    if match:
        return match.group(1)
    match = FALLBACK_ID_REGEX.search(text)
    return match.group(1) if match else None


def clean_filename_title(name: str) -> str:
    stem = Path(name).stem
    cleaned = BRACKET_TAGS_REGEX.sub("", stem)
    return re.sub(r"\s+", " ", cleaned).strip()


def extract_url_from_shortcut(url_file: Path) -> str | None:
    try:
        text = url_file.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            if line.startswith("URL="):
                return line[4:].strip()
    except OSError:
        pass
    return None


def get_yt_api_metadata(video_id: str) -> tuple[str | None, str | None, int | None]:
    if not YOUTUBE_API_KEY:
        return None, None, None
    url = f"https://www.googleapis.com/youtube/v3/videos?id={video_id}&part=snippet,contentDetails&key={YOUTUBE_API_KEY}"
    try:
        resp = requests.get(url, timeout=5).json()
        items = resp.get("items", [])
        if not items:
            return None, None, None
        snippet = items[0]["snippet"]
        published_at = snippet.get("publishedAt", "")[:10].replace("-", ".")
        duration_iso = items[0]["contentDetails"].get("duration", "")
        seconds = parse_iso8601_duration(duration_iso)
        duration_str = f"{round(seconds / 60):03d}"
        return published_at, duration_str, seconds
    except (requests.RequestException, ValueError, KeyError):
        return None, None, None


def search_yt_by_title(title: str, target_seconds: int | None = None) -> tuple[str | None, str | None, str | None]:
    if not YOUTUBE_API_KEY or not title:
        return None, None, None
    search_url = f"https://www.googleapis.com/youtube/v3/search?q={quote(title)}&type=video&part=snippet&maxResults=3&key={YOUTUBE_API_KEY}"
    try:
        resp = requests.get(search_url, timeout=5).json()
        for item in resp.get("items", []):
            v_id = item["id"]["videoId"]
            pub_date, dur_str, sec = get_yt_api_metadata(v_id)
            if target_seconds is not None and sec is not None:
                if abs(sec - target_seconds) <= 5:
                    return v_id, pub_date, dur_str
            elif pub_date:
                return v_id, pub_date, dur_str
    except (requests.RequestException, ValueError, KeyError):
        pass
    return None, None, None


def extract_html_datetime(url: str) -> str | None:
    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(response.text, "html.parser")

        for script in soup.find_all("script", type="application/ld+json"):
            text = script.get_text()
            match = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})', text)
            if match:
                return match.group(1).replace("-", ".")

        candidates = []
        candidates += soup.find_all("meta", attrs={"property": "article:published_time"})
        for name in ["date", "pubdate", "publish_date", "published_time", "datePublished"]:
            candidates += soup.find_all("meta", attrs={"name": name})

        for tag in candidates:
            value = tag.get("content")
            if value:
                match = re.search(r"\d{4}[-.]\d{2}[-.]\d{2}", value)
                if match:
                    return match.group().replace("-", ".")
    except requests.RequestException:
        pass
    return None


def extract_ytdlp_datetime(url_or_path: str) -> tuple[str | None, str | None, str | None]:
    try:
        ydl_opts = {"skip_download": True, "quiet": True, "no_warnings": True, "enable_file_urls": True}
        with yt_dlp.YoutubeDL(cast(Any, ydl_opts)) as ydl:
            target = url_or_path if url_or_path.startswith(("http://", "https://")) else Path(url_or_path).as_uri()
            info = ydl.extract_info(target, download=False)
            if not info:
                return None, None, None

            v_id = info.get("id")
            raw_date = info.get("upload_date")
            raw_duration = info.get("duration")

            date = None
            duration = None

            if raw_date and len(str(raw_date)) == 8:
                date = f"{str(raw_date)[:4]}.{str(raw_date)[4:6]}.{str(raw_date)[6:8]}"

            if raw_duration is not None:
                minutes = round(int(raw_duration) / 60)
                duration = f"{minutes:03d}"

            return v_id, date, duration
    except DownloadError:
        return None, None, None


def process_file(file_path: Path) -> bool:
    target_url = None
    is_url_file = file_path.suffix.lower() == ".url"

    target_seconds = None
    duration = None
    date = None
    v_id = None

    if is_url_file:
        target_url = extract_url_from_shortcut(file_path)
    else:
        try:
            ydl_opts = {"skip_download": True, "quiet": True, "no_warnings": True, "enable_file_urls": True}
            with yt_dlp.YoutubeDL(cast(Any, ydl_opts)) as ydl:
                info = ydl.extract_info(file_path.as_uri(), download=False)
                dur = info.get("duration") if info else None
                if dur is not None:
                    target_seconds = int(dur)
                    duration = f"{round(target_seconds / 60):03d}"
        except (DownloadError, OSError, ValueError):
            pass

    v_id = extract_video_id(target_url or file_path.name)

    if v_id:
        date, duration, target_seconds = get_yt_api_metadata(v_id)
    if not date and v_id:
        _, date, duration = extract_ytdlp_datetime(f"https://www.youtube.com/watch?v={v_id}")

    if not date and target_url:
        v_id, date, duration = extract_ytdlp_datetime(target_url)
        if not date:
            date = extract_html_datetime(target_url)

    if not date:
        clean_title = clean_filename_title(file_path.name)
        v_id, date, duration = search_yt_by_title(clean_title, target_seconds=target_seconds)

    if not date:
        print(f"[ERROR] Could not extract date for: {file_path.name}")
        return False

    base_title = clean_filename_title(file_path.name)
    ext = file_path.suffix if not is_url_file else ".url"

    prefix = f"[{date}~]"
    if duration:
        prefix += f"[{duration}]"
    parts = [prefix, base_title]
    if v_id and v_id not in base_title:
        parts.append(f"[{v_id}]")

    new_name = " ".join(parts) + ext
    new_path = file_path.with_name(new_name)

    if new_path == file_path:
        print(f"[SKIP] Unchanged: {file_path.name}")
        return True

    if new_path.exists():
        print(f"[WARN] Target already exists: {new_path.name}")
        return False

    try:
        file_path.rename(new_path)
        print(f"[OK] {file_path.name} -> {new_path.name}")
        return True
    except OSError as e:
        print(f"[ERROR] Failed to rename {file_path.name}: {e}")
        return False


def main():
    if "--worker" not in sys.argv:
        app, folder_path, selected = get_context_fields("application", "folder_path", "selected_items")
        if app != "explorer.exe" or not folder_path or not selected:
            return
        cmd = ["cmd.exe", "/c", "start", "Metadata Enricher", "cmd.exe", "/k", sys.executable, __file__, "--worker"] + list(selected)
        subprocess.Popen(cmd, cwd=folder_path)
        return

    selected = sys.argv[sys.argv.index("--worker") + 1 :]
    if not selected:
        print("No files selected.")
        return

    print(f"[ACTIVE PATH] {Path.cwd()}")
    print(f"[SELECTED FILES] ({len(selected)} item(s)):")
    for item in selected:
        print(f"  - {Path(item).name}")
    print("-" * 50)

    target_files = [Path(item) for item in selected if Path(item).is_file()]
    if not target_files:
        print("No valid files selected.")
        return

    print("[INFO] Enriching file metadata...")
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(process_file, target_files))

    if not all(results):
        print("\n[!] Completed with errors.")
    else:
        print("\n[OK] Processing complete.")
        sys.exit(0)


if __name__ == "__main__":
    main()