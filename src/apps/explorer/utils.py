# file: src/apps/explorer/utils.py

import os
import sys

import win32api
import win32con
import win32gui

_DEBUG = bool(os.environ.get("BITU_EXPLORER_DEBUG"))

# Windows 11 is build 22000+. This package targets Win11's tabbed Explorer
# specifically (see active_tab.py) and is not expected to work correctly
# on Windows 10 or earlier.
_MIN_WIN11_BUILD = 22000
_warned_unsupported_os = False


def _dbg(msg: str) -> None:
    if _DEBUG:
        print(f"[explorer DEBUG] {msg}")


def is_win11() -> bool:
    """Best-effort check that we're running on Windows 11 (build 22000+)."""
    try:
        return sys.getwindowsversion().build >= _MIN_WIN11_BUILD
    except Exception:
        return False


def warn_if_unsupported_os() -> None:
    """Log a one-time warning if this doesn't look like Windows 11.

    This package (src/apps/explorer) targets Windows 11's tabbed File
    Explorer specifically. It is not designed to support Windows 10 or
    other platforms -- contributions for those are welcome but out of
    scope here.
    """
    global _warned_unsupported_os
    if _warned_unsupported_os or is_win11():
        return
    _warned_unsupported_os = True
    print(
        "[explorer] WARNING: this module targets Windows 11's tabbed File "
        "Explorer; active-tab detection is not expected to work correctly "
        "on this OS/build.",
        file=sys.stderr,
    )


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