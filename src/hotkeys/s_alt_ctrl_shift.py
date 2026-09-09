# file: src/hotkeys/s_alt_ctrl_shift.py
# Moves selected dated journal files into a calendar archive and creates tag-based shortcuts from extracted hashtags to the archived files.

import os
import re
import shutil
from datetime import datetime
from pod.paths import personal_concepts_root, personal_calendar_root
from apps.explorer import get_active_explorer_info
from lib.fs.shortcut_creator import create_windows_shortcut
from pathlib import Path


explorer_folder, selected = get_active_explorer_info()

if not explorer_folder:
    raise RuntimeError("No active Explorer folder detected")




pattern = re.compile(r"^\d{4}\.\d{2}\.\d{2} \d{4}\.txt$")
hashtag_pattern = re.compile(r"#([a-zA-Z0-9_]+)")

MAX_TAGS = 10

# for name in os.listdir(explorer_folder):
for src in selected:
    name = os.path.basename(src)
   
    if not pattern.match(name):
        continue

    # src = os.path.join(explorer_folder, name)

    if not os.path.isfile(src):
        continue

    # read file content for hashtags
    try:
        with open(src, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        continue

    tags = list(dict.fromkeys(hashtag_pattern.findall(content)))[:MAX_TAGS]

    date_part = name.split(" ")[0]
    year, month, day = date_part.split(".")

    # archive target
    target_dir = os.path.join(personal_calendar_root(explorer_folder), year, month, day)
    os.makedirs(target_dir, exist_ok=True)

    dst = os.path.join(target_dir, name)

    shutil.move(src, dst)

    # create tag shortcuts
    for tag in tags:
        # tag_dir = os.path.join(root, "I/-", tag.replace("_", " "))
        tag_dir = os.path.join(
            personal_concepts_root(explorer_folder), tag.replace("_", " ")
        )
        os.makedirs(tag_dir, exist_ok=True)

        link_path = os.path.join(tag_dir, name)

        shortcut_path = Path(link_path + ".lnk")

        ok = create_windows_shortcut(shortcut_path, Path(dst))

        if not ok:
            with open(link_path + ".txt", "w", encoding="utf-8") as f:
                f.write(dst)
