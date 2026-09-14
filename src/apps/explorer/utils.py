# file: src/apps/explorer/utils.py

import win32api
import win32con
import win32gui


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