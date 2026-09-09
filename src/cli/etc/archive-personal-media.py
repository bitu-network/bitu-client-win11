# file: src/cli/etc/archive-personal-media.py
import os
import shutil
from datetime import datetime
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS
import subprocess

DEST_ROOT = Path("E:/I/t")
EXTS = {".jpg", ".jpeg", ".mp4"}


def get_exif_datetime(image_path):
    """Extract 'DateTimeOriginal' from EXIF metadata if available."""
    try:
        image = Image.open(image_path)
        exif_data = image._getexif()
        if not exif_data:
            return None
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == "DateTimeOriginal":
                return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
    except Exception:
        return None


def get_video_datetime(video_path):
    """Extract creation time from MP4 metadata using ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream_tags=creation_time",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(video_path)
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        output = result.stdout.strip()
        if output:
            try:
                return datetime.fromisoformat(output.replace("Z", "+00:00"))
            except Exception:
                pass
    except Exception:
        pass
    return None


def move_by_date_taken(src_dir):
    for entry in Path(src_dir).iterdir():
        if not entry.is_file() or entry.suffix.lower() not in EXTS:
            continue

        date_taken = None
        if entry.suffix.lower() in {".jpg", ".jpeg"}:
            date_taken = get_exif_datetime(entry)
        elif entry.suffix.lower() == ".mp4":
            date_taken = get_video_datetime(entry)

        # Fallback: use file's modified time
        if not date_taken:
            date_taken = datetime.fromtimestamp(entry.stat().st_mtime)

        year = str(date_taken.year)
        month = f"{date_taken.month:02d}"
        day = f"{date_taken.day:02d}"

        dest_dir = DEST_ROOT / year / month / day
        dest_dir.mkdir(parents=True, exist_ok=True)

        dest_path = dest_dir / entry.name
        shutil.move(str(entry), dest_path)
        print(f"Moved: {entry.name} → {dest_path}")


if __name__ == "__main__":
    move_by_date_taken(Path.cwd())
