# file: src/tests/f/fs/test_video_utils.py

from pathlib import Path
from lib import video_utils

def test_is_video(tmp_path):
    file = tmp_path / "test.mp4"
    file.write_text("dummy")
    assert video_utils.is_video(file)

    non_video = tmp_path / "file.txt"
    non_video.write_text("dummy")
    assert not video_utils.is_video(non_video)

def test_format_duration():
    assert video_utils.format_duration(65) == "[01꞉05]"
    assert video_utils.format_duration(3665) == "[01꞉01꞉05]"
