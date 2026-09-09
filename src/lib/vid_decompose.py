# file: src/lib/vid_decompose.py
# title: split selected into shots (frame-accurate, colored progress)

from apps.explorer import get_active_explorer_info
from pathlib import Path
import subprocess
import sys, os

SCRIPT_PATH = Path(__file__).resolve()

def print_progress(current, total, bar_length=30):
    GREEN = "\033[32m"
    RESET = "\033[0m"
    filled_length = int(bar_length * current // total)
    bar = f"{GREEN}{'█' * filled_length}{RESET}{'-' * (bar_length - filled_length)}"
    print(f"\rProgress: |{bar}| {current}/{total} shots", end='', flush=True)

def run_in_new_terminal(file_path):
    cmd = f'start cmd /c python "{SCRIPT_PATH}" --split "{file_path}"'
    subprocess.Popen(cmd, shell=True)

def split_into_shots(file_path):
    from scenedetect import VideoManager, SceneManager
    from scenedetect.detectors import ContentDetector

    file_path = Path(file_path)

    # Friendly startup message
    BLUE = "\033[34m"
    GREEN = "\033[32m"
    RESET = "\033[0m"
    print(f"{BLUE}Preparing to split: {file_path}{RESET}")
    print(f"{GREEN}Loading video and detecting scenes... please wait...{RESET}")

    # Suppress VideoManager deprecation warning
    stderr_backup = sys.stderr
    sys.stderr = open(os.devnull, 'w')
    video_manager = VideoManager([str(file_path)])
    sys.stderr.close()
    sys.stderr = stderr_backup

    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=30.0))
    video_manager.start()
    scene_manager.detect_scenes(frame_source=video_manager)

    scene_list = scene_manager.get_scene_list()
    total = len(scene_list)
    width = len(str(total))
    out_dir = file_path.with_name(f"{file_path.stem}_shots")
    out_dir.mkdir(exist_ok=True)

    print(f"\nDetected {total} shots. Starting frame-accurate splitting...")

    for i, (start, end) in enumerate(scene_list, 1):
        start_sec = start.get_seconds()
        end_sec = end.get_seconds()
        out_file = out_dir / f"{i:0{width}d}{file_path.suffix}"

        print_progress(i - 1, total)
        subprocess.run([
            "ffmpeg", "-y",
            "-ss", str(start_sec),
            "-to", str(end_sec),
            "-i", str(file_path),
            "-c:v", "libx264", "-crf", "0", "-preset", "veryfast",
            "-c:a", "copy",
            str(out_file)
        ], check=True)
        print_progress(i, total)

    video_manager.release()
    print(f"\n{GREEN}Frame-accurate shot splitting complete for: {file_path}{RESET}")

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", help="Single file to split (internal use)")
    args = parser.parse_args()

    if args.split:
        split_into_shots(args.split)
        return

    folder, selected = get_active_explorer_info()
    if not folder or not selected:
        print("No files selected or active Explorer window found, skipping split.")
        return

    folder_path = Path(folder)
    for name in selected:
        file_path = folder_path / name
        if file_path.exists():
            run_in_new_terminal(file_path)
        else:
            print(f"File not found: {file_path}")

if __name__ == "__main__":
    main()
