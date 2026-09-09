# file: src/lib/fs/rename.py

from pathlib import Path

from lib.str.tags import (
    prepend_prefix,
    append_prefix,
    prepend_suffix,
    append_suffix,
)


def rename_file(path: Path, new_name: str) -> Path:
    """
    Rename a file while keeping it in the same directory.
    """
    new_path = path.with_name(new_name)
    path.rename(new_path)
    return new_path


def prepend_prefix_tag(path: Path, tag: str) -> Path:
    """
    [a] foo [b].jpg
    ->
    [c][a] foo [b].jpg
    """
    return rename_file(
        path,
        prepend_prefix(path.name, tag),
    )


def append_prefix_tag(path: Path, tag: str) -> Path:
    """
    [a] foo [b].jpg
    ->
    [a][c] foo [b].jpg
    """
    return rename_file(
        path,
        append_prefix(path.name, tag),
    )


def prepend_suffix_tag(path: Path, tag: str) -> Path:
    """
    [a] foo [b].jpg
    ->
    [a] foo [c][b].jpg
    """
    return rename_file(
        path,
        prepend_suffix(path.name, tag),
    )


def append_suffix_tag(path: Path, tag: str) -> Path:
    """
    [a] foo [b].jpg
    ->
    [a] foo [b][c].jpg
    """
    return rename_file(
        path,
        append_suffix(path.name, tag),
    )