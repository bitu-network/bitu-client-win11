# file: src/cli/inode.py
# description: native python command-line tool to query NTFS file IDs (inodes) for selected explorer files or all files in the active directory

from __future__ import annotations

import ctypes
from pathlib import Path
import sys

import pythoncom
import win32con
import win32file

from apps.explorer import get_active_explorer_info


def enable_vt_mode() -> None:
    """Enables Virtual Terminal Processing (ANSI escape sequence support) for Windows CMD/PowerShell."""
    if sys.platform != "win32":
        return
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except (AttributeError, OSError, ValueError):
        pass


def get_file_id(file_path: Path) -> int | None:
    """Retrieve the NTFS File ID (inode) of a file using Win32 CreateFile and GetFileInformationByHandleEx."""
    try:
        h_file = win32file.CreateFile(
            str(file_path),
            win32con.GENERIC_READ,
            win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE,
            None,
            win32con.OPEN_EXISTING,
            win32con.FILE_FLAG_BACKUP_SEMANTICS,
            None,
        )
    except OSError:
        return None

    if h_file == win32file.INVALID_HANDLE_VALUE:
        return None

    try:
        class FILE_ID_INFO(ctypes.Structure):
            _fields_ = [("VolumeSerialNumber", ctypes.c_ulonglong), ("FileId", ctypes.c_ubyte * 16)]

        file_id_info = FILE_ID_INFO()
        success = ctypes.windll.kernel32.GetFileInformationByHandleEx(
            int(h_file),
            18,  # FileIdInfo
            ctypes.byref(file_id_info),
            ctypes.sizeof(file_id_info),
        )
        if not success:
            return None

        file_id_int = int.from_bytes(bytes(file_id_info.FileId), byteorder="little")
        return file_id_int
    except (OSError, RuntimeError):
        return None
    finally:
        h_file.Close()


def main() -> None:
    enable_vt_mode()

    pythoncom.CoInitialize()
    try:
        folder_path, selected_items = get_active_explorer_info(require_focus=False)
    except (OSError, RuntimeError) as e:
        print(f"[ERROR] Failed to query Explorer context: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        pythoncom.CoUninitialize()

    if not folder_path or not folder_path.exists():
        folder_path = Path.cwd()
        selected_items = []

    if not folder_path or not folder_path.exists():
        print("[!] No valid target directory detected.", file=sys.stderr)
        sys.exit(1)

    targets = selected_items if selected_items else [p for p in folder_path.iterdir() if p.is_file()]

    if not targets:
        print(f"[!] No files found in: {folder_path}")
        return

    print(f"\n\033[95m=== NTFS INODES: {folder_path.name} ===\033[0m")
    for file_path in targets:
        if not file_path.is_file():
            continue
        inode = get_file_id(file_path)
        if inode is not None:
            print(f"  \033[93m0x{inode:032x}\033[0m  {file_path.name}")
        else:
            print(f"  \033[91m[ERROR]\033[0m  {file_path.name}")
    print("\033[95m=====================================\033[0m\n")


if __name__ == "__main__":
    main()