# file: src/hotkeys/s_ctrl_alt.py
# description: downloads selected Explorer .url shortcuts sequentially using embedded gallery_dl module, keeping console open on errors

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from lib.hotkey_context import get_context_fields


def parse_url_file(file_path: Path) -> Optional[str]:
    """Extracts the URL from an Internet Shortcut (.url) file."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        for line in content.splitlines():
            line = line.strip()
            if line.lower().startswith("url="):
                return line[4:].strip()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return None


def process_url_file(url_file: Path) -> None:
    target_url = parse_url_file(url_file)
    if not target_url:
        print(f"Skipping {url_file.name}: No valid 'URL=' line found.")
        return

    dest_dir = url_file.parent / url_file.stem

    print(f"\nProcessing: {url_file.name}")
    print(f"Target URL: {target_url}")
    print(f"Destination: {dest_dir}")

    # -d specifies the root destination path for downloads in gallery-dl
    cmd = [
        "cmd.exe",
        "/k",
        sys.executable,
        "-m",
        "gallery_dl",
        "--directory",
        str(dest_dir.resolve()),
        target_url,
    ]

    proc = subprocess.Popen(
        cmd,
        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0,
    )
    proc.wait()  # Enforces serial execution

    # Check if download succeeded and created content before removing shortcut
    if dest_dir.exists() and any(dest_dir.iterdir()):
        print(f"Successfully downloaded. Removing shortcut: {url_file.name}")
        try:
            url_file.unlink()
        except OSError as e:
            print(f"Failed to remove {url_file.name}: {e}")
    else:
        print(f"Download failed or produced no output for {url_file.name}. Preserving shortcut.")
        if dest_dir.exists() and not any(dest_dir.iterdir()):
            try:
                dest_dir.rmdir()
            except OSError:
                pass


def main() -> None:
    application, selected = get_context_fields("application", "selected_items")

    if application != "explorer.exe":
        print("Active window is not File Explorer.")
        return

    if not selected:
        print("No files selected in File Explorer.")
        return

    url_files = [Path(item) for item in selected if Path(item).suffix.lower() == ".url"]

    if not url_files:
        print("No .url files selected.")
        return

    # Process each selected .url file sequentially
    for url_file in url_files:
        process_url_file(url_file)


if __name__ == "__main__":
    main()