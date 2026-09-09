# file: src/lib/video_utils.py

import subprocess
from pathlib import Path

VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"}
TAG_SEPARATOR = "꞉"
# TAG_SEPARATOR = "_"



# filename: /f/video_utils.py



def is_video(path: Path) -> bool:
    """
    Returns True if the path points to a video file.
    Works for nameless files (like \.mp4) by inspecting the suffix
    and, if empty, the full name.
    """
    ext = path.suffix.lower()

    # Handle nameless files: extract extension from name if suffix empty
    if not ext and '.' in path.name:
        ext = '.' + path.name.lower().rsplit('.', 1)[-1]

    return ext in VIDEO_EXTS

def duration_seconds(path: Path) -> int | None:
    return ffprobe_duration(path)



def ffprobe_duration(path: Path) -> int | None:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return int(float(result.stdout.strip()))
    except Exception as e:
        # log(f"ffprobe failed on {path}: {e}")
        return None


def format_duration(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"[{h:02d}{TAG_SEPARATOR}{m:02d}{TAG_SEPARATOR}{s:02d}]"
    return f"[{m:02d}{TAG_SEPARATOR}{s:02d}]"