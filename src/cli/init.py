# file: src/cli/init.py
import os
import runpy
import sys
import shutil
from pathlib import Path

WIZARD_FOLDER = os.path.join(os.path.dirname(__file__), "init")
POD_FILE = Path.cwd() / ".pod"

# Explicit order of execution
WIZARD_ORDER = [
    "pod.py",
    "keygen.py",
]

def main():
    python_exe = sys.executable

    # Check for existing .pod
    if POD_FILE.exists():
        while True:
            choice = input(f"[!] Pod file already exists at {POD_FILE}.\n"
                           "Do you want to (A)bort or (D)elete and start fresh? [A/D]: ").strip().upper()
            if choice == "A":
                print("[i] Aborting initialization.")
                sys.exit(0)
            elif choice == "D":
                POD_FILE.unlink()
                print(f"[i] Deleted existing pod file: {POD_FILE}")
                break
            else:
                print("[!] Invalid choice. Please enter 'A' or 'D'.")

    for filename in WIZARD_ORDER:
        filepath = os.path.join(WIZARD_FOLDER, filename)
        if not os.path.isfile(filepath):
            print(f"[!] Wizard not found: {filename}, skipping.")
            continue

        print(f"[+] Launching wizard: {filename}")
        # subprocess.run([python_exe, filepath])
        runpy.run_path(filepath, run_name="__main__")

        width = shutil.get_terminal_size().columns
        print("\n" + "|" * width + "\n")  # light horizontal line

    print("[✓] All wizards completed.")

if __name__ == "__main__":
    main()
