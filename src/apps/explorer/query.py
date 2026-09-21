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
    _dbg(f"query: start require_focus={require_focus}")

    if _is_mouse_down():
        _dbg("query: mouse down at start -> returning (None, [])")
        result_queue.put((None, []))
        return

    pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)  # type: ignore[attr-defined]
    try:
        fg_hwnd = win32gui.GetForegroundWindow()
        root_fg_hwnd = win32gui.GetAncestor(fg_hwnd, win32con.GA_ROOT) if fg_hwnd else 0
        _dbg(f"query: fg_hwnd={fg_hwnd} root_fg_hwnd={root_fg_hwnd}")

        if root_fg_hwnd and win32gui.GetClassName(root_fg_hwnd) in ("CabinetWClass", "ExploreWClass"):
            if _is_mouse_down():
                _dbg("query: mouse down before responsiveness check -> returning (None, [])")
                result_queue.put((None, []))
                return
            if not _is_hwnd_responsive(root_fg_hwnd):
                _dbg(f"query: root_fg_hwnd={root_fg_hwnd} unresponsive -> returning (None, [])")
                result_queue.put((None, []))
                return

        target_hwnd = root_fg_hwnd if root_fg_hwnd else fg_hwnd
        folder_path = None
        selected_items = []

        active_tab_name, active_tab_path = detect_active_tab(target_hwnd)

        shell = win32com.client.Dispatch("Shell.Application")
        matching_window = None
        fallback_window = None  # first responsive candidate, used only if matching can't resolve one

        try:
            _dbg(f"query: shell.Windows() count={shell.Windows().Count}")
        except Exception as e:
            _dbg(f"query: could not read shell.Windows() count: {e!r}")

        seen = 0
        for window in shell.Windows():
            seen += 1
            try:
                if _is_mouse_down():
                    _dbg("loop: mouse down -> break")
                    break

                w_hwnd = int(window.HWND)
                w_root = win32gui.GetAncestor(w_hwnd, win32con.GA_ROOT) if w_hwnd else 0

                if not _is_hwnd_responsive(w_hwnd):
                    _dbg(f"loop: w_hwnd={w_hwnd} unresponsive -> skip")
                    continue

                focus_ok = (
                    not require_focus
                    or w_hwnd == fg_hwnd
                    or (root_fg_hwnd and w_root == root_fg_hwnd)
                )
                if not focus_ok:
                    _dbg(f"loop: w_hwnd={w_hwnd} w_root={w_root} not foreground "
                         f"({fg_hwnd}/{root_fg_hwnd}) -> skip")
                    continue

                win_path = None
                if window.LocationURL:
                    parsed = urlparse(window.LocationURL)
                    if parsed.scheme == "file":
                        win_path = Path(unquote(parsed.path)).resolve()

                win_title = None
                try:
                    if window.Document and hasattr(window.Document, "Folder") and window.Document.Folder:
                        win_title = window.Document.Folder.Title
                except Exception as e:
                    _dbg(f"loop: w_hwnd={w_hwnd} could not read Document.Folder.Title: {e!r}")

                _dbg(f"candidate w_hwnd={w_hwnd} w_root={w_root} LocationURL={window.LocationURL!r} "
                     f"win_path={win_path} win_title={win_title!r}")

                if active_tab_name and win_title and win_title.strip().lower() == active_tab_name.strip().lower():
                    _dbg(f"loop: matched by tab name w_hwnd={w_hwnd}")
                    matching_window = window
                    break

                if active_tab_path and win_path and _paths_equal(win_path, active_tab_path):
                    _dbg(f"loop: matched by tab path w_hwnd={w_hwnd}")
                    matching_window = window
                    break

                if fallback_window is None:
                    fallback_window = window
            except Exception as e:
                print("Explorer detection error:", e)
                _dbg(f"loop: exception {e!r}")

        _dbg(f"loop done: seen={seen} matching={matching_window is not None} "
             f"fallback={fallback_window is not None}")

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
                _dbg(f"details: exception {e!r}")
        else:
            _dbg("query: no matching window -> folder_path/selected_items stay empty")

        if not folder_path and matching_window:
            try:
                if matching_window.Document and hasattr(matching_window.Document, "Folder"):
                    folder_path = Path(matching_window.Document.Folder.Self.Path)
            except Exception as e:
                _dbg(f"details: Folder.Self.Path fallback failed: {e!r}")

        _dbg(f"query: result folder_path={folder_path} selected_count={len(selected_items)}")
        result_queue.put((folder_path, selected_items))
    except Exception as e:
        print("Explorer COM lookup error:", e)
        _dbg(f"query: outer exception {e!r}")
        result_queue.put((None, []))
    finally:
        pythoncom.CoUninitialize()


def get_active_explorer_info(require_focus: bool = True) -> tuple[Path | None, list[Path]]:
    if _is_mouse_down():
        _dbg("get_active_explorer_info: mouse down -> returning (None, [])")
        return (None, [])

    result_q: queue.Queue = queue.Queue()
    t = threading.Thread(target=_query_explorer_com, args=(require_focus, result_q,), daemon=True)
    t.start()
    t.join()

    try:
        return result_q.get_nowait()
    except queue.Empty:
        _dbg("get_active_explorer_info: worker produced no result")
        return (None, [])


def get_target_folder() -> Path | None:
    explorer_folder, _ = get_active_explorer_info()
    return explorer_folder


def require_target_folder() -> Path:
    folder = get_target_folder()
    if folder is None:
        raise RuntimeError("No active Explorer folder detected")
    return folder
