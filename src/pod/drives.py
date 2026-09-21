# file: src/pod/drives.py
# description: drive enumeration for BITU. Config loading/validation lives in
# pod/config.py -- this module is purely "which drives exist" and "which of
# them are opted in", re-exporting load_drive_config for callers that only
# need a drive's config rather than the full enumeration.

from __future__ import annotations

import ctypes
import string
import sys
from pathlib import Path

from .config import load_drive_config

__all__ = [
    "enumerate_drive_roots",
    "load_drive_config",
    "find_bitu_drives",
    "get_volume_label",
    "find_drive_by_label",
]


def enumerate_drive_roots() -> list[Path]:
    """Return all currently mounted drive roots. Windows only."""
    if sys.platform != "win32":
        return []

    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    roots = []
    for i, letter in enumerate(string.ascii_uppercase):
        if bitmask & (1 << i):
            roots.append(Path(f"{letter}:\\"))
    return roots


def get_volume_label(drive_root: Path) -> str | None:
    """The drive's volume label (e.g. "backup", "bitu_test_drive"), or None if
    it can't be read (unready media, no label set, etc).
    """
    if sys.platform != "win32":
        return None

    kernel32 = ctypes.windll.kernel32
    vol_name_buf = ctypes.create_unicode_buffer(1024)
    fs_name_buf = ctypes.create_unicode_buffer(1024)
    serial = ctypes.c_uint(0)
    max_len = ctypes.c_uint(0)
    flags = ctypes.c_uint(0)
    ok = kernel32.GetVolumeInformationW(
        ctypes.c_wchar_p(str(drive_root)),
        vol_name_buf, ctypes.sizeof(vol_name_buf),
        ctypes.byref(serial), ctypes.byref(max_len), ctypes.byref(flags),
        fs_name_buf, ctypes.sizeof(fs_name_buf),
    )
    if not ok:
        return None
    return vol_name_buf.value or None


def find_drive_by_label(label: str) -> Path | None:
    """Return the root of the first currently mounted drive whose volume label
    matches `label` (case-insensitive), or None if no such drive is mounted.
    """
    target = label.strip().lower()
    for root in enumerate_drive_roots():
        vol_label = get_volume_label(root)
        if vol_label and vol_label.strip().lower() == target:
            return root
    return None


def find_bitu_drives() -> list[tuple[Path, dict]]:
    """Return (drive_root, config) for every currently mounted drive that has
    a valid BITU config -- i.e. every drive that should get a dedupe/file_server
    pair spawned."""
    result = []
    for root in enumerate_drive_roots():
        config = load_drive_config(root)
        if config:
            result.append((root, config))
    return result
