# file: src/lib/low_level_helpers.py
from pathlib import Path
from datetime import datetime
from typing import Optional

def write_file(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(value))

def read_file(path: Path, default=None):
    return path.read_text().strip() if path.exists() else default

def format_timestamp(ts: Optional[str]):
    try:
        if ts in (None, ""):
            return ""
        return datetime.fromtimestamp(int(ts)).strftime("%Y.%m.%d %H%M%S")
    except Exception:
        return ts or ""
