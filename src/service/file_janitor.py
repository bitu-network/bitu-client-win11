# file: src/service/file_janitor.py
# description: background janitor service that detects accidental native file copies in active directories and replaces them with hardlinks

from __future__ import annotations

import ctypes
from ctypes import wintypes
from pathlib import Path
import time

user32 = ctypes.windll.user32
user32.GetForegroundWindow.restype = wintypes.HWND


def get_active_explorer_path() -> Path | None:
    """Retrieve the current folder path of the active Windows Explorer window via COM."""
    try:
        import comtypes.client  # type: ignore

        shell = comtypes.client.CreateObject("Shell.Application")
        hwnd = user32.GetForegroundWindow()
        for window in shell.Windows():
            if window.HWND == hwnd:
                return Path(window.Document.Folder.Self.Path)
    except (ImportError, AttributeError, OSError):
        pass
    return None


def janitor_pass() -> None:
    """Scan the active directory for native Windows duplicate copies and convert them to hardlinks."""
    target_dir = get_active_explorer_path()
    if not target_dir or not target_dir.exists():
        return

    try:
        for item in target_dir.iterdir():
            if not item.is_file():
                continue

            name = item.name
            if " - Copy" in name:
                base_name_part = name.split(" - Copy")[0]
                suffix = item.suffix
                original_name = f"{base_name_part}{suffix}"
                original_file = target_dir / original_name

                if original_file.exists() and original_file.is_file():
                    if item.drive.upper() == original_file.drive.upper():
                        try:
                            item.unlink()
                            item.hardlink_to(original_file)
                            print(f"[JANITOR] Converted accidental copy to hardlink: {name} -> {original_name}")
                        except (OSError, IOError) as e:
                            print(f"[ERROR] Failed to convert {name} to hardlink: {e}")
    except (OSError, RuntimeError) as e:
        print(f"[ERROR] Janitor directory scan failed: {e}")


def main() -> None:
    print("Initializing file_janitor service...")
    while True:
        try:
            janitor_pass()
            time.sleep(3.0)
        except KeyboardInterrupt:
            break
        except (OSError, RuntimeError) as e:
            print(f"[ERROR] Janitor loop exception: {e}")
            time.sleep(5.0)


if __name__ == "__main__":
    main()