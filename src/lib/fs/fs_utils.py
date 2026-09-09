# file: src/lib/fs/fs_utils.py
def safe_folder_name(name: str) -> str:
    """Convert a string into a filesystem-safe folder name."""
    return name.replace(":", "_")
