# file: src/tests/f/fs/test_filename_utils.py

from pathlib import Path
import pytest
from lib.fs.filename_utils import prepend_tag

def test_prepend_tag_normal_file(tmp_path):
    file = tmp_path / "video.mp4"
    file.write_text("dummy")
    tag = "[00.45]"
    result = prepend_tag(file, tag)
    assert result is True
    expected = tmp_path / f"{tag} video.mp4"
    assert expected.exists()

def test_prepend_tag_dot_only_file(tmp_path):
    file = tmp_path / ".mp4"
    file.write_text("dummy")
    tag = "[01.23]"
    result = prepend_tag(file, tag)
    assert result is True
    # Should use folder name as stem
    expected = tmp_path / f"{tag} {tmp_path.name}.mp4"
    assert expected.exists()

def test_prepend_tag_unicode_filename(tmp_path):
    # Farsi / Unicode filename
    filename = "بدن نمایی.mp4"
    file = tmp_path / filename
    file.write_text("dummy")
    tag = "[02.34]"
    result = prepend_tag(file, tag)
    assert result is True
    expected = tmp_path / f"{tag} {filename}"
    assert expected.exists()

def test_prepend_tag_already_tagged(tmp_path):
    file = tmp_path / "[03.21] video.mp4"
    file.write_text("dummy")
    tag = "[03.21]"
    result = prepend_tag(file, tag)
    assert result is False  # no change
