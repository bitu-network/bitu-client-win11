# file: src/service/hotkey_engine.py
# description: robust low-level keyboard hook (WH_KEYBOARD_LL) engine for zero-flicker selective hotkey interception

from __future__ import annotations
from __main__ import *

import ctypes
from ctypes import wintypes
import json
import os
import queue
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import pythoncom
import win32api
import win32con
import win32gui
import win32process

from apps.explorer import get_active_explorer_info
from lib.ensures_single_instance import ensure_single_instance
from project import get_src_root

os.system("")  # enable ansi color escape sequences in windows cmd

@dataclass
class ActiveContext:
    application: str | None = None
    window_title: str | None = None
    folder_path: Path | None = None
    selected_items: list[Path] = field(default_factory=list)

def _get_vk_code(key_str: str) -> int:
    key = key_str.lower()
    if len(key) == 1:
        return ord(key.upper())
    
    special_keys = {
        "f1": win32con.VK_F1, "f2": win32con.VK_F2, "f3": win32con.VK_F3, "f4": win32con.VK_F4,
        "f5": win32con.VK_F5, "f6": win32con.VK_F6, "f7": win32con.VK_F7, "f8": win32con.VK_F8,
        "f9": win32con.VK_F9, "f10": win32con.VK_F10, "f11": win32con.VK_F11, "f12": win32con.VK_F12,
        "space": win32con.VK_SPACE, "enter": win32con.VK_RETURN, "tab": win32con.VK_TAB,
        "esc": win32con.VK_ESCAPE, "backspace": win32con.VK_BACK, "delete": win32con.VK_DELETE,
    }
    return special_keys.get(key, 0)

def get_active_context() -> ActiveContext:
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
    except Exception as e:
        exe, title = None, win32gui.GetWindowText(hwnd)
        if os.environ.get("BITU_EXPLORER_DEBUG"):
            print(f"[hotkey_engine DEBUG] exe detection failed for hwnd={hwnd} pid={pid}: {e}")

    if os.environ.get("BITU_EXPLORER_DEBUG"):
        print(f"[hotkey_engine DEBUG] foreground hwnd={hwnd} pid={pid} exe={exe!r} title={title!r}")

    context = ActiveContext(application=exe, window_title=title)

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


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))
    ]


class HotkeyEngine:
    def __init__(self, scripts_folder: Path):
        self.scripts_folder = Path(scripts_folder)
        self.scripts_folder.mkdir(parents=True, exist_ok=True)
        self.task_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.combo_map = {}
        self._hook_id = None
        self._hook_callback = None
        
        user32 = ctypes.windll.user32
        user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
        user32.CallNextHookEx.restype = ctypes.c_long
        self._call_next_hook = user32.CallNextHookEx

    def load_scripts(self) -> dict:
        combo_map = {}
        for f in self.scripts_folder.glob("*.py"):
            parts = f.stem.split("_")
            if parts:
                key = parts[0].upper()
                mods = [m.lower() for m in parts[1:]]
                combo_map[(tuple(sorted(mods)), key)] = f
        return combo_map

    def _log_debug(self, msg: str):
        log_file = self.scripts_folder / "hotkey_debug.log"
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {msg}\n")
        except Exception:
            pass

    def _worker_loop(self):
        while True:
            mods, key, script_path = self.task_queue.get()
            try:
                msg = f"[HOTKEY TRIGGERED] {'+'.join(mods).upper()}+{key.upper()} -> {script_path.name}"
                print(f"\033[92m{msg}\033[0m")
                self._log_debug(msg)

                context = get_active_context()
                context_data = {
                    "application": context.application,
                    "window_title": context.window_title,
                    "folder_path": str(context.folder_path) if context.folder_path else None,
                    "selected_items": [str(p) for p in context.selected_items],
                }

                env = os.environ.copy()
                env["PYTHONPATH"] = str(get_src_root())

                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0  # SW_HIDE

                subprocess.Popen(
                    [sys.executable, str(script_path), json.dumps(context_data)],
                    env=env,
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP,
                )
            except Exception as e:
                err_msg = f"[ERROR] Dispatch failed for {script_path.name}: {e}"
                print(err_msg, file=sys.stderr)
                self._log_debug(err_msg)
            finally:
                self.task_queue.task_done()

    def enqueue_dispatch(self, mods: list[str], key: str):
        script_path = self.combo_map.get((tuple(sorted(mods)), key.upper()))
        if script_path:
            self.task_queue.put((mods, key, script_path))

    def _low_level_keyboard_proc(self, nCode, wParam, lParam):
        if nCode >= 0 and wParam in (win32con.WM_KEYDOWN, win32con.WM_SYSKEYDOWN):
            kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            vk = kb.vkCode

            # Check modifier states live from hardware state
            ctrl_pressed = bool(win32api.GetAsyncKeyState(win32con.VK_CONTROL) & 0x8000)
            alt_pressed = bool(win32api.GetAsyncKeyState(win32con.VK_MENU) & 0x8000)
            shift_pressed = bool(win32api.GetAsyncKeyState(win32con.VK_SHIFT) & 0x8000)
            win_pressed = bool(win32api.GetAsyncKeyState(win32con.VK_LWIN) & 0x8000 or win32api.GetAsyncKeyState(win32con.VK_RWIN) & 0x8000)

            active_mods = []
            if ctrl_pressed: active_mods.append("ctrl")
            if alt_pressed: active_mods.append("alt")
            if shift_pressed: active_mods.append("shift")
            if win_pressed: active_mods.append("win")

            # Determine key name from vkCode
            key_name = None
            if 48 <= vk <= 57 or 65 <= vk <= 90:  # 0-9, A-Z
                key_name = chr(vk).upper()
            elif win32con.VK_F1 <= vk <= win32con.VK_F12:
                key_name = f"f{vk - win32con.VK_F1 + 1}"
            else:
                for k, code in {"space": win32con.VK_SPACE, "enter": win32con.VK_RETURN, "tab": win32con.VK_TAB, "esc": win32con.VK_ESCAPE}.items():
                    if vk == code:
                        key_name = k.upper()
                        break

            if key_name:
                combo_key = (tuple(sorted(active_mods)), key_name)
                if combo_key in self.combo_map:
                    self.enqueue_dispatch(active_mods, key_name)
                    return 1  # Swallow event completely, preventing any default window action or flash

        return self._call_next_hook(self._hook_id, nCode, wParam, lParam)

    def start(self):
        self.combo_map = self.load_scripts()

        print(f"\n\033[95m=== REGISTERED HOTKEYS ({len(self.combo_map)}) ===\033[0m")
        for (mods, key), script_path in self.combo_map.items():
            clean_mods = list(dict.fromkeys(mods))
            combo_str = "+".join(clean_mods + [key]).upper()
            print(f"  \033[93m{combo_str:<20}\033[0m -> \033[96m{script_path.name}\033[0m")
        print("\033[95m=================================\033[0m\n")

        self.worker_thread.start()

        CMPFUNC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
        self._hook_callback = CMPFUNC(self._low_level_keyboard_proc)
        
        self._hook_id = ctypes.windll.user32.SetWindowsHookExW(
            win32con.WH_KEYBOARD_LL, self._hook_callback, None, 0
        )

        if not self._hook_id:
            print("\033[91m[!] Failed to install WH_KEYBOARD_LL hook.\033[0m")
            return

        print("[+] Listening for hotkeys via WH_KEYBOARD_LL hook...")

        msg = wintypes.MSG()
        try:
            while ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
                ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            if self._hook_id:
                ctypes.windll.user32.UnhookWindowsHookEx(self._hook_id)


def main():
    if not ensure_single_instance("hotkey_listener"):
        print("[Hotkey Engine] Instance already running. Exiting.")
        sys.exit(0)

    src_root = get_src_root()
    hotkeys_dir = src_root / "hotkeys"
    hotkeys_dir.mkdir(parents=True, exist_ok=True)
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