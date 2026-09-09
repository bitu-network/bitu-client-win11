# file: src/cli/hotkeys/stop.py
import subprocess
from pathlib import Path
from project import get_src_root

def main():
    pid_file = get_src_root() / "hotkeys" / "hotkey_listener.pid"
    if pid_file.exists():
        try:
            pid = pid_file.read_text().strip()
            if pid:
                subprocess.run(
                    ["taskkill", "/f", "/pid", pid],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
        except Exception:
            pass
        finally:
            try:
                pid_file.unlink()
            except Exception:
                pass

if __name__ == "__main__":
    main()