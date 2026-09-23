# file: src/pod/paths.py
# description: where things live on a pod. A pod is a mounted volume: a drive
# letter (or UNC share), or a volume mounted into a folder of another volume
# (a pod nested inside a physical disk, e.g. D:\pod_1). The pod root is simply
# the nearest enclosing mount point of a path -- no marker file to find.

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

# -----------------------
# Constants
# -----------------------
BLOBS_DIR = "o"
CONCEPTS_DIR = "-"
PERSONAL_CONCEPTS_DIR = "I/-"
PERSONAL_CALENDAR_DIR = "I/t"
BITU_DIR = "bitu"  # <pod>\I\-\bitu\ : BITU's own per-pod state (config.json, dedupe.log)


def _absolute(path: Path) -> Path:
    # abspath, not resolve(): resolve() follows subst drives, mapped drives and
    # junctions, which could turn "E:\..." into some other root. The drive the
    # user sees is the pod.
    return Path(os.path.abspath(path))


def _is_mount(path: Path) -> bool:
    """Is `path` the root of a volume: a drive root, a UNC share root, or a
    folder that another volume is mounted into?"""
    try:
        return os.path.ismount(path)
    except (OSError, ValueError):
        return False


def pod_root(path: Path) -> Path:
    """The pod a path lives on: its nearest enclosing mount point -- a drive
    root, a UNC share root, or a folder mount such as D:\\pod_1.

    Walks up the path lexically and never resolves it, so the result is always
    a prefix of the path as given (the drive/mount the user sees is the pod).
    """
    p = _absolute(path)
    if not p.anchor:
        raise FileNotFoundError(f"No pod root found from {path}")
    for candidate in (p, *p.parents):
        if _is_mount(candidate):
            return candidate
    return Path(p.anchor)


def same_pod(a: Path, b: Path) -> bool:
    """True if both paths live on the same pod, i.e. the same volume -- and so
    the same hardlink domain (NTFS can't hardlink across volumes)."""
    return pod_root(a) == pod_root(b)


def _pod_dir(path: Path, rel: str) -> Path:
    folder = pod_root(path) / rel
    folder.mkdir(parents=True, exist_ok=True)
    return folder


# -----------------------
# Blob and Concept Paths
# -----------------------
def blobs_root(path: Path) -> Path:
    """<drive>\\o, created if necessary."""
    return _pod_dir(path, BLOBS_DIR)


def concepts_root(path: Path) -> Path:
    """<drive>\\-, created if necessary."""
    return _pod_dir(path, CONCEPTS_DIR)


def personal_concepts_root(path: Path) -> Path:
    """<drive>\\I\\-, created if necessary."""
    return _pod_dir(path, PERSONAL_CONCEPTS_DIR)


def personal_calendar_root(path: Path) -> Path:
    """<drive>\\I\\t, created if necessary."""
    return _pod_dir(path, PERSONAL_CALENDAR_DIR)


# -----------------------
# Utility: relative path to pod root
# -----------------------
def relative_path(path: Path) -> Path:
    """The path relative to its pod root."""
    return _absolute(path).relative_to(pod_root(path))


def interpret_path(cwd: Path) -> Optional[dict]:
    """
    Return a dict describing the type ('blob', 'concept', 'root' or 'other')
    and the identifier (SHA-256 hex or concept name) for a path on a pod.
    """
    rel = relative_path(cwd)

    parts = rel.parts
    if not parts:
        return {"type": "root", "id": None}

    head = parts[0]
    if head == BLOBS_DIR:
        return {"type": "blob", "id": parts[1] if len(parts) > 1 else None}
    elif head == CONCEPTS_DIR:
        return {"type": "concept", "id": parts[1] if len(parts) > 1 else None}
    else:
        return {"type": "other", "id": str(rel)}
