# file: src/install.py
import os
from pathlib import Path
import re
import subprocess
import sys


def setup_virtual_environment(project_root: Path) -> Path:
    venv_dir = project_root / ".venv"
    if os.name == "nt":
        venv_python = venv_dir / "Scripts" / "python.exe"
    else:
        venv_python = venv_dir / "bin" / "python"

    if not venv_python.exists():
        print(f"[*] Creating virtual environment in {venv_dir}...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        print("[*] Virtual environment created.")

    req_file = project_root / "requirements.txt"
    if req_file.exists():
        print("[*] Installing / updating dependencies from requirements.txt...")
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "--upgrade", "pip"],
            check=True,
        )
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "-r", str(req_file)],
            check=True,
        )
        print("[+] Dependencies successfully installed.")

    return venv_python


def install_startup_hook(project_root: Path, venv_python: Path):
    startup_dir = Path(
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")
    )
    startup_dir.mkdir(parents=True, exist_ok=True)

    startup_bat_path = startup_dir / "bitu.bat"

    bat_content = [
        "@echo off",
        "title BITU",
        f'cd /d "{project_root}"',
        'set "PYTHONPATH=src"',
        f'"{venv_python}" -m cli.start',
    ]

    startup_bat_path.write_text("\n".join(bat_content) + "\n", encoding="utf-8")
    print(f"Generated startup batch file at:\n{startup_bat_path}")


def get_macro_file_path():
    try:
        result = subprocess.run(
            [
                "reg",
                "query",
                r"HKCU\Software\Microsoft\Command Processor",
                "/v",
                "Autorun",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        match = re.search(
            r'doskey\s+/macrofile=["\']?([^"\']+)["\']?',
            result.stdout,
            re.IGNORECASE,
        )
        if match:
            potential_path = Path(match.group(1))
            if potential_path.exists():
                return potential_path
    except Exception:
        pass

    default_drive = os.environ.get("SystemDrive", "C:").rstrip(":")
    prompt = f"Enter your persistent drive letter [default: {default_drive}]: "
    choice = input(prompt).strip().rstrip(":\\").upper()

    target_drive = choice if choice else default_drive
    macro_dir = Path(f"{target_drive}:\\") / "I" / "-" / "doskey"
    macro_dir.mkdir(parents=True, exist_ok=True)
    return macro_dir / "macros.doskey"


def install_doskey_macros(project_root: Path, venv_python: Path):
    cli_main = project_root / "src" / "cli" / "__main__.py"
    macro_file = get_macro_file_path()

    reg_command = f'doskey /macrofile="{macro_file}"'
    subprocess.run(
        [
            "reg",
            "add",
            r"HKCU\Software\Microsoft\Command Processor",
            "/v",
            "Autorun",
            "/d",
            reg_command,
            "/f",
        ],
        check=True,
    )
    print(f"Configured registry Autorun with macro file:\n{macro_file}")

    new_macros = [
        f'bitu="{venv_python}" "{cli_main}" $*',
        f'u="{venv_python}" "{cli_main}" $*',
    ]

    existing_lines = (
        macro_file.read_text(encoding="utf-8").splitlines()
        if macro_file.exists()
        else []
    )
    retained_lines = [
        line
        for line in existing_lines
        if not line.strip().startswith("bitu=") and not line.strip().startswith("u=")
    ]

    final_lines = retained_lines + new_macros
    macro_file.write_text("\n".join(final_lines) + "\n", encoding="utf-8")
    print(f"Configured CLI macros in:\n{macro_file}")


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    venv_python = setup_virtual_environment(project_root)
    install_startup_hook(project_root, venv_python)
    install_doskey_macros(project_root, venv_python)