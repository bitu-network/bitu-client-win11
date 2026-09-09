# file: src/hotkeys/y_alt_ctrl_shift.py
# description: single hotkey router for video operations:
#   - multiple selected files → merge/join
#   - single selected file → shot decomposition
#   - no selection → split current MPC-player file

from pathlib import Path
from apps.explorer import get_active_explorer_info
from lib import vid_split, vid_decompose, vid_join
import subprocess

SCRIPT_PATH = Path(__file__).resolve()

def run_in_new_terminal(module_name, arg_path):
    """Launch the given module in a new terminal for progress display."""
    cmd = f'start cmd /c python -m {module_name} --split "{arg_path}"'
    subprocess.Popen(cmd, shell=True)

def main():
    folder, selected = get_active_explorer_info()
    folder_path = folder if folder else None
    selected_paths = [str(folder_path / name) for name in selected] if folder_path else []

    if len(selected_paths) > 1:
        # Merge multiple files
        vid_join.merge_videos(selected_paths, delete_original=True)
    elif len(selected_paths) == 1:
        # Decompose single file into shots
        run_in_new_terminal("f.vid_decompose", selected_paths[0])
    else:
        # No selection → attempt split of current MPC-player file
        from lib.player import get_current_file_and_position
        player_file, _ = get_current_file_and_position()
        if player_file:
            run_in_new_terminal("f.vid_split", player_file)
        else:
            print("No player file active and no files selected in Explorer.")

if __name__ == "__main__":
    main()