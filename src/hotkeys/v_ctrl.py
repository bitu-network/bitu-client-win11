# file: src/hotkeys/v_ctrl.py

import sys
import json
import time
import ctypes
from ctypes import wintypes
from pathlib import Path

# --- Win32 Definitions ---
CF_HDROP = 15
VK_CONTROL = 0x11
VK_V = 0x56
KEYEVENTF_KEYUP = 0x0002
DROPEFFECT_MOVE = 0x02

user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32
kernel32 = ctypes.windll.kernel32

user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL
user32.CloseClipboard.restype = wintypes.BOOL
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.GetClipboardData.restype = wintypes.HANDLE
user32.RegisterClipboardFormatW.argtypes = [wintypes.LPCWSTR]
user32.RegisterClipboardFormatW.restype = wintypes.UINT
user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_ulonglong]
user32.keybd_event.restype = None

shell32.DragQueryFileW.argtypes = [wintypes.HANDLE, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
shell32.DragQueryFileW.restype = wintypes.UINT

kernel32.GlobalLock.argtypes = [wintypes.HANDLE]
kernel32.GlobalLock.restype = wintypes.LPVOID
kernel32.GlobalUnlock.argtypes = [wintypes.HANDLE]
kernel32.GlobalUnlock.restype = wintypes.BOOL


def is_cut_operation() -> bool:
    """Check if the current clipboard payload represents a 'Cut' (Move) operation."""
    cf_preferred_dropeffect = user32.RegisterClipboardFormatW("Preferred DropEffect")
    if not cf_preferred_dropeffect:
        return False

    if not user32.OpenClipboard(None):
        return False

    try:
        h_mem = user32.GetClipboardData(cf_preferred_dropeffect)
        if not h_mem:
            return False

        p_mem = kernel32.GlobalLock(h_mem)
        if not p_mem:
            return False

        try:
            effect = ctypes.cast(p_mem, ctypes.POINTER(wintypes.DWORD)).contents.value
            return bool(effect & DROPEFFECT_MOVE)
        finally:
            kernel32.GlobalUnlock(h_mem)
    finally:
        user32.CloseClipboard()


def get_clipboard_files() -> list[Path]:
    """Extract file paths from HDROP clipboard payload."""
    if not user32.OpenClipboard(None):
        return []

    try:
        h_drop = user32.GetClipboardData(CF_HDROP)
        if not h_drop:
            return []

        count = shell32.DragQueryFileW(h_drop, 0xFFFFFFFF, None, 0)
        files = []
        for i in range(count):
            buf_len = shell32.DragQueryFileW(h_drop, i, None, 0) + 1
            buf = ctypes.create_unicode_buffer(buf_len)
            shell32.DragQueryFileW(h_drop, i, buf, buf_len)
            files.append(Path(buf.value))
        return files
    finally:
        user32.CloseClipboard()


def pass_through_native_paste():
    """Synthesizes Ctrl+V keyup/keydown event for non-file/fallback clipboard pastes."""
    time.sleep(0.05)  # Brief delay to allow hotkey release state to settle
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(VK_V, 0, 0, 0)
    user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)


def paste_hard_links():
    if len(sys.argv) < 2:
        pass_through_native_paste()
        return

    try:
        context_data = json.loads(sys.argv[1])
    except Exception:
        pass_through_native_paste()
        return

    application = context_data.get("application")
    folder_path_str = context_data.get("folder_path")

    # If active window is not Explorer or no valid folder path is active, pass-through
    if application != "explorer.exe" or not folder_path_str:
        pass_through_native_paste()
        return

    target_dir = Path(folder_path_str)
    if not target_dir.exists():
        pass_through_native_paste()
        return

    # Pass through if the clipboard action is a Cut / Move
    if is_cut_operation():
        pass_through_native_paste()
        return

    clipboard_files = get_clipboard_files()

    # Fall back to standard paste if clipboard contains non-file data (e.g. text/image)
    if not clipboard_files:
        pass_through_native_paste()
        return

    target_drive = target_dir.drive.upper()

    # Fall back to native paste if sources reside on a different drive or partition
    if any(src_file.drive.upper() != target_drive for src_file in clipboard_files):
        pass_through_native_paste()
        return

    # Process local NTFS hard linking directly
    for src_file in clipboard_files:
        if not src_file.is_file():
            continue

        target_file = target_dir / src_file.name

        if target_file.exists():
            stem = src_file.stem
            suffix = src_file.suffix
            counter = 1
            while target_file.exists():
                target_file = target_dir / f"{stem} - Hardlink ({counter}){suffix}"
                counter += 1

        try:
            target_file.hardlink_to(src_file)
        except OSError as e:
            print(f"[ERROR] Hard link creation failed: {e}", file=sys.stderr)


if __name__ == "__main__":
    paste_hard_links()