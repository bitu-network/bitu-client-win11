# file: src/hotkeys/l_alt.py
# Bi-directional link and return: drops a .lnk of the current path in the previous history folder and navigates back.

import ctypes
import os
import subprocess
import sys
import time
from pathlib import Path
import win32gui
import win32com.client
import win32api
import win32con

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))


def force_windows_shell_refresh(path):
    if os.path.exists(path):
        os.utime(path, None)
        SHCNE_UPDATEDIR = 0x00001000
        SHCNF_PATHW = 0x0005
        ctypes.windll.shell32.SHChangeNotify(
            SHCNE_UPDATEDIR, SHCNF_PATHW, ctypes.c_wchar_p(path), None
        )


def create_shortcut(target_path: Path, dest_dir: Path):
    if not target_path.exists():
        return False

    link_name = f"{target_path.name}.lnk"
    link_path = dest_dir / link_name

    counter = 1
    while link_path.exists():
        link_name = f"{target_path.name} ({counter}).lnk"
        link_path = dest_dir / link_name
        counter += 1

    safe_target = str(target_path).replace("'", "''")
    safe_link = str(link_path).replace("'", "''")
    safe_workdir = str(
        target_path.parent if target_path.is_file() else target_path
    ).replace("'", "''")

    ps_script = (
        f"$ws = New-Object -ComObject WScript.Shell; "
        f"$sc = $ws.CreateShortcut('{safe_link}'); "
        f"$sc.TargetPath = '{safe_target}'; "
        f"$sc.WorkingDirectory = '{safe_workdir}'; "
        f"$sc.Save()"
    )
    powershell_cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        ps_script,
    ]
    try:
        res = subprocess.run(
            powershell_cmd,
            capture_output=True,
            text=True,
            timeout=2,
            creationflags=0x08000000,
            check=False,
        )
        if res.returncode == 0:
            force_windows_shell_refresh(str(dest_dir))
            return True
    except Exception:
        pass
    return False


def get_active_explorer_path() -> Path:
    try:
        hwnd = win32gui.GetForegroundWindow()
        shell = win32com.client.Dispatch("Shell.Application")
        for window in shell.Windows():
            if window.HWND == hwnd:
                return Path(window.Document.Folder.Self.Path)
    except Exception:
        pass
    try:
        shell = win32com.client.Dispatch("Shell.Application")
        for window in shell.Windows():
            return Path(window.Document.Folder.Self.Path)
    except Exception:
        pass
    return Path("C:\\")


def handle_l_alt():
    # 1. Capture current path before leaving
    current_path = get_active_explorer_path()
    if not current_path.exists():
        return

    # 2. Simulate Alt+Left to go back in Explorer history
    hwnd = win32gui.GetForegroundWindow()
    if hwnd:
        win32gui.SetForegroundWindow(hwnd)
        win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
        win32api.keybd_event(win32con.VK_LEFT, 0, 0, 0)
        win32api.keybd_event(win32con.VK_LEFT, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)

    # 3. Give Explorer a brief moment to update its active directory to the previous path
    time.sleep(0.15)

    # 4. Grab the new active path (which is now the previous folder in history)
    previous_path = get_active_explorer_path()

    # 5. Create the shortcut of the old current path inside the previous path
    if previous_path and previous_path != current_path and previous_path.exists():
        create_shortcut(current_path, previous_path)


if __name__ == "__main__":
    try:
        handle_l_alt()
    except Exception as e:
        print("ERROR:", e)