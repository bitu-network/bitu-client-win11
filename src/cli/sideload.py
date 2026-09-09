# file: src/cli/sideload.py

import os
import sys
import shutil
from pathlib import Path
# from win32com.client import Dispatch
import pythoncom
from win32com.shell import shell, shellcon
from pathlib import Path

def resolve_shortcut(path: Path) -> Path | None:
    """Return the target path of a .lnk file (Unicode-safe)."""
    try:
        pythoncom.CoInitialize()
        shell_link = pythoncom.CoCreateInstance(
            shell.CLSID_ShellLink, None,
            pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink
        )
        persist_file = shell_link.QueryInterface(pythoncom.IID_IPersistFile)
        persist_file.Load(str(path), 0)
        target_path, _ = shell_link.GetPath(shell.SLGP_UNCPRIORITY)
        if target_path:
            return Path(target_path)
    except Exception:
        return None


def copy_and_prepend_unicode(scan_path, recursive=False):
    """Copy target files of .lnk shortcuts into CWD, prepending their shortcut names (Unicode-safe)."""
    scan_path = Path(scan_path)
    cwd = Path.cwd()

    for lnk_file in scan_path.glob("*.lnk"):
        target_path = resolve_shortcut(lnk_file)
        if not target_path or not target_path.exists():
            continue

        try:
            src = target_path.resolve()
            dest_temp = cwd / src.name

            # Copy file to current working directory
            shutil.copy2(src, dest_temp)

            # Prepend shortcut's stem (Unicode-safe)
            new_name = f"{lnk_file.stem}_{src.name}"
            final_dest = cwd / new_name

            # Rename safely
            shutil.move(dest_temp, final_dest)

            print(f"Copied: {lnk_file.name} → {new_name}")

        except Exception as e:
            print(f"Failed to copy {lnk_file}: {e}")

    if recursive:
        for subfolder in scan_path.iterdir():
            if subfolder.is_dir():
                copy_and_prepend_unicode(subfolder, recursive=True)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: biou sideload <path> [--recursive]")
        sys.exit(1)

    scan_path = sys.argv[1]
    recursive_flag = len(sys.argv) > 2 and sys.argv[2].lower() == "--recursive"
    copy_and_prepend_unicode(scan_path, recursive_flag)






'''This Python script is designed to copy the targets of Windows shortcut files (.lnk) into the current working directory, optionally doing so recursively for subfolders, while prefixing the copied file with the original shortcut name.'''