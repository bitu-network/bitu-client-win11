# file: src/hotkeys/s_ctrl.py
# classifying selected Explorer items and dispatching them to appropriate processors such as media archiving.

import os
import subprocess
import sys
import json
import base64
from pathlib import Path
from lib.hotkey_context import get_context_fields
from pod.folders import move_folder_to_concepts

# --------------------------------------------------
# Main
# --------------------------------------------------

application, selected = get_context_fields(
    "application",
    "selected_items",
)

if application != "explorer.exe":
    print("Active window is not File Explorer.")
    raise SystemExit(0)

if not selected:
    print("No files selected.")
    raise SystemExit(0)

url_files = []

for item in map(Path, selected):
    if item.is_dir():
        print(f"  -> moving folder to concepts: {item}")
        move_folder_to_concepts(item)
        if os.name == "nt":
            import ctypes

            ctypes.windll.shell32.SHChangeNotify(
                0x00001000, 0x0005, str(item.parent), None
            )
    elif item.is_file():
        ext = item.suffix.lower()
        if ext == ".url":
            url_files.append(item)
    else:
        print(f"[UNKNOWN] {item}")

if url_files:
    env = os.environ.copy()

    json_bytes = json.dumps([str(f) for f in url_files]).encode("utf-8")
    env["BITU_URL_FILES_B64"] = base64.b64encode(json_bytes).decode("ascii")

    subprocess.Popen(
        [sys.executable, "-m", "lib.net.vid_download"],
        env=env,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )