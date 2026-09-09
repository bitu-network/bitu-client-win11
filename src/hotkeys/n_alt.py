# file: src/hotkeys/n_alt.py
# Renames selected files using a timestamp derived from their file metadata, adding numeric suffixes to avoid collisions.

import os
from datetime import datetime
from apps.explorer import get_active_explorer_info

folder, selected = get_active_explorer_info()

if not folder or not selected:
    print("No files selected.")
    raise SystemExit

for i, filename in enumerate(selected, start=1):
    old_path = os.path.join(folder, filename)

    # Get the file's modification time from its metadata
    file_time = os.path.getmtime(old_path)
    timestamp = datetime.fromtimestamp(file_time).strftime("%Y%m%d%H%M")

    name, ext = os.path.splitext(filename)

    # Avoid collisions when multiple files are selected
    new_name = f"{timestamp}{'' if i == 1 else f' {i}'}{ext}"
    new_path = os.path.join(folder, new_name)

    os.rename(old_path, new_path)

    print(f"{filename} -> {new_name}")