# file: src/hotkeys/v_alt.py
# description: custom hotkey handler for Alt+V that performs smart paste using engine context data

from __future__ import annotations

from pathlib import Path
import shutil
import sys
import json

def execute_smart_paste() -> None:
    target_dir = None
    
    # Extract target directory from hotkey engine context payload if available
    if len(sys.argv) > 1:
        try:
            context = json.loads(sys.argv[1])
            if context.get("folder_path"):
                target_dir = Path(context["folder_path"])
        except Exception:
            pass

    # Fallback to active Explorer window via COM if context is missing
    if not target_dir or not target_dir.exists():
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            import comtypes.client  # type: ignore
            shell = comtypes.client.CreateObject("Shell.Application")
            hwnd = user32.GetForegroundWindow()
            for window in shell.Windows():
                if window.HWND == hwnd:
                    target_dir = Path(window.Document.Folder.Self.Path)
                    break
        except (ImportError, AttributeError, OSError):
            pass

    if not target_dir or not target_dir.exists():
        print("[!] No active Windows Explorer window detected.")
        return

    # Use standard clipboard file extraction
    import ctypes
    from ctypes import wintypes
    CF_HDROP = 15
    user32 = ctypes.windll.user32
    shell32 = ctypes.windll.shell32
    
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.CloseClipboard.restype = wintypes.BOOL
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = wintypes.HANDLE
    shell32.DragQueryFileW.argtypes = [wintypes.HANDLE, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
    shell32.DragQueryFileW.restype = wintypes.UINT

    if not user32.OpenClipboard(None):
        print("[!] Failed to open clipboard.")
        return

    try:
        h_drop = user32.GetClipboardData(CF_HDROP)
        if not h_drop:
            print("[!] No files found in clipboard.")
            return

        count = shell32.DragQueryFileW(h_drop, 0xFFFFFFFF, None, 0)
        clipboard_files = []
        for i in range(count):
            buf_len = shell32.DragQueryFileW(h_drop, i, None, 0) + 1
            buf = ctypes.create_unicode_buffer(buf_len)
            shell32.DragQueryFileW(h_drop, i, buf, buf_len)
            clipboard_files.append(Path(buf.value))
    finally:
        user32.CloseClipboard()

    if not clipboard_files:
        print("[!] No files found in clipboard payload.")
        return

    target_drive = target_dir.drive.upper()
    processed_count = 0

    for src_file in clipboard_files:
        if not src_file.is_file():
            continue

        target_file = target_dir / src_file.name
        if target_file.exists():
            stem = src_file.stem
            suffix = src_file.suffix
            counter = 1
            while target_file.exists():
                target_file = target_dir / f"{stem} - Copy ({counter}){suffix}"
                counter += 1

        try:
            if src_file.drive.upper() == target_drive:
                target_file.hardlink_to(src_file)
                print(f"[LINK] {src_file.name} -> {target_dir.name}")
            else:
                shutil.copy2(src_file, target_file)
                print(f"[COPY] {src_file.name} -> {target_dir.name}")
            processed_count += 1
        except (OSError, IOError) as e:
            print(f"[ERROR] Failed to process {src_file.name}: {e}")

    if processed_count > 0:
        print(f"[INFO] Smart paste completed successfully in: {target_dir}")


if __name__ == "__main__":
    execute_smart_paste()