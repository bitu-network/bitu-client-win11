# file: src/hotkeys/t_alt_ctrl.py
import os
import subprocess
from pathlib import Path
from apps.explorer import get_active_explorer_info


def main():
    folder, selected = get_active_explorer_info()
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
        subprocess.Popen(["xdg-open"], cwd=str(target_dir))


if __name__ == "__main__":
    main()