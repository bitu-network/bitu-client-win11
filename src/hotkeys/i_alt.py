# file: src/hotkeys/i_alt.py
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import re
import sys
from typing import Any, cast
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import requests
import yt_dlp

from apps.explorer import get_active_explorer_info
from lib.wait_cursor import WaitCursor

# Reconfigure stdout/stderr for safe UTF-8 printing on Windows
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]


def extract_url_from_shortcut(url_file: Path) -> str | None:
    """Read the URL target from a Windows .url file."""
    try:
        text = url_file.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            if line.startswith("URL="):
                return line[4:].strip()
    except Exception:
        pass
    return None


def get_url_type(url: str) -> str:
    domain = urlparse(url).netloc.lower()
    video_domains = [
        "youtube.com",
        "youtu.be",
        "vimeo.com",
        "dailymotion.com",
        "twitch.tv",
    ]
    for site in video_domains:
        if site in domain:
            return "video"
    return "article"


def get_online_datetime(url: str) -> tuple[str | None, str | None]:
    url_type = get_url_type(url)

    if url_type == "video":
        date, duration = extract_ytdlp_datetime(url)
        if date:
            return date, duration
    else:
        date = extract_html_datetime(url)
        if date:
            return date, None

    date, duration = extract_ytdlp_datetime(url)
    if date:
        return date, duration

    date = extract_html_datetime(url)
    if date:
        return date, None

    return None, None


def rename_with_date(url_file: Path) -> bool:
    url = extract_url_from_shortcut(url_file)
    if not url:
        print(f"[ERROR] No URL found in shortcut: {url_file.name}")
        return False

    date, duration = get_online_datetime(url)
    if not date:
        print(f"[ERROR] Could not figure out publication date for: {url_file.name}")
        return False

    if duration:
        new_name = f"[{date}~][{duration}] {url_file.name}"
    else:
        new_name = f"[{date}~] {url_file.name}"

    new_path = url_file.with_name(new_name)
    if new_path.exists():
        print(f"[WARN] Target already exists: {new_path.name}")
        return False

    try:
        url_file.rename(new_path)
        print(f"[OK] {url_file.name} -> {new_path.name}")
        return True
    except Exception:
        print(f"[ERROR] Failed to rename {url_file.name}")
        return False


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
    except Exception:
        pass
    return None


def extract_ytdlp_datetime(url: str) -> tuple[str | None, str | None]:
    try:
        ydl_opts = {
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(cast(Any, ydl_opts)) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return None, None

            raw_date = info.get("upload_date")
            raw_duration = info.get("duration")

            date = None
            duration = None

            if raw_date and len(str(raw_date)) == 8:
                date = f"{str(raw_date)[:4]}.{str(raw_date)[4:6]}.{str(raw_date)[6:8]}"

            if raw_duration is not None:
                minutes = round(int(raw_duration) / 60)
                duration = f"{minutes:03d}"

            return date, duration
    except Exception:
        return None, None


def main():
    _, selected = get_active_explorer_info()
    if not selected:
        print("No files selected.")
        return

    url_files = [
        Path(item)
        for item in selected
        if Path(item).is_file() and Path(item).suffix.lower() == ".url"
    ]

    if not url_files:
        print("No .url files found in selection.")
        return

    print("[INFO] Fetching metadata and renaming files...")
    with WaitCursor(), ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(rename_with_date, url_files))

    if not all(results):
        print("\n[!] Completed with errors.")
        sys.exit(1)


if __name__ == "__main__":
    main()