# file: src/apps/explorer/active_tab.py
# description: Windows 11 tabbed-Explorer active-tab detection.
#
# This is the volatile half of active-explorer detection: it depends on the
# window title format and UIA control tree of Windows 11's File Explorer,
# both of which have changed across builds and may change again. Keeping it
# isolated from query.py means a future Explorer update should only require
# changes here, not to the shell.Windows() orchestration logic.
#
# Windows-11-only by design. Not intended to support Windows 10 or earlier.

from __future__ import annotations

from pathlib import Path
import re

import win32com.client
import win32gui

from .utils import _dbg, warn_if_unsupported_os


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


def _get_active_tab_name_via_uia(uia, element) -> str | None:
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


def _get_active_tab_path_via_uia(uia, element) -> Path | None:
    """Try the address-bar Edit control first, then fall back to breadcrumb buttons."""
    active_tab_path = None

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

    return active_tab_path


def detect_active_tab(target_hwnd: int) -> tuple[str | None, Path | None]:
    """Best-effort detection of the active tab's display name and/or folder path
    for a Win11 tabbed Explorer window.

    Returns (active_tab_name, active_tab_path). Either or both may be None if
    detection fails -- callers should treat this as advisory, not authoritative.
    """
    warn_if_unsupported_os()

    active_tab_name = None
    active_tab_path = None

    if not target_hwnd:
        return (None, None)

    # 0. Cheapest and most reliable: Win11 encodes the active tab's name directly
    #    in the window title ("<name> and N more tabs - File Explorer").
    title_text = win32gui.GetWindowText(target_hwnd)
    active_tab_name = _parse_active_tab_name_from_title(title_text)
    _dbg(f"window title={title_text!r} parsed active_tab_name={active_tab_name!r}")

    try:
        uia = win32com.client.Dispatch("UIAutomationClient.CUIAutomation")
        element = uia.ElementFromHandle(target_hwnd)
        if element:
            # Only needed if the title didn't already give us a name (e.g. an
            # unexpected title format).
            if not active_tab_name:
                active_tab_name = _get_active_tab_name_via_uia(uia, element)

            active_tab_path = _get_active_tab_path_via_uia(uia, element)
    except Exception:
        pass

    _dbg(f"target_hwnd={target_hwnd} active_tab_name={active_tab_name!r} active_tab_path={active_tab_path}")
    return (active_tab_name, active_tab_path)
