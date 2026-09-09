# file: src/hotkeys/p_alt_ctrl.py
# version: 1.6
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse
import tkinter as tk

from lib.wait_cursor import WaitCursor

# Reconfigure stdout/stderr for safe UTF-8 printing on Windows
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]


def get_explorer_path() -> str:
    try:
        from apps.explorer import get_active_explorer_info
        path_str, _ = get_active_explorer_info()
        if path_str and Path(path_str).is_dir():
            return path_str  # type: ignore
    except Exception:
        pass

    try:
        import win32com.client
        shell = win32com.client.Dispatch("Shell.Application")
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        for window in shell.Windows():
            try:
                if window.HWND == hwnd:
                    p = window.Document.Folder.Self.Path
                    if p and Path(p).is_dir():
                        return p
            except Exception:
                continue
        for window in shell.Windows():
            try:
                p = window.Document.Folder.Self.Path
                if p and Path(p).is_dir():
                    return p
            except Exception:
                continue
    except Exception:
        pass
    return ""


def force_windows_shell_refresh(path, is_item=False):
    if os.path.exists(path):
        os.utime(path, None)
        SHCNE_UPDATEDIR = 0x00001000
        SHCNE_UPDATEITEM = 0x00002000
        SHCNF_PATHW = 0x0005
        flag = SHCNE_UPDATEITEM if is_item else SHCNE_UPDATEDIR
        try:
            ctypes.windll.shell32.SHChangeNotify(
                flag, SHCNF_PATHW, ctypes.c_wchar_p(path), None
            )
        except Exception:
            pass


def evict_windows_thumbnail_cache(path):
    try:
        stat = os.stat(path)
        new_mtime = time.time()
        os.utime(path, (stat.st_atime, new_mtime))
    except Exception:
        pass


def get_active_explorer_path() -> Path:
    env_path = os.environ.get("ACTIVE_EXPLORER_PATH")
    if env_path and Path(env_path).is_dir():
        return Path(env_path)
    
    path_str = get_explorer_path()
    if path_str and Path(path_str).is_dir():
        return Path(path_str)

    return Path.cwd()


def is_youtube_url(url: str) -> bool:
    if not url:
        return False
    url_lower = url.lower()
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return True
    try:
        domain = urlparse(url).netloc.lower()
        return "youtube.com" in domain or "youtu.be" in domain
    except Exception:
        return False


def get_clipboard_url() -> str | None:
    try:
        root = tk.Tk()
        root.withdraw()
        text = root.clipboard_get().strip()
        root.destroy()
        if is_youtube_url(text):
            return text
    except Exception as e:
        print(f"[DEBUG] Clipboard read error: {e}")
    return None


def download_thumbnail(url: str, output_dir: Path) -> bool:
    cmd = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--skip-download",
        "--write-thumbnail",
        "--output",
        "%(title)s",
        url,
    ]
    try:
        result = subprocess.run(
            cmd,
            cwd=str(output_dir),
            check=False,
            creationflags=0x08000000 if os.name == "nt" else 0,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"[ERROR] yt-dlp failed: {result.stderr.strip()}")
            return False
        return True
    except Exception as e:
        print(f"[ERROR] Failed to download thumbnail for {url}: {e}")
        return False


def main():
    current_dir = get_active_explorer_path()
    print(f"[INFO] Target Explorer Directory: {current_dir}")

    clipboard_url = get_clipboard_url()
    has_errors = False

    if clipboard_url:
        print(f"[DOWNLOAD] Found YouTube URL in clipboard: {clipboard_url}")
        with WaitCursor():
            success = download_thumbnail(clipboard_url, current_dir)
        if success:
            print("[OK] Thumbnail downloaded successfully.")
            evict_windows_thumbnail_cache(current_dir)
            force_windows_shell_refresh(str(current_dir), is_item=False)
        else:
            has_errors = True
    else:
        print("[INFO] No YouTube URL found in clipboard.")
        has_errors = True

    if has_errors:
        sys.exit(1)


if __name__ == "__main__":
    main()