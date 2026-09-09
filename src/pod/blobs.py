# file: src/pod/blobs.py
import os
import hashlib
import shutil
import pythoncom
from win32com.shell import shell
from pod.paths import blobs_root
from pathlib import Path


def sha256_of_file(filepath: str | Path) -> str:
    """Compute SHA-256 of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def create_shortcut(target_path: Path, shortcut_path: Path) -> None:
    """Create a Windows shortcut pointing to target_path."""
    pythoncom.CoInitialize()
    try:
        shell_link = pythoncom.CoCreateInstance(
            shell.CLSID_ShellLink,
            None,
            pythoncom.CLSCTX_INPROC_SERVER,
            shell.IID_IShellLink,
        )
        shell_link.SetPath(str(target_path))
        # Working directory left blank
        persist_file = shell_link.QueryInterface(pythoncom.IID_IPersistFile)
        persist_file.Save(str(shortcut_path), 0)
    finally:
        pythoncom.CoUninitialize()


def archive_files(file_paths: list[Path], extensions: set[str] | None = None) -> None:
    """
    Process a list of file paths:
      - Store each file in o/<byte1>/<byte2>/<hash>/<original_filename>
      - Create an NTFS hard link in the original folder using the double-dot convention (e.g., foo..jpg)
    """
    if not file_paths:
        print("No files to process.")
        return

    base_path = file_paths[0].parent
    dest_root = blobs_root(base_path)
    if not dest_root or not dest_root.exists():
        print("Aborting: archive 'blobs' folder not found.")
        return

    processed_files = 0

    for file_path in file_paths:
        if not file_path.is_file():
            continue

        ext = file_path.suffix.lower()
        if not ext and file_path.name.startswith("."):
            ext = file_path.name.lower()

        if extensions and ext not in extensions:
            continue

        try:
            file_hash = sha256_of_file(file_path)
            byte1 = file_hash[:2]
            byte2 = file_hash[2:4]

            # CHANGED: Create a dedicated folder container named after the hash
            dest_dir = dest_root / byte1 / byte2 / file_hash
            dest_dir.mkdir(parents=True, exist_ok=True)

            # CHANGED: Store the file inside its hash folder using its original filename
            canonical_path = dest_dir / file_path.name

            if not canonical_path.exists():
                shutil.move(str(file_path), str(canonical_path))
            else:
                file_path.unlink()

            ext_clean = ext.lstrip(".")
            stem = file_path.name[: -len(ext)] if ext else file_path.name
            hardlink_path = file_path.with_name(f"{stem}..{ext_clean}")

            if hardlink_path.exists():
                hardlink_path.unlink()

            os.link(str(canonical_path), str(hardlink_path))

            processed_files += 1
            print(f"\rProcessed files: {processed_files}", end="", flush=True)

        except Exception as e:
            print(f"\nFailed to process {file_path}: {e}")

    print()  # finish line
