# file: src/lib/fs/filename_utils.py

from pathlib import Path

def prepend_tag(path: Path, tag: str) -> bool:
    # Handle nameless files: use folder name as stem
    stem = path.stem
    if not stem:
        stem = path.parent.name if path.parent.name else "file"

    if path.name.startswith(tag):
        return False

    new_name = f"{tag} {stem}{path.suffix}"
    try:
        path.rename(path.with_name(new_name))
        return True
    except Exception as e:
        # log(f"Rename failed: {e}")
        return False
