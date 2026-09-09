# file: src/lib/kbd_hotkey_script_loader.py

import os  # Added
import sys  # Added
import subprocess
import json
from pathlib import Path
from lib.context_finder import get_active_context
from project import get_src_root  # Added


class HotkeyScriptLoader:
    def __init__(self, scripts_folder: Path):
        self.SCRIPT_FOLDER = Path(scripts_folder)
        print(f"Hotkey scripts folder: {self.SCRIPT_FOLDER}")

        self.SCRIPT_FOLDER.mkdir(exist_ok=True)
        self.combo_map = self.load_scripts()

    def load_scripts(self, folder: Path | None = None):
        """Load all Python scripts in the folder into a combo map."""
        folder = folder or self.SCRIPT_FOLDER
        combo_map = {}

        for f in folder.glob("*.py"):
            parts = f.stem.split("_")

            if not parts:
                continue

            key = parts[0].upper()
            mods = parts[1:]

            combo_map[(tuple(sorted(mods)), key)] = f

        return combo_map

    def on_combo(self, mods, key):
        """Callback invoked on combo detection."""

        try:

            self.combo_map = self.load_scripts()

            combo_tuple = (tuple(sorted(mods)), key.upper() if key else None)
            script_path = self.combo_map.get(combo_tuple)

            if not script_path:
                return

            context = get_active_context()

            context_data = {
                "application": context.application,
                "window_title": context.window_title,
                "folder_path": (
                    str(context.folder_path) if context.folder_path else None
                ),
                "selected_items": [str(item) for item in context.selected_items],
            }

            env = os.environ.copy()
            env["PYTHONPATH"] = str(get_src_root())

            subprocess.Popen(
                [
                    sys.executable,
                    str(script_path),
                    json.dumps(context_data),
                ],
                env=env
            )

        except Exception as e:
            print(f"[ERROR] Combo execution failed: {e}")