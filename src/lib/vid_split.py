# file: src/lib/vid_split.py
# description: frame-accurate, lossless split of the current MPC-player file with terminal progress

from lib.player import get_current_file_and_position, open_file, close
from pathlib import Path
import subprocess
import sys
import os
import time
import json

SCRIPT_PATH = Path(__file__).resolve()

def print_progress(current, total, bar_length=30):
    GREEN = "\033[32m"
    RESET = "\033[0m"
    filled_length = int(bar_length * current // total)
    bar = f"{GREEN}{'█' * filled_length}{RESET}{'-' * (bar_length - filled_length)}"
    print(f"\rProgress: |{bar}| {current}/{total}", end='', flush=True)

def run_in_new_terminal(file_path):
    """Launch this script in a new terminal to show progress."""
    cmd = f'start cmd /c python "{SCRIPT_PATH}" --split "{file_path}"'
    subprocess.Popen(cmd, shell=True)

def get_frames(video_path):
    """Return list of frame timestamps in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_frames",
        "-show_entries", "frame=pkt_pts_time,best_effort_timestamp_time",
        "-of", "json", video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True, check=True)
    data = json.loads(result.stdout)
    frames = []
    for f in data.get("frames", []):
        t = f.get("pkt_pts_time") or f.get("best_effort_timestamp_time")
        if t is not None:
            frames.append(float(t))
    return frames

def find_nearest_frame(frames, time_sec):
    return min(frames, key=lambda t: abs(t - time_sec))

def split_lossless(file_path, delete_original=True):
    try:
        file_path, pos_ms = get_current_file_and_position()
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Video file not found: {file_path}")
        pos_sec = pos_ms / 1000.0

        # Close player immediately for instant feedback
        if delete_original:
            close()

        frames = get_frames(str(file_path))
        if not frames:
            raise ValueError("No frames found in file")

        split_time = find_nearest_frame(frames, pos_sec)

        part1_path = file_path.with_name(f"{file_path.stem}.1{file_path.suffix}")
        part2_path = file_path.with_name(f"{file_path.stem}.2{file_path.suffix}")

        # Lossless frame-accurate split using ffmpeg
        subprocess.run([
            "ffmpeg", "-y", "-i", str(file_path),
            "-to", str(split_time),
            "-c:v", "libx264", "-crf", "0", "-preset", "veryslow",
            "-c:a", "copy",
            str(part1_path)
        ], check=True)
        print_progress(1,2)

        subprocess.run([
            "ffmpeg", "-y", "-i", str(file_path),
            "-ss", str(split_time),
            "-c:v", "libx264", "-crf", "0", "-preset", "veryslow",
            "-c:a", "copy",
            str(part2_path)
        ], check=True)
        print_progress(2,2)

        print(f"\nCreated:\n  {part1_path}\n  {part2_path}")

        # Delete original
        if delete_original:
            for _ in range(5):
                try:
                    file_path.unlink()
                    print(f"Original file deleted: {file_path}")
                    break
                except PermissionError:
                    time.sleep(0.5)
            else:
                print(f"Failed to delete original file: {file_path}")

            # Open second part paused
            open_file(part2_path, paused=True)

    except Exception as e:
        print("Error splitting file:", e)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", help="Internal use: file to split in terminal")
    args = parser.parse_args()

    if args.split:
        split_lossless(args.split)
        return

    # Normal hotkey path: get current file and launch new terminal
    file_path, _ = get_current_file_and_position()
    if file_path:
        run_in_new_terminal(file_path)
    else:
        print("No active file found in player.")

if __name__ == "__main__":
    main()
