# file: src/hotkeys/n_alt_ctrl_shift.py
# Opens a terminal-based folder creation interface initialized with the currently active Windows Explorer folder.

import os
import sys
from pathlib import Path

from apps.explorer import get_active_explorer_info
from web.tui_concept_selector import select_concept


def run_tui(target_folder: str | Path):
    result = select_concept(Path(target_folder))

    if not result:
        return

    path = os.path.join(target_folder, result)
    os.makedirs(path, exist_ok=True)


def get_target_folder():
    if len(sys.argv) < 2:
        explorer_folder, _ = get_active_explorer_info()
        if explorer_folder:
            return explorer_folder
        raise RuntimeError("Missing target folder from hotkey")

    return sys.argv[1]


def launch_tui():
    explorer_folder, _ = get_active_explorer_info()

    if not explorer_folder:
        print("No active Explorer folder detected")
        return

    run_tui(explorer_folder)


if __name__ == "__main__":
    run_tui(get_target_folder())