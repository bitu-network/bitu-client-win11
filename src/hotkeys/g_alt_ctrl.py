# file: src/hotkeys/g_alt_ctrl.py
# Redirects the active Windows Explorer window to the personal concepts root directory derived from the current folder context.


from apps.explorer import get_active_explorer_info, redirect_active_explorer
from pod.paths import personal_concepts_root


def redirect_active_explorer_to_root() -> bool:
    folder, _ = get_active_explorer_info()

    if not folder:
        return False

    try:
        root = personal_concepts_root(folder)
    except Exception:
        return False

    return redirect_active_explorer(root)


if __name__ == "__main__":
    ok = redirect_active_explorer_to_root()
    print("redirected" if ok else "no active explorer or root not found")