# file: src/hotkeys/n_alt.py
import ctypes
import json
import sys
from datetime import datetime
from pathlib import Path

def get_win32_move_file():
    """Fallback Win32 move to bypass transient Explorer lock handles."""
    move = ctypes.windll.kernel32.MoveFileExW
    move.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32]
    move.restype = ctypes.c_int
    return move


def get_creation_timestamp(file_path: Path) -> datetime:
    """Retrieve Windows creation time (ctime), defaulting to current time on failure."""
    try:
        return datetime.fromtimestamp(file_path.stat().st_ctime)
    except Exception:
        return datetime.now()


def parse_name_and_ext(file_path: Path) -> tuple[str, str]:
    """Accurately parse extension and name stem, handling dotfiles (e.g. '.jpg')."""
    if file_path.is_dir():
        return file_path.name, ""

    name = file_path.name
    if name.startswith(".") and name.count(".") == 1:
        return "", name

    return file_path.stem, file_path.suffix


def rename_item(target_path: Path) -> None:
    target = target_path.resolve()
    if not target.exists():
        return

    dt = get_creation_timestamp(target)
    timestamp_prefix = dt.strftime("%Y%m%d%H%M%S")

    _, ext = parse_name_and_ext(target)
    new_name = f"{timestamp_prefix}{ext}"
    new_path = target.parent / new_name

    if target == new_path:
        return

    counter = 1
    while new_path.exists():
        new_name = f"{timestamp_prefix}_{counter}{ext}"
        new_path = target.parent / new_name
        counter += 1

    try:
        target.rename(new_path)
    except Exception:
        win32_move = get_win32_move_file()
        # MOVEFILE_REPLACE_EXISTING (0x1) | MOVEFILE_WRITE_THROUGH (0x8)
        win32_move(str(target), str(new_path), 0x1 | 0x8)


def parse_targets_from_args() -> list[Path]:
    """Extract path targets from JSON payload or raw CLI arguments."""
    if len(sys.argv) < 2:
        return []

    raw_arg = sys.argv[1]
    targets = []

    try:
        data = json.loads(raw_arg)
        if isinstance(data, dict):
            selected = data.get("selected_items", [])
            if selected:
                return [Path(p) for p in selected]
            
            folder = data.get("folder_path")
            if folder:
                return [Path(folder)]
    except (json.JSONDecodeError, TypeError):
        pass

    # Direct CLI invocation fallback
    for arg in sys.argv[1:]:
        targets.append(Path(arg.strip('"')))

    return targets


if __name__ == "__main__":
    try:
        items = parse_targets_from_args()
        for item in items:
            rename_item(item)
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")