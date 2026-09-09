# file: src/cli/hotkeys/start.py


import os
import sys
import subprocess
from pathlib import Path

src_dir = Path(__file__).resolve().parents[2]
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
    
from project import get_src_root
from lib.kbd_hotkey_listener import ComboListener
from lib.kbd_hotkey_script_loader import HotkeyScriptLoader
from lib.ensures_single_instance import ensure_single_instance


def main():
    hotkeys_dir = get_src_root() / "hotkeys"
    hotkeys_dir.mkdir(parents=True, exist_ok=True)

    if "--worker" in sys.argv:
        if not ensure_single_instance("hotkey_listener"):
            print("[Hotkey Listener] Another instance is running. Exiting worker.", flush=True)
            sys.exit(0)

        pid_file = hotkeys_dir / "hotkey_listener.pid"
        pid_file.write_text(str(os.getpid()))

        loader = HotkeyScriptLoader(hotkeys_dir)
        listener = ComboListener(loader.on_combo, verbose=False)

        print("[+] Hotkey listener active.", flush=True)
        try:
            listener.start()
        except Exception as e:
            print(f"[ERROR] Hotkey listener encountered an error: {e}", file=sys.stderr, flush=True)
            raise
        finally:
            if pid_file.exists():
                try:
                    pid_file.unlink()
                except Exception:
                    pass
        return

    # Direct CLI launcher fallback
    env = os.environ.copy()
    env["PYTHONPATH"] = str(get_src_root())
    env["PYTHONUNBUFFERED"] = "1"
    python_exec = sys.executable.lower().replace("pythonw.exe", "python.exe")

    try:
        subprocess.Popen(
            [python_exec, __file__, "--worker"],
            env=env
        )
        print("Hotkey listener started.", flush=True)
    except Exception as e:
        print(f"Failed to start hotkey listener: {e}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()