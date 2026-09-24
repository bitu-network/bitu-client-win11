# file: src/hotkeys/s_ctrl_alt.py
# description: downloads selected Explorer .url shortcuts sequentially using the project's embedded gallery_dl module; auto-advances on success, pauses on error, and halts batch on terminal close

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


def process_url_file(url_file: Path) -> bool:
    """Processes a single URL shortcut. Returns True to continue batch, False to stop batch."""
    target_url = parse_url_file(url_file)
    if not target_url:
        print(f"Skipping {url_file.name}: No valid 'URL=' line found.")
        return True

    dest_dir = url_file.parent / url_file.stem

    print(f"\nProcessing: {url_file.name}")
    print(f"Target URL: {target_url}")
    print(f"Destination: {dest_dir}")

    # Build clean execution command for cmd.exe without double-quoted string mangling
    cmd = [
        "cmd.exe",
        "/c",
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
    status = proc.wait()  # Enforces serial execution

    download_succeeded = dest_dir.exists() and any(dest_dir.iterdir())

    if status == 0 and download_succeeded:
        print(f"Successfully downloaded. Removing shortcut: {url_file.name}")
        try:
            url_file.unlink()
        except OSError as e:
            print(f"Failed to remove {url_file.name}: {e}")
        return True  # Proceed automatically to the next gallery in batch

    # Handle download failure or manual window termination
    if not download_succeeded:
        print(f"Download aborted or failed for {url_file.name}. Preserving shortcut.")
        if dest_dir.exists() and not any(dest_dir.iterdir()):
            try:
                dest_dir.rmdir()
            except OSError:
                pass

    # Abort batch processing if window was closed or process returned non-zero exit status
    if status != 0:
        print("Terminal window closed or download failed. Halting batch execution.")
        return False

    return True


def main() -> None:
    application, selected = get_context_fields("application", "selected_items")

    if application != "explorer.exe":
        print("Active window is not File Explorer.")
        return

    if not selected:
        print("No files selected in File Explorer.")
        return

    # Filter for .url files and sort alphabetically by file name
    url_files = sorted(
        [Path(item) for item in selected if Path(item).suffix.lower() == ".url"],
        key=lambda p: p.name.lower()
    )

    if not url_files:
        print("No .url files selected.")
        return

    # Process each selected .url file sequentially in alphabetical order
    for url_file in url_files:
        should_continue = process_url_file(url_file)
        if not should_continue:
            print("Batch download cancelled.")
            break


if __name__ == "__main__":
    main()