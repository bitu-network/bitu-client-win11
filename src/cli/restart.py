# file: src/cli/restart.py
import os
import sys
import subprocess
from project import get_project_root, get_src_root


def main():
    project_root = get_project_root()
    main_script = get_src_root() / "tray" / "main.py"

    if os.name == "nt":
        try:
            subprocess.run(
                [
                    "powershell",
                    "-Command",
                    f"Get-WmiObject Win32_Process | Where-Object {{ $_.CommandLine -like '*{main_script.name}*' -and $_.ProcessId -ne {os.getpid()} }} | ForEach-Object {{ $_.Terminate() }}",
                ],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception:
            pass

    env = os.environ.copy()
    env["PYTHONPATH"] = str(get_src_root())
    subprocess.Popen(
        [sys.executable, str(main_script)],
        cwd=str(project_root),
        env=env,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )


if __name__ == "__main__":
    main()
