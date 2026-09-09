# file: src/cli/hotkeys/log.py
import sys
import subprocess
from pathlib import Path

# Ensure 'src' directory is in sys.path so 'project' can be imported
src_dir = Path(__file__).resolve().parents[2]
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from project import get_src_root

def main():
    log_file = get_src_root() / "hotkeys" / "hotkey_debug.log"
    if not log_file.exists():
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_text("--- Hotkey debug log initialized ---\n")

    subprocess.Popen([
        "powershell.exe", "-NoExit", "-Command",
        f"Write-Host '=== Hotkey Debug Log (Close window to exit) ===' -ForegroundColor Cyan; Get-Content -Path '{log_file}' -Wait"
    ], creationflags=subprocess.CREATE_NEW_CONSOLE)

if __name__ == "__main__":
    main()