# file: src/cli/start.py

import os
import sys
import subprocess
from project import get_project_root, get_src_root


def is_process_running(pid: int) -> bool:
    try:
        if os.name == 'nt':
            res = subprocess.run(
                ["tasklist", "/fi", f"PID eq {pid}"],
                capture_output=True,
                text=True
            )
            return str(pid) in res.stdout
        else:
            os.kill(pid, 0)
            return True
    except Exception:
        return False


def start_background_hotkeys(project_root, src_dir):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(src_dir)
    env["PYTHONUNBUFFERED"] = "1"
    try:
        # Launch worker directly to stream hotkey errors to the same terminal
        hotkeys_script = src_dir / "cli" / "hotkeys" / "start.py"
        return subprocess.Popen(
            [sys.executable, str(hotkeys_script), "--worker"],
            cwd=str(project_root),
            env=env,
            stdout=None,
            stderr=None
        )
    except Exception as e:
        print(f"[ERROR] Failed to start hotkey listener: {e}", file=sys.stderr, flush=True)
        return None


def stop_background_hotkeys(project_root, src_dir):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(src_dir)
    try:
        subprocess.run(
            [sys.executable, "-m", "cli.hotkeys.stop"],
            cwd=str(project_root),
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
    except Exception:
        pass


def main():
    project_root = get_project_root()
    src_dir = get_src_root()

    pid_file = src_dir / "tray" / "tray.pid"
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            if is_process_running(pid):
                print("Bitu tray is already running.", flush=True)
                return
        except Exception:
            pass

    env = os.environ.copy()
    env["PYTHONPATH"] = str(src_dir)
    env["PYTHONUNBUFFERED"] = "1"

    tray_main = src_dir / "tray" / "main.py"
    python_executable = sys.executable.lower().replace("pythonw.exe", "python.exe")

    print("=== Launching BITU Services (Console Output Active) ===", flush=True)
    hotkey_proc = start_background_hotkeys(project_root, src_dir)
    
    tray_proc = None
    try:
        tray_proc = subprocess.Popen(
            [python_executable, str(tray_main)],
            cwd=str(project_root),
            env=env,
            stdout=None,
            stderr=None
        )
        pid_file.write_text(str(tray_proc.pid))
        print("[+] Bitu tray started successfully.", flush=True)
        
        tray_proc.wait()
    except KeyboardInterrupt:
        print("\n[!] Terminal closed or interrupted. Shutting down services...", flush=True)
    except Exception as e:
        print(f"[ERROR] Tray orchestration failure: {e}", file=sys.stderr, flush=True)
        sys.exit(1)
    finally:
        if pid_file.exists():
            try:
                pid_file.unlink()
            except Exception:
                pass
        if tray_proc and tray_proc.poll() is None:
            tray_proc.terminate()
        if hotkey_proc and hotkey_proc.poll() is None:
            hotkey_proc.terminate()
        stop_background_hotkeys(project_root, src_dir)
        print("[+] All services terminated cleanly.", flush=True)


if __name__ == "__main__":
    main()