# file: src/cli/dev/watch/burden_detector.py
import time
import win32gui
import win32process
import win32api
import win32con
import psutil
from datetime import datetime

# Windows Cursor Constants for Spinning/Loading modes
# 65541 or similar internal handles represent OCR_WAIT and OCR_APPSTARTING
# Because cursor handle IDs can change across boots, we grab the defaults dynamically.
try:
    CURSOR_WAIT = win32gui.LoadCursor(0, win32con.IDC_WAIT)
    CURSOR_APPSTARTING = win32gui.LoadCursor(0, win32con.IDC_APPSTARTING)
    LOADING_HANDLES = {int(CURSOR_WAIT), int(CURSOR_APPSTARTING)}
except Exception:
    # Fallback IDs often assigned by the Win32 subsystem if dynamic loading drops
    LOADING_HANDLES = {65543, 65545} 

def get_process_info_at_mouse():
    """Finds the name and PID of the process directly underneath the mouse cursor."""
    try:
        # Get absolute mouse coordinates
        flags, hcursor, (x, y) = win32gui.GetCursorInfo()
        # Locate the specific window handle under the coordinates
        hwnd = win32gui.WindowFromPoint((x, y))
        if hwnd:
            # Extract the thread and process ID from the window handle
            thread_id, process_id = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(process_id)
            return process.name(), process_id
    except Exception:
        pass
    return "Unknown Process", "N/A"

def monitor_cursor(threshold_seconds=1.0):
    print(f"Monitoring started. Logging loading cursors persisting > {threshold_seconds}s...")
    print("Press Ctrl+C to terminate the script.\n")
    
    is_loading = False
    start_time = None
    suspect_process = "Unknown"
    suspect_pid = "N/A"

    while True:
        try:
            # Extract current cursor metrics
            flags, hcursor, pos = win32gui.GetCursorInfo()
            cursor_handle = int(hcursor)
            
            # Check if current handle matches a known Windows loading pattern
            if cursor_handle in LOADING_HANDLES:
                if not is_loading:
                    # Cursor just switched to spinning mode
                    is_loading = True
                    start_time = time.time()
                    # Catch the process currently active under the mouse
                    suspect_process, suspect_pid = get_process_info_at_mouse()
            else:
                if is_loading:
                    # Cursor just reverted to standard pointer
                    duration = time.time() - start_time
                    if duration >= threshold_seconds:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(f"[{timestamp}] 🔴 SPINNING DETECTED")
                        print(f"    Duration:  {duration:.2f} seconds")
                        print(f"    App Name:  {suspect_process}")
                        print(f"    PID:       {suspect_pid}")
                        print("-" * 45)
                    
                    # Reset tracker flags
                    is_loading = False
                    start_time = None
            
            # Brief pause to minimize CPU consumption
            time.sleep(0.05)
            
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user.")
            break
        except Exception as e:
            # Prevent crashes if cursor info drops during full-screen transitions
            time.sleep(0.1)

if __name__ == "__main__":
    monitor_cursor(threshold_seconds=1.0)
