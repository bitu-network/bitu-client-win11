# file: src/lib/file_reader.py
# Description: Provides safe text file reading utilities.

from pathlib import Path


def read_file_content(path: Path) -> str:
    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    except Exception as e:
        return f"[FAILED TO READ FILE: {e}]"