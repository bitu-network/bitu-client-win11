# file: src/apps/explorer/query.py

from pathlib import Path
import queue
import threading
from urllib.parse import unquote, urlparse

import pythoncom
import win32com.client
import win32gui
import win32con

from .active_tab import detect_active_tab
from .utils import _is_mouse_down, _is_hwnd_responsive, _dbg


def _paths_equal(a: Path, b: Path) -> bool:
    """Case-insensitive path comparison (Windows paths are case-insensitive)."""
    try:
        return str(a).rstrip("\\/").lower() == str(b).rstrip("\\/").lower()
    except Exception:
        return False


def _query_explorer_com(require_focus: bool, result_queue: queue.Queue):
    if _is_mouse_down():
        result_queue.put((None, []))
        return

    pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)  # type: ignore[attr-defined]
    try:
        fg_hwnd = win32gui.GetForegroundWindow()
        root_fg_hwnd = win32gui.GetAncestor(fg_hwnd, win32con.GA_ROOT) if fg_hwnd else 0

        if root_fg_hwnd and win32gui.GetClassName(root_fg_hwnd) in ("CabinetWClass", "ExploreWClass"):
            if _is_mouse_down() or not _is_hwnd_responsive(root_fg_hwnd):
                result_queue.put((None, []))
                return

        target_hwnd = root_fg_hwnd if root_fg_hwnd else fg_hwnd
        folder_path = None
        selected_items = []

        active_tab_name, active_tab_path = detect_active_tab(target_hwnd)

        shell = win32com.client.Dispatch("Shell.Application")
        matching_window = None
        fallback_window = None  # first responsive candidate, used only if matching can't resolve one

        for window in shell.Windows():
            try:
                if _is_mouse_down():
                    break

                w_hwnd = int(window.HWND)
                w_root = win32gui.GetAncestor(w_hwnd, win32con.GA_ROOT) if w_hwnd else 0

                if not _is_hwnd_responsive(w_hwnd):
                    continue

                if not require_focus or w_hwnd == fg_hwnd or (root_fg_hwnd and w_root == root_fg_hwnd):
                    win_path = None
                    if window.LocationURL:
                        parsed = urlparse(window.LocationURL)
                        if parsed.scheme == "file":
                            win_path = Path(unquote(parsed.path)).resolve()

                    win_title = None
                    try:
                        if window.Document and hasattr(window.Document, "Folder") and window.Document.Folder:
                            win_title = window.Document.Folder.Title
                    except Exception:
                        pass

                    _dbg(f"candidate w_hwnd={w_hwnd} w_root={w_root} LocationURL={window.LocationURL!r} "
                         f"win_path={win_path} win_title={win_title!r}")

                    if active_tab_name and win_title and win_title.strip().lower() == active_tab_name.strip().lower():
                        matching_window = window
                        break

                    if active_tab_path and win_path and _paths_equal(win_path, active_tab_path):
                        matching_window = window
                        break

                    if fallback_window is None:
                        fallback_window = window
            except Exception as e:
                print("Explorer detection error:", e)

        if not matching_window and fallback_window is not None:
            if active_tab_name or active_tab_path:
                _dbg("active tab identified but no candidate window matched it by name or path; "
                     "falling back to first responsive window (this is the bug if it fires)")
            matching_window = fallback_window

        if matching_window:
            try:
                loc_url = getattr(matching_window, "LocationURL", None)
                if loc_url:
                    parsed = urlparse(loc_url)
                    if parsed.scheme == "file":
                        path_str = unquote(parsed.path)
                        if path_str.startswith("/") and len(path_str) > 2 and path_str[2] == ":":
                            path_str = path_str[1:]
                        folder_path = Path(path_str)

                if matching_window.Document and hasattr(matching_window.Document, "SelectedItems"):
                    items = matching_window.Document.SelectedItems()
                    if items is not None:
                        for item in items:
                            item_path = getattr(item, "Path", None)
                            if item_path:
                                selected_items.append(Path(item_path))
            except Exception as e:
                print("Explorer window details error:", e)

        if not folder_path and matching_window:
            try:
                if matching_window.Document and hasattr(matching_window.Document, "Folder"):
                    folder_path = Path(matching_window.Document.Folder.Self.Path)
            except Exception:
                pass

        result_queue.put((folder_path, selected_items))
    except Exception as e:
        print("Explorer COM lookup error:", e)
        result_queue.put((None, []))
    finally:
        pythoncom.CoUninitialize()


def get_active_explorer_info(require_focus: bool = True) -> tuple[Path | None, list[Path]]:
    if _is_mouse_down():
        return (None, [])

    result_q: queue.Queue = queue.Queue()
    t = threading.Thread(target=_query_explorer_com, args=(require_focus, result_q,), daemon=True)
    t.start()
    t.join()

    try:
        return result_q.get_nowait()
    except queue.Empty:
        return (None, [])


def get_target_folder() -> Path | None:
    explorer_folder, _ = get_active_explorer_info()
    return explorer_folder


def require_target_folder() -> Path:
    folder = get_target_folder()
    if folder is None:
        raise RuntimeError("No active Explorer folder detected")
    return folder
