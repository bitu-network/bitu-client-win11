# file: src/lib/project_finder.py

from pathlib import Path


def find_project_root(start: Path) -> Path | None:
    """
    Find the nearest project root by walking upward from a path.

    A project root is identified by the presence of a .git directory.

    Args:
        start:
            Starting file or directory path.

    Returns:
        The project root path, or None if no root is found.
    """

    current = start.resolve()

    if current.is_file():
        current = current.parent

    while True:
        if (current / ".git").exists():
            return current

        if current == current.parent:
            break

        current = current.parent

    return None