# file: src/pod/drives.py
# description: volume enumeration for BITU. Config loading/validation lives in
# pod/config.py -- this module is purely "which volumes exist" and "which of
# them are opted in", re-exporting load_drive_config for callers that only
# need a drive's config rather than the full enumeration.
#
# A volume is mounted either at a drive letter ("D:\") or nested in a folder
# of another volume ("D:\pod_1" -- e.g. the pods created by cli/pod/partition.py,
# which keep My Computer down to one icon per physical disk). Both count the
# same: a volume is a pod if it has a valid BITU config (see find_bitu_drives).
# A volume that has a drive letter is always represented by that letter, so it
# never shows up twice.
#
# Nested pods are found by looking for folder mounts directly under each local
# drive's root (where cli/pod/partition.py puts them) using the very same
# os.path.ismount() test that pod.paths.pod_root() uses, so enumeration and
# path -> pod lookup always agree on what counts as a mount point.

from __future__ import annotations

import ctypes
import os
import stat
import string
import sys
from pathlib import Path
from typing import Callable

from .config import load_drive_config

__all__ = [
    "enumerate_drive_roots",
    "load_drive_config",
    "find_bitu_drives",
    "get_volume_label",
    "find_drive_by_label",
]

_DRIVE_REMOVABLE = 2
_DRIVE_FIXED = 3


def _letter_roots() -> list[Path]:
    """Every drive letter currently in use (local, mapped and subst drives)."""
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    roots = []
    for i, letter in enumerate(string.ascii_uppercase):
        if bitmask & (1 << i):
            roots.append(Path(f"{letter}:\\"))
    return roots


def _hosts_mounts(root: Path) -> bool:
    """Only local disks can host folder mounts -- skip network shares, empty
    optical drives and the like, so scanning never stalls on them."""
    return ctypes.windll.kernel32.GetDriveTypeW(str(root)) in (_DRIVE_REMOVABLE, _DRIVE_FIXED)


def _folder_mounts(host_root: Path) -> list[Path]:
    """Volumes mounted in folders directly under `host_root` (e.g. D:\\pod_1).

    A subfolder qualifies if it is a reparse point (cheap: the attribute comes
    with the directory listing) that os.path.ismount() confirms is the root of
    a volume -- which rules out plain folders and ordinary junctions.
    """
    try:
        entries = list(os.scandir(host_root))
    except OSError:
        return []  # unready media, no access, ...

    found = []
    for entry in entries:
        try:
            attrs = entry.stat(follow_symlinks=False).st_file_attributes
        except (OSError, AttributeError):
            continue
        if attrs & stat.FILE_ATTRIBUTE_REPARSE_POINT and os.path.ismount(entry.path):
            found.append(Path(entry.path))
    return found


def _volume_id(path: Path) -> int | None:
    """Volume serial number of the volume `path` lives on (os.stat follows
    mount points), used to tell whether two paths are the same volume."""
    try:
        return os.stat(path).st_dev
    except OSError:
        return None


def _discover_nested(
    letter_roots: list[Path],
    hosts: list[Path],
    list_mounts: Callable[[Path], list[Path]] | None = None,
    volume_id: Callable[[Path], int | None] | None = None,
) -> list[Path]:
    """Roots of the volumes that have no drive letter and are reachable only
    through a folder mount, found by scanning `hosts` (and, recursively, the
    pods found on them).

    A volume that also has a drive letter is skipped (the letter represents
    it), and a volume mounted in several folders is reported once, under its
    shortest path -- so the same pod never appears under two roots.
    """
    list_mounts = list_mounts or _folder_mounts
    volume_id = volume_id or _volume_id

    seen = {volume_id(root) for root in letter_roots} - {None}
    found: dict[int, list[Path]] = {}
    queue = list(hosts)
    while queue:
        host = queue.pop(0)
        for mount in list_mounts(host):
            vid = volume_id(mount)
            if vid is None or vid in seen:
                continue
            if vid not in found:
                queue.append(mount)  # pods can be nested inside pods, too
            found.setdefault(vid, []).append(mount)

    roots = [min(paths, key=lambda p: (len(str(p)), str(p))) for paths in found.values()]
    return sorted(roots, key=str)


def enumerate_drive_roots(nested: bool = True) -> list[Path]:
    """Return the root of every currently mounted volume. Windows only.

    nested=True (default): drive letters, then volumes reachable only through
    a folder mount (pods nested inside a disk, e.g. D:\\pod_1).
    nested=False: drive letters only -- what "My Computer" shows. For callers
    that must never touch nested pods (e.g. backup).
    """
    if sys.platform != "win32":
        return []

    roots = _letter_roots()
    if nested:
        roots += _discover_nested(roots, [r for r in roots if _hosts_mounts(r)])
    return roots


def get_volume_label(drive_root: Path) -> str | None:
    """The volume's label (e.g. "backup", "bitu_test_drive"), or None if it
    can't be read (unready media, no label set, etc).
    """
    if sys.platform != "win32":
        return None

    # GetVolumeInformationW wants a root ending in a backslash -- for a folder
    # mount that means "D:\pod_1\", which Path() would have stripped.
    root = str(drive_root).rstrip("\\/") + "\\"

    kernel32 = ctypes.windll.kernel32
    vol_name_buf = ctypes.create_unicode_buffer(1024)
    fs_name_buf = ctypes.create_unicode_buffer(1024)
    serial = ctypes.c_uint(0)
    max_len = ctypes.c_uint(0)
    flags = ctypes.c_uint(0)
    ok = kernel32.GetVolumeInformationW(
        ctypes.c_wchar_p(root),
        vol_name_buf, ctypes.sizeof(vol_name_buf),
        ctypes.byref(serial), ctypes.byref(max_len), ctypes.byref(flags),
        fs_name_buf, ctypes.sizeof(fs_name_buf),
    )
    if not ok:
        return None
    return vol_name_buf.value or None


def find_drive_by_label(label: str, nested: bool = True) -> Path | None:
    """Return the root of the first currently mounted volume whose label
    matches `label` (case-insensitive), or None if no such volume is mounted.
    Labels aren't unique -- with several disks of pods attached, "pod_1" is
    ambiguous and the first match wins.
    """
    target = label.strip().lower()
    for root in enumerate_drive_roots(nested=nested):
        vol_label = get_volume_label(root)
        if vol_label and vol_label.strip().lower() == target:
            return root
    return None


def find_bitu_drives(nested: bool = True) -> list[tuple[Path, dict]]:
    """Return (drive_root, config) for every currently mounted volume that has
    a valid BITU config -- i.e. every pod that should get its services spawned.
    A drive letter and a folder-mounted volume are recognized the same way.
    """
    result = []
    for root in enumerate_drive_roots(nested=nested):
        config = load_drive_config(root)
        if config:
            result.append((root, config))
    return result
