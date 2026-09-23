# file: src/hotkeys/g_ctrl.py
import sys
from pathlib import Path

from apps.explorer import focus_address_bar
from lib.hotkey_context import get_context_fields
from pod.paths import CONCEPTS_DIR, pod_root

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))


def set_explorer_address_bar():
    app, folder, _ = get_context_fields("application", "folder_path", "selected_items")
    if app != "explorer.exe" or not folder:
        return

    folder_path = Path(folder)
    if not folder_path.anchor:
        return  # not a filesystem folder (e.g. "This PC")
    target_path = f"{pod_root(folder_path) / CONCEPTS_DIR}\\"


    focus_address_bar(target_path)  # type: ignore[arg-type]


if __name__ == "__main__":
    try:
        set_explorer_address_bar()
    except Exception as e:  # noqa: BLE001
        print("ERROR:", e)