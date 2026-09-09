# file: src/hotkeys/m_alt.py

import os
import re
import math
import shutil
import ctypes

from lib.hotkey_context import get_context_fields


# Enable ANSI color on Windows 10+
if os.name == "nt":
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)


GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"


application, folder = get_context_fields(
    "application",
    "folder_path",
)


print(GREEN + f"Active application: {application}")

if application == "explorer.exe" and folder:
    print(f"Active Explorer folder: {folder}")
    
    # Regex to find bracketed numbers like [000] or [45]
    duration_pattern = re.compile(r'\[(\d+)\]')
    moved_count = 0

    try:
        for filename in os.listdir(folder):
            if filename.lower().endswith('.url'):
                match = duration_pattern.search(filename)
                if match:
                    m = int(match.group(1))
                    
                    # Calculate power-of-two lower bound bucket: 2^floor(log2(m))
                    n = 2 ** math.floor(math.log2(m)) if m > 0 else 0
                    
                    target_dir = os.path.join(folder, f"_{n}")
                    os.makedirs(target_dir, exist_ok=True)
                    
                    src_path = os.path.join(folder, filename)
                    dst_path = os.path.join(target_dir, filename)
                    
                    try:
                        shutil.move(src_path, dst_path)
                        print(f"  Moved: {filename} -> _{n}/{filename}")
                        moved_count += 1
                    except Exception as e:
                        print(YELLOW + f"  Error moving {filename}: {e}" + RESET)
                        
        print(f"Successfully sorted {moved_count} .url file(s).")
    except Exception as e:
        print(YELLOW + f"Error accessing folder: {e}" + RESET)
else:
    print("Not an active File Explorer context or folder path unavailable.")

print("-" * 40 + RESET)