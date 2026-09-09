# file: src/hotkeys/j_ctrl.py

from pathlib import Path
from lib.hotkey_context import get_context_fields
from apps.explorer import redirect_active_explorer
from pod.paths import pod_root


def run():
    folder_str, = get_context_fields("folder_path")
    if not folder_str:
        raise RuntimeError("No active Explorer folder found in context")
    
    folder = Path(folder_str)
    path = folder.resolve()
    pod_root_dir = pod_root(path)
    c_root = pod_root_dir / "-"
    personal_root = pod_root_dir / "I" / "-"

    # Determine if we are in the personal or public tree
    is_personal = False
    try:
        rel = path.relative_to(personal_root)
        is_personal = True
    except ValueError:
        try:
            rel = path.relative_to(c_root)
        except ValueError:
            raise ValueError("Path must be relative to concept root '-' or personal root 'I/-'")

    parts = rel.parts

    if len(parts) == 1:
        # Single concept: toggle between public and personal trees
        foo = parts[0]
        target = c_root / foo if is_personal else personal_root / foo
        action_desc = "public" if is_personal else "personal"
    elif len(parts) >= 3 and parts[1] == "-":
        # Concept pair (<a>/-/<b>): swap 'a' and 'b' within the same tree root
        a, b = parts[0], parts[2]
        base_root = personal_root if is_personal else c_root
        target = base_root / b / "-" / a
        if len(parts) > 3:
            target = target.joinpath(*parts[3:])
        action_desc = "concept pair swap"
    else:
        raise ValueError(f"Unsupported path structure: {path}")

    target.mkdir(parents=True, exist_ok=True)
    redirect_active_explorer(target)
    print(f"Jumped ({action_desc}): {target}")


if __name__ == "__main__":
    run()