# file: src/cli/sudo.py
import ctypes
import os

def main():
    cwd = os.getcwd()
    
    # Launch elevated CMD in the current working directory
    ctypes.windll.shell32.ShellExecuteW(
        None, 
        "runas", 
        "cmd.exe", 
        f'/k cd /d "{cwd}"', 
        None, 
        1
    )
    
    # Detach and close the current terminal window
    ctypes.windll.kernel32.FreeConsole()

if __name__ == "__main__":
    main()