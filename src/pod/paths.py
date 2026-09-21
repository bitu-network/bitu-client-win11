# file: src/pod/paths.py
# description: where things live on a pod. Each drive (or UNC share) is a pod,
# so the pod root is simply the drive a path lives on -- no marker file to find.

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


def _absolute(path: Path) -> Path:
    # abspath, not resolve(): resolve() follows subst drives, mapped drives and
    # junctions, which could turn "E:\..." into some other root. The drive the
    # user sees is the pod.
    return Path(os.path.abspath(path))


def pod_root(path: Path) -> Path:
    """The pod a path lives on: its drive root (or UNC share root)."""
    anchor = _absolute(path).anchor
    if not anchor:
        raise FileNotFoundError(f"No pod root found from {path}")
    return Path(anchor)


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
