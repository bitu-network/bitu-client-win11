# file: src/cli/apps/explorer/info.py

import os
import ctypes
import win32com.client
import win32gui

# Enable ANSI color on Windows 10+
if os.name == "nt":
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

GREEN = "\033[92m"
CYAN = "\033[96m"
DIM = "\033[90m"
RESET = "\033[0m"


def get_explorer_windows_zorder():
    """Enumerates Explorer windows in Z-order (front-most / most recently active first)

    and extracts their current folder path and highlighted selections.
    """
    zorder_hwnds = []

    def enum_window_callback(hwnd, extra):
        if win32gui.IsWindowVisible(hwnd):
            if win32gui.GetClassName(hwnd) == "CabinetWClass":
                zorder_hwnds.append(hwnd)
        return True

    win32gui.EnumWindows(enum_window_callback, None)

    shell = win32com.client.Dispatch("Shell.Application")
    window_map = {}
    for window in shell.Windows():
        try:
            if window.FullName.lower().endswith("explorer.exe"):
                window_map[window.HWND] = window
        except Exception:
            continue

    explorer_data = []
    for hwnd in zorder_hwnds:
        if hwnd in window_map:
            window = window_map[hwnd]
            try:
                folder_path = window.Document.Folder.Self.Path
                selected_items = [
                    item.Path for item in window.Document.SelectedItems()
                ]
                explorer_data.append({
                    "path": folder_path,
                    "selected": selected_items,
                })
            except Exception:
                continue

    return explorer_data


if __name__ == "__main__":
    windows = get_explorer_windows_zorder()

    print(GREEN + "\n[*] Open Windows Explorer Windows (Ordered by Recent Activity):" + RESET)
    if not windows:
        print("    [-] No open Explorer windows detected.")
    else:
        print("-" * 60)
        for idx, win in enumerate(windows, 1):
            path = win["path"]
            selected = win["selected"]
            
            print(f"{GREEN}[{idx}]{RESET} {path}")
            
            if selected:
                for s_idx, s_item in enumerate(selected, 1):
                    file_name = os.path.basename(s_item)
                    print(f"    {DIM}{idx}.{s_idx}{RESET} {CYAN}{file_name}{RESET}")
            else:
                print(f"    {DIM}{idx}.1{RESET} {DIM}(No selection){RESET}")
            print("-" * 60)