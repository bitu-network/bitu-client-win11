# file: src/apps/explorer.py
from pathlib import Path
import queue
import threading
import time

import pythoncom
import win32api
import win32com.client
import win32con
import win32gui

_LAST_EXPLORER_CACHE: tuple[Path | None, list[Path]] = (None, [])


def _is_mouse_down() -> bool:
    """Returns True if the left or right mouse button is currently held down.

    Detects active drag-and-drop operations at the OS level before COM queries can hang.
    """
    return bool(
        (win32api.GetAsyncKeyState(win32con.VK_LBUTTON) & 0x8000)
        or (win32api.GetAsyncKeyState(win32con.VK_RBUTTON) & 0x8000)
    )


def _is_hwnd_responsive(hwnd: int) -> bool:
    """Probes a window handle via Win32 kernel message with SMTO_ABORTIFHUNG.

    Fails instantly (<10ms) if the window is unresponsive or in a modal OLE drag loop.
    """
    if not hwnd or not win32gui.IsWindow(hwnd):
        return False
    res, _ = win32gui.SendMessageTimeout(
        hwnd,
        win32con.WM_NULL,
        0,
        0,
        win32con.SMTO_ABORTIFHUNG,
        10,
    )
    return res != 0


def _query_explorer_com(require_focus: bool, result_queue: queue.Queue):
    global _LAST_EXPLORER_CACHE
    if _is_mouse_down():
        result_queue.put(_LAST_EXPLORER_CACHE if not require_focus else (None, []))
        return

    pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)  # type: ignore[attr-defined]
    try:
        fg_hwnd = win32gui.GetForegroundWindow()
        root_fg_hwnd = win32gui.GetAncestor(fg_hwnd, win32con.GA_ROOT) if fg_hwnd else 0

        if root_fg_hwnd and win32gui.GetClassName(root_fg_hwnd) in ("CabinetWClass", "ExploreWClass"):
            if _is_mouse_down() or not _is_hwnd_responsive(root_fg_hwnd):
                result_queue.put(_LAST_EXPLORER_CACHE if not require_focus else (None, []))
                return

        # Build Z-order lookup list from top to bottom
        z_order = []
        win32gui.EnumWindows(lambda hwnd, extra: z_order.append(hwnd), None)

        def get_z_index(hwnd: int) -> int:
            try:
                return z_order.index(hwnd)
            except ValueError:
                return 999999

        shell = win32com.client.Dispatch("Shell.Application")
        matching_candidates = []

        for window in shell.Windows():
            try:
                if _is_mouse_down():
                    break

                w_hwnd = int(window.HWND)
                w_root = win32gui.GetAncestor(w_hwnd, win32con.GA_ROOT) if w_hwnd else 0

                if not _is_hwnd_responsive(w_hwnd):
                    continue

                if not require_focus or w_hwnd == fg_hwnd or (root_fg_hwnd and w_root == root_fg_hwnd):
                    folder_path = (
                        Path(window.Document.Folder.Self.Path)
                        if window.Document and hasattr(window.Document, "Folder")
                        else None
                    )
                    selected_items = []
                    if window.Document and hasattr(window.Document, "SelectedItems"):
                        try:
                            items = window.Document.SelectedItems()
                            if items is not None:
                                for item in items:
                                    item_path = getattr(item, "Path", None)
                                    if item_path:
                                        selected_items.append(Path(item_path))
                        except Exception:
                            pass

                    z_idx = get_z_index(w_hwnd)
                    matching_candidates.append((z_idx, folder_path, selected_items))
            except Exception as e:
                print("Explorer detection error:", e)

        # Sort candidates by Z-index (lower index = closer to the top of visual Z-order)
        matching_candidates.sort(key=lambda x: x[0])

        if matching_candidates:
            # Always respect the topmost window in Z-order first
            _, folder_path, selected_items = matching_candidates[0]
            _LAST_EXPLORER_CACHE = (folder_path, selected_items)
            result_queue.put((folder_path, selected_items))
            return

        if not require_focus and _LAST_EXPLORER_CACHE[0] is not None:
            result_queue.put(_LAST_EXPLORER_CACHE)
            return

        result_queue.put((None, []))
    except Exception as e:
        print("Explorer COM lookup error:", e)
        result_queue.put(_LAST_EXPLORER_CACHE if not require_focus else (None, []))
    finally:
        pythoncom.CoUninitialize()


def get_active_explorer_info(require_focus: bool = True) -> tuple[Path | None, list[Path]]:
    if _is_mouse_down():
        return _LAST_EXPLORER_CACHE if not require_focus else (None, [])

    result_q: queue.Queue = queue.Queue()
    t = threading.Thread(target=_query_explorer_com, args=(require_focus, result_q,), daemon=True)
    t.start()
    t.join()

    try:
        return result_q.get_nowait()
    except queue.Empty:
        return _LAST_EXPLORER_CACHE if not require_focus else (None, [])


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