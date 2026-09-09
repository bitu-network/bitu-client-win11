# file: src/pod/folders.py

import shutil
from pathlib import Path

from pod.paths import concepts_root
from lib.fs.lnk.lnk import create_lnk


def move_folder_to_concepts(folder: Path) -> None:
    """
    Move a folder into the pod personal concepts root and leave a .lnk shortcut
    with the same name in the original location.

    If the destination folder already exists, merge the source folder into it.
    """

    folder = folder.resolve()

    if not folder.exists() or not folder.is_dir():
        raise ValueError(f"Not a valid folder: {folder}")

    original_parent = folder.parent

    destination = concepts_root(folder) / folder.name

    if destination.exists():

        print(f"Merging into existing concept folder: {destination}")

        shutil.copytree(
            folder,
            destination,
            dirs_exist_ok=True,
        )

        shutil.rmtree(folder)

    else:

        shutil.move(
            str(folder),
            str(destination),
        )

    # Recreate shortcut where the folder used to be
    shortcut_path = original_parent / f"{folder.name}.lnk"

    ok = create_lnk(
        shortcut_path,
        destination,
    )

    if not ok:
        print(f"Warning: failed to create shortcut: {shortcut_path}")
