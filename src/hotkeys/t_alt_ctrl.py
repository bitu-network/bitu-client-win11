# file: src/hotkeys/t_alt_ctrl.py
# description: hotkey script to open a new command prompt at the hotkey-captured explorer directory

import os
import subprocess
from pathlib import Path
from lib.hotkey_context import load_context


def main():
    ctx = load_context()
    folder = ctx.get("folder_path") if ctx else None
    target_dir = Path(folder) if folder else Path.cwd()

    if not target_dir.is_dir():
        target_dir = Path.home()

    if os.name == "nt":
        subprocess.Popen(
            ["cmd.exe"],
            cwd=str(target_dir),
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
    else:
        subprocess.Popen(["xdg-open", str(target_dir)], cwd=str(target_dir))


if __name__ == "__main__":
    main()