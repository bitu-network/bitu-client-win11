# file: src/hotkeys/n_alt_ctrl.py
# Creates an empty timestamp-named .txt file in the currently active Windows Explorer folder when triggered by the hotkey .

import os
from datetime import datetime
from apps.explorer import get_active_explorer_info

explorer_folder, selected = get_active_explorer_info()

if not explorer_folder:
    raise RuntimeError("No active Explorer folder detected")

now = datetime.now()

target_dir = explorer_folder

os.makedirs(target_dir, exist_ok=True)

filepath = os.path.join(
    target_dir,
    now.strftime("%Y.%m.%d %H%M") + ".txt"
)

open(filepath, "a", encoding="utf-8").close()
# os.startfile(filepath) # automatically open the newly created file.