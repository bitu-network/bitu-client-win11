# file: src/hotkeys/x_alt.py

## from apps.vscode import get_active_process_name,get_active_window_title
## print("active process:", get_active_process_name())
## print("active window title:", get_active_window_title())


# file: src/hotkeys/x_alt.py
# from __future__ import annotations

import time
from lib.wait_cursor import WaitCursor


def main():
    print("[INFO] Showing wait cursor / spinner for 3 seconds...")
    with WaitCursor():
        time.sleep(3)
    print("[OK] Done.")


if __name__ == "__main__":
    main()
