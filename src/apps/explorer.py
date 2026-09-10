# file: src/apps/explorer.py
from pathlib import Path
import pythoncom
import win32com.client
import win32gui
import time
import win32api
import win32con

# TODO: Refactor window-lookup logic into a private helper function to DRY up redirect_active_explorer and focus_address_bar


def get_active_explorer_info() -> tuple[Path | None, list[Path]]:
    pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)  # type: ignore[attr-defined]
    try:
        shell = win32com.client.Dispatch("Shell.Application")
        fg_hwnd = win32gui.GetForegroundWindow()
        root_fg_hwnd = win32gui.GetAncestor(fg_hwnd, win32con.GA_ROOT) if fg_hwnd else 0

        matching_candidates = []
        for window in shell.Windows():
            try:
                w_hwnd = int(window.HWND)
                w_root = win32gui.GetAncestor(w_hwnd, win32con.GA_ROOT) if w_hwnd else 0
                if w_hwnd == fg_hwnd or (root_fg_hwnd and w_root == root_fg_hwnd):
                    folder_path = (
                        Path(window.Document.Folder.Self.Path)
                        if window.Document and hasattr(window.Document, "Folder")
                        else None
                    )
                    selected_items = []
                    if window.Document and hasattr(window.Document, "SelectedItems"):
                        for item in window.Document.SelectedItems():
                            item_path = getattr(item, "Path", None)
                            if item_path:
                                selected_items.append(Path(item_path))
                    matching_candidates.append((folder_path, selected_items))
            except Exception as e:
                print("Explorer detection error:", e)

        for folder_path, selected_items in matching_candidates:
            if selected_items:
                return folder_path, selected_items

        if matching_candidates:
            return matching_candidates[0]

        return None, []
    finally:
        pythoncom.CoUninitialize()


def get_target_folder() -> Path | None:
    explorer_folder, _ = get_active_explorer_info()
    return explorer_folder


def require_target_folder() -> Path:
    folder = get_target_folder()
    if folder is None:
        raise RuntimeError("No active Explorer folder detected")
    return folder


def redirect_active_explorer(target_path, hwnd=None):
    """
    Redirects a Windows File Explorer window to the given path.

    Smart Fallback:
    1. If the currently focused window is an Explorer window, it redirects that exact window.
    2. If run from a terminal (or non-Explorer window), it picks the first available open Explorer window.
    3. If no Explorer windows are open, it opens a new Explorer window to the target path.
    """
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
                if window.Document and hasattr(window.Document, "Folder"):
                    explorer_windows.append(window)
                    if w_hwnd == target_hwnd:
                        matching_window = window
            except Exception:
                continue

        # 1. Prioritize matching the active foreground Explorer window (for hotkeys)
        if matching_window:
            matching_window.Navigate(str(target_path))
            return True

        # 2. Fallback: If terminal is foreground, use the first available open Explorer window
        if explorer_windows:
            explorer_windows[0].Navigate(str(target_path))
            return True

        # 3. Ultimate Fallback: If no Explorer windows are open, spawn one
        shell.Open(str(target_path))
        return True

    except Exception as e:
        print("Explorer redirection error:", e)
        return False
    finally:
        pythoncom.CoUninitialize()


def focus_address_bar(target_path: Path) -> bool:
    """
    Focuses the active Explorer window's address bar, populates it with the given path,
    and leaves it ready for user input without triggering immediate navigation or touching the clipboard.
    """
    pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)  # type: ignore[attr-defined]
    try:
        input_val = str(target_path)
        target_path = Path(target_path)
        shell = win32com.client.Dispatch("Shell.Application")
        fg_hwnd = win32gui.GetForegroundWindow()

        matching_window = None
        for window in shell.Windows():
            try:
                if int(window.HWND) == fg_hwnd:
                    matching_window = window
                    break
            except Exception:
                continue

        if not matching_window:
            for window in shell.Windows():
                try:
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

            # Type out the path character by character completely clipboard-free
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
