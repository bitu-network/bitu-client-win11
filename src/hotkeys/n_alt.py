# file: src/hotkeys/n_alt.py

import os
import sys
from pathlib import Path
from datetime import datetime
from lib.hotkey_context import get_context_fields


def rename_selected():
    app, folder_str, selected = get_context_fields("application", "folder_path", "selected_items")

    if app != "explorer.exe" or not folder_str or not selected:
        print("[n_alt] No active Explorer folder or files selected.")
        return

    folder = Path(folder_str)

    for i, item_str in enumerate(selected, start=1):
        filename = Path(item_str).name
        old_path = folder / filename

        if not old_path.exists():
            continue

        file_time = os.path.getmtime(old_path)
        timestamp = datetime.fromtimestamp(file_time).strftime("%Y%m%d%H%M")
        ext = old_path.suffix

        new_name = f"{timestamp}{'' if i == 1 else f' {i}'}{ext}"
        new_path = folder / new_name

        try:
            old_path.rename(new_path)
            print(f"[n_alt] {filename} -> {new_name}")
        except Exception as e:
            print(f"[n_alt] Error renaming {filename}: {e}")


if __name__ == "__main__":
    rename_selected()