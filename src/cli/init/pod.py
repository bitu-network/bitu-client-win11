# file: src/cli/init/pod.py

import sys
from pathlib import Path
import sqlite3

# -----------------------------
# Exceptions
# -----------------------------
class PodInitError(Exception):
    pass

# -----------------------------
# Constants
# -----------------------------
DEFAULT_POD_FILE = Path.cwd() / ".pod"  # or rename to .biou if preferred

CORE_TABLES_SQL = [
    """
    CREATE TABLE IF NOT EXISTS peers (
        public_key TEXT PRIMARY KEY,
        socket TEXT NOT NULL UNIQUE,
        alias TEXT NOT NULL UNIQUE,
        balance INTEGER NOT NULL DEFAULT 0,
        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS config (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """
]

# -----------------------------
# Functions
# -----------------------------
def init_pod_file(pod_file: Path = DEFAULT_POD_FILE) -> Path:
    """
    Initialize the pod SQLite file with core tables.

    Args:
        pod_file: Path to the .pod file (or .biou)

    Returns:
        Path to the initialized pod file.

    Raises:
        PodInitError on failure.
    """
    pod_file = pod_file.resolve()

    if pod_file.exists() and not pod_file.is_file():
        raise PodInitError(f"Target path exists and is not a file: {pod_file}")

    try:
        conn = sqlite3.connect(pod_file)
        cursor = conn.cursor()
        for sql in CORE_TABLES_SQL:
            cursor.execute(sql)
        conn.commit()
        conn.close()
    except Exception as e:
        raise PodInitError(f"Failed to initialize pod file {pod_file}: {e}") from e

    return pod_file

# -----------------------------
# CLI Entry Point
# -----------------------------
def main():
    """
    CLI entry point to initialize the pod.
    Can later be extended to run a step-by-step wizard.
    """
    try:
        pod_path = init_pod_file()
        print(f"[ok] Pod initialized at {pod_path}")
    except PodInitError as e:
        print(f"[error] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

