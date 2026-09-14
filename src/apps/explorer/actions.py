# file: src/apps/explorer/actions.py



from pathlib import Path
import time

import pythoncom
import win32api
import win32com.client
import win32con
import win32gui

from .utils import _is_mouse_down, _is_hwnd_responsive


def redirect_active_explorer(target_path, hwnd=None) -> bool:
    """
    Redirects a Windows File Explorer window to the given path safely.
    """
    if _is_mouse_down():
        return False

    pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)  # type: ignore[attr-defined]
    try:
        target_path = Path(target_path).resolve()
        shell = win32com.client.Dispatch("Shell.Application")
        target_hwnd = int(hwnd) if hwnd else win32gui.GetForegroundWindow()

        explorer_windows = []
        matching_window = None

        for window in shell.Windows():
            try:
                w_hwnd = int(window.HWND)
                if not _is_hwnd_responsive(w_hwnd):
                    continue
                if window.Document and hasattr(window.Document, "Folder"):
                    explorer_windows.append(window)
                    if w_hwnd == target_hwnd:
                        matching_window = window
            except Exception:
                continue

        if matching_window:
            matching_window.Navigate(str(target_path))
            return True

        if explorer_windows:
            explorer_windows[0].Navigate(str(target_path))
            return True

        shell.Open(str(target_path))
        return True

    except Exception as e:
        print("Explorer redirection error:", e)
        return False
    finally:
        pythoncom.CoUninitialize()


def focus_address_bar(target_path: Path) -> bool:
    """
    Focuses the active Explorer window's address bar and types the given path clipboard-free.
    """
    if _is_mouse_down():
        return False

    pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)  # type: ignore[attr-defined]
    try:
        input_val = str(target_path)
        target_path = Path(target_path)
        shell = win32com.client.Dispatch("Shell.Application")
        fg_hwnd = win32gui.GetForegroundWindow()

        matching_window = None
        for window in shell.Windows():
            try:
                w_hwnd = int(window.HWND)
                if not _is_hwnd_responsive(w_hwnd):
                    continue
                if w_hwnd == fg_hwnd:
                    matching_window = window
                    break
            except Exception:
                continue

        if not matching_window:
            for window in shell.Windows():
                try:
                    w_hwnd = int(window.HWND)
                    if not _is_hwnd_responsive(w_hwnd):
                        continue
                    matching_window = window
                    break
                except Exception:
                    continue

        if matching_window:
            win32gui.SetForegroundWindow(int(matching_window.HWND))
            time.sleep(0.05)

            # Focus address bar via Alt+D shortcut
            win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
            win32api.keybd_event(ord("D"), 0, 0, 0)
            win32api.keybd_event(ord("D"), 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(0.05)

            path_to_type = str(target_path)
            if input_val.endswith(("\\", "/")) and not path_to_type.endswith(
                ("\\", "/")
            ):
                path_to_type += "\\"

            for char in path_to_type:
                vk = win32api.VkKeyScan(char)
                if vk == -1:
                    continue
                shift = (vk >> 8) & 1
                keycode = vk & 0xFF
                if shift:
                    win32api.keybd_event(win32con.VK_SHIFT, 0, 0, 0)
                win32api.keybd_event(keycode, 0, 0, 0)
                win32api.keybd_event(keycode, 0, win32con.KEYEVENTF_KEYUP, 0)
                if shift:
                    win32api.keybd_event(
                        win32con.VK_SHIFT, 0, win32con.KEYEVENTF_KEYUP, 0
                    )
            return True

        return False
    except Exception as e:
        print("Address bar focus error:", e)
        return False
    finally:
        pythoncom.CoUninitialize()