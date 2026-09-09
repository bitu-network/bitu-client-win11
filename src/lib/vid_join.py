# file: src/lib/vid_join.py
# description: merge selected video files in Explorer into a single file, optionally delete originals

from apps.explorer import get_active_explorer_info
from pathlib import Path
import subprocess
import sys
import os

def merge_videos(selected_files, delete_original=False):
    if not selected_files:
        print("No files selected to merge.")
        return

    # Verify all files exist
    for f in selected_files:
        if not Path(f).exists():
            print(f"File not found: {f}")
            return

    # Sort files alphabetically
    selected_files.sort()
    paths = [Path(f) for f in selected_files]

    # Build output filename by joining stems with underscores
    combined_stem = "_".join([p.stem for p in paths])
    out_file = paths[0].with_name(f"{combined_stem}{paths[0].suffix}")

    # Create temporary file listing for ffmpeg concat
    list_file = Path(out_file.parent) / f"ffmpeg_merge_list.txt"
    with open(list_file, 'w', encoding='utf-8') as f:
        for p in paths:
            # ffmpeg requires paths to be escaped
            f.write(f"file '{p.resolve().as_posix()}'\n")

    # Run ffmpeg concat
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(out_file)
    ]
    print(f"Merging {len(paths)} files into:\n  {out_file}")
    subprocess.run(cmd, check=True)

    # Remove temporary list file
    list_file.unlink()

    # Optionally delete original files
    if delete_original:
        for p in paths:
            try:
                p.unlink()
                print(f"Deleted original: {p}")
            except Exception as e:
                print(f"Failed to delete {p}: {e}")

    print("Merge complete.")

def main():
    folder, selected = get_active_explorer_info()
    if not folder or not selected:
        print("No selected files in Explorer.")
        return

    folder_path = Path(folder)
    selected_paths = [str(folder_path / name) for name in selected]

    # Call merge with default delete_original=False
    merge_videos(selected_paths, delete_original=True)

if __name__ == "__main__":
    main()
