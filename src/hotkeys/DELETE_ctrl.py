# file: src/hotkeys/DELETE_ctrl.py

from pathlib import Path
import tkinter as tk
from tkinter import messagebox
from send2trash import send2trash

from apps.explorer import get_active_explorer_info,redirect_active_explorer
from lib.fs.lnk.lnk import resolve_lnk_target



def build_delete_plan(selected_items: list[Path]) -> list[Path]:
    plan = []

    for item in selected_items:
        if item.suffix.lower() != ".lnk":
            continue

        target = resolve_lnk_target(item)
        print("Target:", target)

        if not target or not target.is_file():
            continue

        parent = target.parent

        remaining_children = [
            child for child in parent.iterdir()
            if child != target
        ]

        if remaining_children:
            redirect_active_explorer(parent)
            return []

        # No siblings: remove shortcut, target, and empty parent
        plan.append(item)
        plan.append(target)
        plan.append(parent)

    return list(dict.fromkeys(plan))


def confirm_delete_plan(plan: list[Path]) -> bool:
    if not plan:
        return False

    text = "The following items will be moved to Recycle Bin:\n\n"
    text += "\n".join(str(p) for p in plan)
    text += "\n\nAre you sure?"

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)  # Forces the dialog to the front

    result = messagebox.askyesno(
        "Confirm deletion",
        text,
        parent=root  # Anchors the dialog to the hidden root
    )

    root.destroy()

    return result


def execute_delete_plan(plan: list[Path]):
    for item in plan:
        if item.exists():
            send2trash(str(item))


folder, selected = get_active_explorer_info()
plan = build_delete_plan(selected)

print("Selected:", selected)
print("Plan:", plan)

if confirm_delete_plan(plan):
    execute_delete_plan(plan)