# file: src/hotkeys/v_ctrl_alt_shift.py

import ctypes
from ctypes import wintypes

VK_V = 0x56
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt
KEYEVENTF_KEYUP = 0x0002

user32 = ctypes.windll.user32
user32.keybd_event.argtypes = [
    wintypes.BYTE,
    wintypes.BYTE,
    wintypes.DWORD,
    ctypes.c_ulonglong,
]
user32.keybd_event.restype = None


def send_native_paste():
    """Forces physical Ctrl+V keypress to perform a standard Windows paste/duplicate."""
    # Release Alt and Shift so Windows interprets this purely as Ctrl+V
    user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0)
    
    user32.keybd_event(VK_V, 0, 0, 0)
    user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)


if __name__ == "__main__":
    send_native_paste()