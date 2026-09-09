# file: src/cli/lnk/to_hardlink.py

import os
import shutil
import tempfile
from pathlib import Path
from pylnk3 import Lnk
import win32com.client


from lib.hotkey_context import get_context_fields


def resolve_lnk(lnk_path):
    """Resolves a .lnk file using pylnk3 with a WScript.Shell temp copy fallback."""
    path = Path(lnk_path)

    # Try pylnk3 first
    try:
        target = Lnk(str(path)).path
        if target:
            expanded = os.path.expandvars(target)
            target_path = Path(expanded)
            if not target_path.is_absolute():
                target_path = (path.parent / target_path).resolve()
            return str(target_path)
    except Exception:  # noqa: BLE001
        pass

    # Fallback: Copy to a temporary safe name to bypass special characters/pipes
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".lnk") as tmp:
            tmp_path = Path(tmp.name)
        shutil.copy2(path, tmp_path)

        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(str(tmp_path))
        target = shortcut.TargetPath
        if target:
            expanded = os.path.expandvars(target)
            target_path = Path(expanded)
            if not target_path.is_absolute():
                target_path = (path.parent / target_path).resolve()
            return str(target_path)
    except Exception as e:  # noqa: BLE001
        print(f"[!] Failed to resolve shortcut {lnk_path}: {e}")
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)

    return None


def convert_lnk_to_hardlink(lnk_path):
    """Resolves a shortcut and creates a hard link to the target file."""
    path = Path(lnk_path)
    if not path.exists() or path.suffix.lower() != ".lnk":
        print(f"[!] Invalid shortcut: {lnk_path}")
        return False

    target_str = resolve_lnk(path)
    if not target_str:
        print(f"[!] Skipped (could not resolve target for): {path.name}")
        return False

    target_path = Path(target_str)
    if not target_path.exists():
        print(f"[!] Target does not exist: {target_path}")
        return False

    # Handle dot-files and clean base names safely (prevents the '..' issue)
    base_name = path.name[:-4] if path.name.lower().endswith(".lnk") else path.stem
    if not base_name or base_name == ".":
        base_name = "dotfile"

    ext = target_path.suffix
    if not ext and target_path.name.startswith("."):
        ext = target_path.name
    hardlink_path = path.parent / f"{base_name}{ext}"


    if hardlink_path.exists():
        print(f"[!] Hardlink already exists: '{hardlink_path.name}'")
        return False

    try:
        # Create NTFS hard link
        os.link(target_path, hardlink_path)
        print(f"[*] Created hardlink: {hardlink_path.name}")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[!] Failed to create hardlink for {path.name}: {e}")
        return False


# Grab active context via your framework library
application, selected = get_context_fields(
    "application",
    "selected_items",
)

if application == "explorer.exe" and selected:
    print("\n[*] Converting selected .lnk files to hard links...")
    converted_count = 0
    successfully_converted = []

    for item in selected:
        if convert_lnk_to_hardlink(item):
            converted_count += 1
            successfully_converted.append(item)

    print(f"[*] Finished. Converted {converted_count} shortcut(s).")

    # Prompt user to delete original .lnk files if any conversions succeeded
    if converted_count > 0:
        shell = win32com.client.Dispatch("WScript.Shell")
        choice = shell.Popup(
            f"Successfully converted {converted_count} shortcut(s) to hard links.\n\nDo you want to delete the original .lnk files?",
            0,
            "Delete Original Shortcuts",
            4 + 32,  # 4 = Yes/No buttons, 32 = Question icon
        )

        # 6 corresponds to the "Yes" button in WScript.Shell Popups
        if choice == 6:
            print("[*] Deleting original .lnk files...")
            for item in successfully_converted:
                p = Path(item)
                try:
                    p.unlink(missing_ok=True)
                    print(f"[*] Deleted original: {p.name}")
                except Exception as e:
                    print(f"[!] Failed to delete original {p.name}: {e}")
        else:
            print("[*] Kept original .lnk files.")
else:
    print("[-] No files selected or not in Windows Explorer.")
