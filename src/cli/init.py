# file: src/cli/init.py
# description: interactive setup wizard for turning a drive into a BITU node.
# Detects the drive of the current working directory, then runs each wizard
# script under init/ in order, injecting the detected drive root into each
# via init_globals (so a wizard doesn't need to re-detect it independently).
#
# Wizards live in a sibling "init" folder rather than being imported as a
# python package, since a package directory named "init" would collide with
# this module's own name (init.py) under normal python import resolution --
# runpy.run_path() sidesteps that by executing each file directly by path.

from __future__ import annotations

import os
import runpy
import shutil
from pathlib import Path

WIZARD_FOLDER = os.path.join(os.path.dirname(__file__), "init")

WIZARD_ORDER = [
    "config.py",
]


def _detect_drive_root() -> Path:
    """The drive of the terminal's current working directory, e.g. D:\\ ."""
    return Path(Path.cwd().anchor)


def main():
    drive_root = _detect_drive_root()
    print(f"[i] Setting up BITU on drive {drive_root}", flush=True)

    for filename in WIZARD_ORDER:
        filepath = os.path.join(WIZARD_FOLDER, filename)
        if not os.path.isfile(filepath):
            print(f"[!] Wizard not found: {filename}, skipping.")
            continue

        print(f"[+] Launching wizard: {filename}")
        runpy.run_path(filepath, init_globals={"DRIVE_ROOT": drive_root}, run_name="__main__")

        width = shutil.get_terminal_size().columns
        print("\n" + "|" * width + "\n")

    print("[\u2713] All wizards completed.")


if __name__ == "__main__":
    main()
