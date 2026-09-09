# file: src/hotkeys/v_alt.py

import os
import ctypes
from ctypes import wintypes
from pathlib import Path
from lib.hotkey_context import get_context_fields

CF_HDROP = 15

user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32

user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL
user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = wintypes.BOOL
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.GetClipboardData.restype = wintypes.HANDLE

shell32.DragQueryFileW.argtypes = [wintypes.HANDLE, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
shell32.DragQueryFileW.restype = wintypes.UINT

def get_clipboard_file_paths():
    """Retrieves a list of file paths from the Windows clipboard (CF_HDROP format)."""
    file_paths = []
    if not user32.OpenClipboard(None):
        return file_paths
    try:
        h_mem = user32.GetClipboardData(CF_HDROP)
        if h_mem:
            count = shell32.DragQueryFileW(h_mem, 0xFFFFFFFF, None, 0)
            for i in range(count):
                buf_size = shell32.DragQueryFileW(h_mem, i, None, 0) + 1
                buffer = ctypes.create_unicode_buffer(buf_size)
                shell32.DragQueryFileW(h_mem, i, buffer, buf_size)
                if buffer.value:
                    file_paths.append(Path(buffer.value))
    finally:
        user32.CloseClipboard()
    return file_paths

def paste_hard_links():
    application, folder_path, _ = get_context_fields(
        "application",
        "folder_path",
        "selected_items",
    )

    if application != "explorer.exe" or not folder_path:
        return

    target_dir = Path(folder_path)
    if not target_dir.exists() or not target_dir.is_dir():
        return

    clipboard_files = get_clipboard_file_paths()
    if not clipboard_files:
        return

    for src_file in clipboard_files:
        if not src_file.exists() or not src_file.is_file():
            continue

        dest_file = target_dir / src_file.name
        
        # Handle filename collisions gracefully
        counter = 1
        original_dest = dest_file
        while dest_file.exists():
            dest_file = original_dest.with_stem(f"{original_dest.stem}_{counter}")
            counter += 1

        try:
            os.link(src_file, dest_file)
        except OSError:
            pass  # Failsafe for cross-device or permission errors

paste_hard_links()