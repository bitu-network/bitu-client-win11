# file: src/hotkeys/w_alt_ctrl_shift.py
# description: print current folder and path relative to .biou root


from apps.explorer import get_active_explorer_info
from pod.paths import interpret_path

def main():
    folder, _ = get_active_explorer_info()
    if not folder:
        print("No active Explorer window detected.")
        return

    folder_path = folder.resolve()
    print(f"Current folder: {folder_path}")

    # relative = get_relative_to_root(folder_path)
    # if relative is None:
    #     print("No .biou root found for this folder.")
    # else:
    #     print(f"Path relative to .biou root: {relative}")



    info = interpret_path(folder_path)
    if not info:
        print("No .biou root found.")
    else:
        print(f"Type: {info['type']}, ID: {info['id']}")

if __name__ == "__main__":
    main()
