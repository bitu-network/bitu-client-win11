# file: src/project.py

from pathlib import Path


def get_project_root() -> Path:
    src_dir = Path(__file__).resolve().parent
    return src_dir.parent


def get_src_root() -> Path:
    return Path(__file__).resolve().parent
