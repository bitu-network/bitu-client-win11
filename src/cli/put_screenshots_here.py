# file: src/cli/put_screenshots_here.py
import os
import sys
import winreg

def fix_screenshot_path_cwd():
    # 1. Grab the current working directory (CWD) where you run the script
    cwd_path = os.getcwd()
    
    # ANSI escape code for Amber/Yellow text
    AMBER = "\033[93m"
    RESET = "\033[0m"
    
    # 2. Check for Administrator privileges up front
    try:
        # Try to open the registry key with write permissions to test access
        registry_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        test_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path, 0, winreg.KEY_SET_VALUE)
        winreg.CloseKey(test_key)
    except PermissionError:
        print(f"\n{AMBER}[⚠️] WARNING: Administrator Mode Required!{RESET}")
        print(f"{AMBER}Please close this window, right-click your Terminal/CMD, and choose 'Run as administrator'.{RESET}\n")
        return

    # 3. Target GUID that tells Windows where to save screenshots
    screenshot_guid = "{B7BEDE81-DF94-4682-A7D8-57A52620B86F}"

    # 4. Verify existing settings
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path, 0, winreg.KEY_READ)
        current_value, _ = winreg.QueryValueEx(key, screenshot_guid)
        winreg.CloseKey(key)
    except FileNotFoundError:
        # If the key string doesn't even exist yet
        current_value = None

    # 5. Check if it's already set to the CWD
    if current_value == cwd_path:
        print(f"[✅] Everything is already properly set! Screenshots point to: {cwd_path}")
        return

    # 6. Self-Healing: Fix it if it doesn't match
    print(f"[🔧] Current path mismatch detected. Fixing it now...")
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, screenshot_guid, 0, winreg.REG_SZ, cwd_path)
        winreg.CloseKey(key)
        
        print(f"[🎉] Success! Screenshots path updated to: {cwd_path}")
        print("[ℹ️] Reminder: Restart your computer or restart 'explorer.exe' for Windows to apply the change.")
    except Exception as e:
        print(f"[❌] An unexpected error occurred while writing: {e}")

if __name__ == "__main__":
    # Enable ANSI escape codes in Windows Command Prompt for the color to work
    os.system('') 
    fix_screenshot_path_cwd()
