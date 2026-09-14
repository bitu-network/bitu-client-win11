# file: src/apps/explorer/query.py

from pathlib import Path
import queue
import re
import threading
from urllib.parse import unquote, urlparse

import os

import pythoncom
import win32com.client
import win32gui
import win32con

from .utils import _is_mouse_down, _is_hwnd_responsive

_DEBUG = bool(os.environ.get("BITU_EXPLORER_DEBUG"))


def _dbg(msg: str) -> None:
    if _DEBUG:
        print(f"[explorer.query DEBUG] {msg}")


def _paths_equal(a: Path, b: Path) -> bool:
    """Case-insensitive path comparison (Windows paths are case-insensitive)."""
    try:
        return str(a).rstrip("\\/").lower() == str(b).rstrip("\\/").lower()
    except Exception:
        return False


def _reconstruct_path_from_segments(names: list[str]) -> Path | None:
    drive_idx = -1
    drive_letter = None
    for idx, name in enumerate(names):
        match = re.search(r"\(([A-Za-z]):\)", name)
        if match:
            drive_letter = match.group(1).upper()
            drive_idx = idx
            break
        elif re.match(r"^[A-Za-z]:$", name):
            drive_letter = name[0].upper()
            drive_idx = idx
            break

    if drive_letter is None or drive_idx == -1:
        return None

    current_path = Path(f"{drive_letter}:\\")
    for name in names[drive_idx + 1:]:
        if not name or name in (">", "Search", "Address"):
            continue
        current_path = current_path / name

    if current_path.is_dir():
        return current_path.resolve()

    temp_path = current_path
    while temp_path != temp_path.parent:
        if temp_path.is_dir():
            return temp_path.resolve()
        temp_path = temp_path.parent

    return None


def _parse_active_tab_name_from_title(title: str | None) -> str | None:
    """Extract the active tab's display name from a Windows 11 Explorer window title.

    Win11's tabbed Explorer sets the window title to "<active tab> - File Explorer"
    (single tab) or "<active tab> and N more tabs - File Explorer" (multiple tabs).
    Parsing this avoids fragile UIA subtree walks entirely.
    """
    if not title:
        return None
    match = re.match(r"^(.*?)(?:\s+and\s+\d+\s+more\s+tabs?)?\s+-\s+File Explorer$", title)
    if match:
        name = match.group(1).strip()
        if name:
            return name
    return None


def _get_active_tab_name(uia, element) -> str | None:
    """Find the selected TabItem's display name (the folder name shown on the tab)."""
    try:
        tabitem_cond = uia.CreatePropertyCondition(30003, 50019)  # ControlType_TabItem
        tab_items = element.FindAll(3, tabitem_cond)  # TreeScope_Subtree
        if tab_items:
            for i in range(tab_items.Length):
                item = tab_items.GetElement(i)
                try:
                    sel_pattern = item.GetCurrentPattern(10010)  # SelectionItemPatternId
                    if sel_pattern and sel_pattern.CurrentIsSelected:
                        name = item.CurrentName
                        if name:
                            return name
                except Exception:
                    continue
    except Exception:
        pass
    return None


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

        active_tab_path = None
        active_tab_name = None

        # 0. Cheapest and most reliable: Win11 encodes the active tab's name directly
        #    in the window title ("<name> and N more tabs - File Explorer").
        if target_hwnd:
            title_text = win32gui.GetWindowText(target_hwnd)
            active_tab_name = _parse_active_tab_name_from_title(title_text)
            _dbg(f"window title={title_text!r} parsed active_tab_name={active_tab_name!r}")

        if target_hwnd:
            try:
                uia = win32com.client.Dispatch("UIAutomationClient.CUIAutomation")
                element = uia.ElementFromHandle(target_hwnd)
                if element:
                    # 1. Only needed if the title didn't already give us a name (e.g. older
                    #    Explorer without tabs, or an unexpected title format).
                    if not active_tab_name:
                        active_tab_name = _get_active_tab_name(uia, element)

                    # 1. Try finding Edit control (Edit mode)
                    cond = uia.CreatePropertyCondition(30003, 50004)  # UIA_ControlTypePropertyId, ControlType_Edit
                    edit_elements = element.FindAll(3, cond)  # TreeScope_Subtree
                    if edit_elements:
                        for i in range(edit_elements.Length):
                            edit_el = edit_elements.GetElement(i)
                            try:
                                val_pattern = edit_el.GetCurrentPattern(10002)  # UIA_ValuePatternId
                                if val_pattern:
                                    val = val_pattern.CurrentValue
                                    if val:
                                        p = Path(val)
                                        if p.is_dir():
                                            active_tab_path = p.resolve()
                                            break
                            except Exception:
                                pass

                    # 2. Fallback: Parse breadcrumb buttons if Edit control not found/valid
                    if not active_tab_path:
                        btn_cond = uia.CreatePropertyCondition(30003, 50000)  # ControlType_Button
                        buttons = element.FindAll(3, btn_cond)
                        if buttons:
                            segment_names = []
                            for i in range(buttons.Length):
                                btn = buttons.GetElement(i)
                                try:
                                    name = btn.CurrentName
                                    if name:
                                        segment_names.append(name)
                                except Exception:
                                    pass
                            active_tab_path = _reconstruct_path_from_segments(segment_names)
            except Exception:
                pass

        _dbg(f"target_hwnd={target_hwnd} root_fg_hwnd={root_fg_hwnd} "
             f"active_tab_name={active_tab_name!r} active_tab_path={active_tab_path}")

        shell = win32com.client.Dispatch("Shell.Application")
        matching_window = None
        fallback_window = None  # first responsive candidate, used only if path-matching can't resolve one

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