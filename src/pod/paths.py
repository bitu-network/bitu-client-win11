# file: src/pod/paths.py

from pathlib import Path
from typing import Optional

# -----------------------
# Constants
# -----------------------
DB_FILENAME = ".pod"
BLOBS_DIR = "o"
CONCEPTS_DIR = "-"
PERSONAL_CONCEPTS_DIR = "I/-"
PERSONAL_CALENDAR_DIR = "I/t"

def pod_root(path: Path) -> Path:
    """
    Return the closest parent (including cwd) containing the .pod SQLite file as pod root.
    """

    # if path is None:
    #     path = Path.cwd()
    # else:
    #     path = Path(path)
    path = Path(path)
    path = path.resolve()

    for parent in [path] + list(path.parents):
        pod_file = parent / DB_FILENAME
        if pod_file.exists() and pod_file.is_file():
            return parent

    raise FileNotFoundError(f"No pod root found from {path}")



# -----------------------
# DB , Blob and Concept Paths
# -----------------------
def db_path(path: Path) -> Path | None:
    db_dir = pod_root(path)
    return db_dir / DB_FILENAME if db_dir else None

def blobs_root(path: Path) -> Path:
    """
    Return the path to the blobs folder (root / "o"), creating if necessary.
    """
    folder = pod_root(path) / BLOBS_DIR
    folder.mkdir(parents=True, exist_ok=True)
    return folder.resolve()


def concepts_root(path: Path) -> Path:
    """
    Return the path to the concepts folder (root / "-"), creating if necessary.
    """
    folder = pod_root(path) / CONCEPTS_DIR
    folder.mkdir(parents=True, exist_ok=True)
    return folder.resolve()

def personal_concepts_root(path: Path) -> Path:
    """
    Return the path to the personal concepts folder (root / "I/-"), creating if necessary.
    """
    folder = pod_root(path) / PERSONAL_CONCEPTS_DIR
    folder.mkdir(parents=True, exist_ok=True)
    return folder.resolve()


def personal_calendar_root(path: Path) -> Path:
    """
    Return the path to the personal calendar folder (root / "I/t"), creating if necessary.
    """
    folder = pod_root(path) / PERSONAL_CALENDAR_DIR
    folder.mkdir(parents=True, exist_ok=True)
    return folder.resolve()



# -----------------------
# Utility: relative path to archive root
# -----------------------
def relative_path(path: Path) -> Optional[Path]:
    """
    Return cwd relative to the pod root, or None if no root exists.
    """
    root = pod_root(path)
    return path.resolve().relative_to(root)


def interpret_path(cwd: Path) -> Optional[dict]:
    """
    Return a dict describing the type ('blob', 'concept', or 'root')
    and the identifier (SHA-256 hex or concept name), or None if outside archive root.
    """
    rel = relative_path(cwd)
    if rel is None:
        return None

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






