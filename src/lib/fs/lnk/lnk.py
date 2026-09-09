# file: src/lib/fs/lnk/lnk.py

from pathlib import Path
import pythoncom
import win32com.client
import os
import traceback
from lib.fs.lnk.lnk_repair import repair_lnk

def resolve_lnk_target(lnk: Path) -> Path | None:
    """
    Resolve the target path of a Windows shortcut (.lnk) file.

    Reads the shortcut metadata and returns the filesystem path that the
    shortcut points to. If the shortcut contains a relative target path,
    the shortcut working directory is used to construct the absolute path.

    If the shortcut target cannot be obtained from its stored metadata,
    the function may attempt to repair the shortcut using Windows native
    IShellLink resolution before retrying the target lookup.

    Args:
        lnk (Path):
            Path to the Windows shortcut (.lnk) file.

    Returns:
        Path | None:
            The resolved target path if successful, otherwise None.

    Notes:
        - Environment variables in the target path are expanded.
        - Surrounding quotes in the target path are removed.
        - The function does not guarantee that the returned path exists.
        - Shortcut repair modifies the .lnk file only when native Windows
            shortcut resolution is invoked.
    """
    initialized = False
    try:
        pythoncom.CoInitialize()
        initialized = True

        shell = win32com.client.Dispatch("WScript.Shell")
        sc = shell.CreateShortcut(str(lnk))
        print("TARGET:", sc.Targetpath)
        print("WORKDIR:", sc.WorkingDirectory)
        print("ARGUMENTS:", sc.Arguments)
        print("DESCRIPTION:", sc.Description)
        target = sc.Targetpath
        workdir = sc.WorkingDirectory

    except Exception:
        traceback.print_exc()
        return None

    finally:
        if initialized:
            pythoncom.CoUninitialize()


    if not target:
        repaired_target = repair_lnk(lnk)
        if repaired_target:
            return repaired_target
        return None

    target = os.path.expandvars(target).strip().strip('"')
    p = Path(target)

    if not p.is_absolute() and workdir:
        p = Path(workdir) / p

    # return p if p.exists() else None
    print("Resolved target:", p)
    return p


def create_lnk(shortcut_path: Path, target_path: Path) -> bool:
    initialized = False
    try:
        pythoncom.CoInitialize()
        initialized = True

        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(str(shortcut_path))

        shortcut.TargetPath = str(target_path)
        shortcut.WorkingDirectory = str(target_path.parent)
        shortcut.save()

        return True

    except Exception:
        traceback.print_exc()
        return False

    finally:
        if initialized:
            pythoncom.CoUninitialize()
