# file: src/pod/db.py
import sqlite3
from pathlib import Path

from paths import db_path


def get_connection(path: Path | None = None) -> sqlite3.Connection:
    """
    Return a connection to the pod SQLite file.
    """
    pod_file = db_path(path)
    if not pod_file or not pod_file.exists():
        raise FileNotFoundError(f"Pod file not found: {pod_file}")
    return sqlite3.connect(pod_file)


