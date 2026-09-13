# file: src/hotkeys/m_alt_ctrl_shift.py
# description: diagnostic script with enabled ANSI colors and clean filenames

import os
from pathlib import Path
from lib.hotkey_context import load_context

os.system("")  # Enable ANSI color escape sequences in the new Windows console

def main():
    ctx = load_context()
    
    print("\033[95m=== HOTKEY CONTEXT DIAGNOSTIC ===\033[0m")
    print(f"\033[93mApplication:\033[0m   {ctx.get('application')}")
    print(f"\033[93mWindow Title:\033[0m  {ctx.get('window_title')}")
    print(f"\033[93mFolder Path:\033[0m   \033[96m{ctx.get('folder_path')}\033[0m")
    print("\033[93mSelected Items:\033[0m")
    for item in ctx.get('selected_items', []):
        filename = Path(item).name
        print(f"  - \033[92m{filename}\033[0m")
    print("\033[95m=================================\033[0m")
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()