# file: src/service/hotkey_engine.py

import os
import sys
import ctypes
import json
import subprocess
import pythoncom
import threading
from pathlib import Path
from dataclasses import dataclass, field
import win32gui
import win32process
import win32api
import win32con
import keyboard
os.system("")  # Enable ANSI color escape sequences in Windows CMD
from project import get_src_root
from lib.ensures_single_instance import ensure_single_instance
from apps.explorer import get_active_explorer_info


@dataclass
class ActiveContext:
    application: str | None = None
    window_title: str | None = None
    folder_path: Path | None = None
    selected_items: list[Path] = field(default_factory=list)


def get_active_context() -> ActiveContext:
    """Strictly queries foreground window context without process guesswork."""
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return ActiveContext()

    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    try:
        process = win32api.OpenProcess(
            win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, pid
        )
        exe = Path(win32process.GetModuleFileNameEx(process, 0)).name.lower()
        title = win32gui.GetWindowText(hwnd)
    except Exception:
        exe, title = None, win32gui.GetWindowText(hwnd)

    context = ActiveContext(application=exe, window_title=title)

    # Only attempt COM Shell query if the foreground window is natively Explorer
    if exe == "explorer.exe":
        pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)
        try:
            folder, selected = get_active_explorer_info()
            context.folder_path = folder
            context.selected_items = selected
        except Exception as e:
            print(f"[DEBUG] Explorer COM lookup skipped: {e}")
        finally:
            pythoncom.CoUninitialize()

    return context


class HotkeyEngine:
    def __init__(self, scripts_folder: Path):
        self.scripts_folder = Path(scripts_folder)
        self.scripts_folder.mkdir(parents=True, exist_ok=True)

    def load_scripts(self) -> dict:
        combo_map = {}
        for f in self.scripts_folder.glob("*.py"):
            parts = f.stem.split("_")
            if parts:
                key = parts[0].upper()
                mods = parts[1:]
                combo_map[(tuple(sorted(mods)), key)] = f
        return combo_map

    def dispatch(self, mods: list[str], key: str):
        combo_map = self.load_scripts()
        script_path = combo_map.get((tuple(sorted(mods)), key.upper()))
        if not script_path:
            return
        
        print(f"\033[92m[HOTKEY TRIGGERED]\033[0m {'+'.join(mods).upper()}+{key.upper()} -> {script_path.name}")

        context = get_active_context()
        context_data = {
            "application": context.application,
            "window_title": context.window_title,
            "folder_path": str(context.folder_path) if context.folder_path else None,
            "selected_items": [str(p) for p in context.selected_items],
        }

        env = os.environ.copy()
        env["PYTHONPATH"] = str(get_src_root())

        # Spawn child script without creating hidden focus-stealing console windows
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        subprocess.Popen(
            [sys.executable, str(script_path), json.dumps(context_data)],
            env=env,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )

    def start(self):
        combo_map = self.load_scripts()

        print(f"\n\033[95m=== REGISTERED HOTKEYS ({len(combo_map)}) ===\033[0m")
        for (mods, key), script_path in combo_map.items():
            # Remove duplicate modifier entries derived from filename parsing
            clean_mods = list(dict.fromkeys(mods))
            combo_str = "+".join(clean_mods + [key]).upper()
            print(f"  \033[93m{combo_str:<20}\033[0m -> \033[96m{script_path.name}\033[0m")
        print("\033[95m=================================\033[0m\n")


        for mods, key in combo_map.keys():
            hotkey_str = "+".join(list(mods) + [key.lower()])
            is_ctrl_v = (tuple(mods) == ("ctrl",) and key == "V")
            
            keyboard.add_hotkey(
                hotkey_str,
                lambda m=list(mods), k=key: threading.Thread(
                    target=lambda m=m, k=k: self.dispatch(m, k), daemon=True
                ).start(),
                suppress=is_ctrl_v,
            )

        print("[+] Listening for hotkeys...")
        keyboard.wait()


def main():
    # Permanently disable QuickEdit mode on the current terminal handle
    if os.name == "nt":
        try:
            kernel32 = ctypes.windll.kernel32
            h_input = kernel32.GetStdHandle(-10)  # STD_INPUT_HANDLE
            mode = ctypes.c_uint32()
            if kernel32.GetConsoleMode(h_input, ctypes.byref(mode)):
                kernel32.SetConsoleMode(h_input, mode.value & ~0x0040)
        except Exception:
            pass

    if not ensure_single_instance("hotkey_listener"):
        print("[Hotkey Engine] Instance already running. Exiting.")
        sys.exit(0)

    src_root = get_src_root()
    hotkeys_dir = src_root / "hotkeys"
    pid_file = hotkeys_dir / "hotkey_listener.pid"
    pid_file.write_text(str(os.getpid()))

    engine = HotkeyEngine(hotkeys_dir)
    try:
        engine.start()
    finally:
        if pid_file.exists():
            try:
                pid_file.unlink()
            except Exception:
                pass


if __name__ == "__main__":
    main()