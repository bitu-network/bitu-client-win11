# file: src/lib/file_types/video_and_audio.py

import subprocess
from pathlib import Path


def get_duration_seconds(video_path: Path) -> float:
    """
    Return the duration of a media file in seconds.

    Uses ffprobe to inspect the actual file.
    """

    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    return float(result.stdout.strip())


def get_duration_tag(duration_seconds: float) -> str:
    """
    Convert seconds to a 3 digit minute tag.

    Example:
    301 seconds -> "005"
    """

    minutes = round(duration_seconds / 60)

    return f"{minutes:03d}"