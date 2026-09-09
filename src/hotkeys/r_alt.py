# file: src/hotkeys/r_alt.py

import ctypes
import os
import subprocess
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from PIL import Image, ImageTk

from lib.hotkey_context import get_context_fields

# Reconfigure stdout/stderr for safe UTF-8 printing on Windows
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

# Ensure project root is in sys.path when invoked via hotkey
root_dir = (
    Path(__file__).resolve().parent.parent if "__file__" in globals() else Path.cwd()
)
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff")


def force_windows_shell_refresh(path, is_item=False):
    if os.path.exists(path):
        os.utime(path, None)
        SHCNE_UPDATEDIR = 0x00001000
        SHCNE_UPDATEITEM = 0x00002000
        SHCNF_PATHW = 0x0005

        flag = SHCNE_UPDATEITEM if is_item else SHCNE_UPDATEDIR
        ctypes.windll.shell32.SHChangeNotify(
            flag, SHCNF_PATHW, ctypes.c_wchar_p(path), None
        )


def evict_windows_thumbnail_cache(path):
    """Bumps file/folder modification time to force Windows to drop the old cached thumbnail."""
    try:
        stat = os.stat(path)
        new_mtime = time.time()
        os.utime(path, (stat.st_atime, new_mtime))
    except Exception as e:  # noqa: BLE001
        print(f"  [Cache Evict Error] Could not bump timestamp for {path}: {e}")


def resolve_shortcut(path):
    """Resolves a Windows .lnk shortcut to its target path using PowerShell WScript.Shell."""
    if not path.lower().endswith(".lnk"):
        return path
    try:
        safe_path = path.replace("'", "''")
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            f"$sh = New-Object -ComObject WScript.Shell; $sc = $sh.CreateShortcut('{safe_path}'); Write-Output $sc.TargetPath",
        ]
        res = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
            creationflags=0x08000000,
        )
        target = res.stdout.strip()
        if target and os.path.exists(target):
            return target
    except Exception:  # noqa: BLE001
        pass
    return path


def crop_face_preview(image_path, target_w=270, target_h=416):
    """Generates a clean center-cropped thumbnail for grid selection."""
    try:
        pil_img = Image.open(image_path)
        w_orig, h_orig = pil_img.size
        target_ratio = target_w / target_h

        if (w_orig / h_orig) > target_ratio:
            crop_h = h_orig
            crop_w = int(h_orig * target_ratio)
        else:
            crop_w = w_orig
            crop_h = int(w_orig / target_ratio)

        crop_x = (w_orig - crop_w) // 2
        crop_y = (h_orig - crop_h) // 2

        cropped = pil_img.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h))
        return cropped.resize((target_w, target_h), Image.Resampling.LANCZOS)
    except Exception as e:  # noqa: BLE001
        print(f"  [Crop Error for {os.path.basename(image_path)}]: {e}")
        return None


class ImageEditorWindow:
    """Interactive modal window allowing the user to pan and zoom the face crop cleanly."""

    def __init__(self, parent, image_path, target_w=270, target_h=416):
        self.top = tk.Toplevel(parent)
        self.top.title("Fine-Tune Face Preview (v2.11)")
        self.top.configure(bg="#222222")
        self.top.grab_set()

        self.top.attributes("-topmost", True)
        self.top.lift()
        self.top.focus_force()
        self.top.after(10, lambda: self.top.attributes("-topmost", False))

        self.image_path = image_path
        self.target_w = target_w
        self.target_h = target_h
        self.pil_img = Image.open(image_path)

        w_orig, h_orig = self.pil_img.size
        target_ratio = target_w / target_h
        if (w_orig / h_orig) > target_ratio:
            self.base_h = h_orig
            self.base_w = int(h_orig * target_ratio)
        else:
            self.base_w = w_orig
            self.base_h = int(w_orig / target_ratio)
        self.base_x = (w_orig - self.base_w) // 2
        self.base_y = (h_orig - self.base_h) // 2

        max_zoom_w = w_orig / self.base_w
        max_zoom_h = h_orig / self.base_h
        self.max_allowed_zoom = min(max_zoom_w, max_zoom_h)

        self.zoom = self.max_allowed_zoom  # Start fully zoomed out
        self.pan_x = 0
        self.pan_y = 0

        self.drag_start_x = 0
        self.drag_start_y = 0

        tk.Label(
            self.top,
            text="Scroll to zoom | Drag to pan",
            fg="#aaaaaa",
            bg="#222222",
            font=("Arial", 9),
        ).pack(pady=(10, 5))

        self.disp_w = int(target_w * 1.2)
        self.disp_h = int(target_h * 1.2)
        self.canvas = tk.Canvas(
            self.top,
            width=self.disp_w,
            height=self.disp_h,
            bg="#111111",
            highlightthickness=0,
        )
        self.canvas.pack(padx=15, pady=5)

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<MouseWheel>", self.on_wheel)

        btn_frame = tk.Frame(self.top, bg="#222222")
        btn_frame.pack(pady=(10, 15))

        tk.Button(
            btn_frame,
            text="Reset",
            command=self.reset_view,
            bg="#444444",
            fg="white",
            width=10,
        ).pack(side="left", padx=5)
        tk.Button(
            btn_frame,
            text="Confirm",
            command=self.confirm,
            bg="#007acc",
            fg="white",
            width=12,
            font=("Arial", 10, "bold"),
        ).pack(side="left", padx=5)

        self.result_image = None
        self.update_preview()

    def on_press(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def on_drag(self, event):
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        self.drag_start_x = event.x
        self.drag_start_y = event.y

        scale_factor = self.disp_w / self.target_w
        self.pan_x -= int(dx / scale_factor * self.zoom)
        self.pan_y -= int(dy / scale_factor * self.zoom)
        self.update_preview()

    def on_wheel(self, event):
        step = 0.05
        if event.delta > 0:
            self.zoom = max(0.4, self.zoom - step)
        else:
            self.zoom = min(self.max_allowed_zoom, self.zoom + step)
        self.update_preview()

    def reset_view(self):
        self.zoom = self.max_allowed_zoom
        self.pan_x = 0
        self.pan_y = 0
        self.update_preview()

    def get_transformed_image(self):
        img_w, img_h = self.pil_img.size
        current_zoom = max(0.4, min(self.zoom, self.max_allowed_zoom))

        cur_w = self.base_w * current_zoom
        cur_h = self.base_h * current_zoom

        base_cx = self.base_x + self.base_w / 2
        base_cy = self.base_y + self.base_h / 2

        cur_cx = base_cx + self.pan_x
        cur_cy = base_cy + self.pan_y

        x1 = cur_cx - cur_w / 2
        y1 = cur_cy - cur_h / 2

        x1 = max(0.0, min(x1, img_w - cur_w))
        y1 = max(0.0, min(y1, img_h - cur_h))

        x2 = x1 + cur_w
        y2 = y1 + cur_h

        box = [int(x1), int(y1), int(x2), int(y2)]
        cropped = self.pil_img.crop((box[0], box[1], box[2], box[3]))
        return cropped.resize((self.target_w, self.target_h), Image.Resampling.LANCZOS)

    def update_preview(self):
        try:
            img = self.get_transformed_image()
            display_img = img.copy().resize(
                (self.disp_w, self.disp_h), Image.Resampling.LANCZOS
            )
            self.tk_img = ImageTk.PhotoImage(display_img)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
        except Exception as e:  # noqa: BLE001
            print(f"Preview update error: {e}")

    def confirm(self):
        self.result_image = self.get_transformed_image()
        self.top.destroy()


def pick_image_interactive(cropped_items, root_window):
    """Spawns grid selection window (v2.11), then opens fine-tuning editor upon selection."""
    selected_result: list[Image.Image | None] = [None]
    sub_root = tk.Toplevel(root_window)
    sub_root.title("Select Face Preview Thumbnail (v2.11)")
    sub_root.configure(bg="#222222")
    sub_root.grab_set()

    sub_root.attributes("-topmost", True)
    sub_root.lift()
    sub_root.focus_force()
    sub_root.after(10, lambda: sub_root.attributes("-topmost", False))

    frame = tk.Frame(sub_root, bg="#222222")
    frame.pack(padx=15, pady=15)

    tk.Label(
        frame,
        text="Select a face to fine-tune:",
        fg="white",
        bg="#222222",
        font=("Arial", 11, "bold"),
    ).grid(row=0, column=0, columnspan=3, pady=(0, 10))

    row, col = 1, 0
    display_size = (117, 180)
    images_cache = []

    def on_select(path):
        sub_root.destroy()
        editor = ImageEditorWindow(root_window, path)
        root_window.wait_window(editor.top)
        selected_result[0] = editor.result_image

    for path, cropped_img in cropped_items[:9]:
        try:
            display_img = cropped_img.copy()
            display_img.thumbnail(display_size, Image.Resampling.LANCZOS)

            tk_img = ImageTk.PhotoImage(display_img)
            images_cache.append(tk_img)

            btn = tk.Button(
                frame,
                image=tk_img,
                command=lambda p=path: on_select(p),
                bg="#333333",
                activebackground="#555555",
                bd=2,
            )
            btn.grid(row=row, column=col, padx=6, pady=6)

            col += 1
            if col > 2:
                col = 0
                row += 1
        except Exception:  # noqa: BLE001, S112
            continue

    root_window.wait_window(sub_root)
    return selected_result[0]


# --- Main Execution Block ---
application, selected = get_context_fields("application", "selected_items")

if application == "explorer.exe" and selected:
    print("\nScanning folders for face close-ups...")

    main_root = tk.Tk()
    main_root.withdraw()

    try:
        updated_count = 0
        for raw_path in selected:
            target_path = resolve_shortcut(raw_path)

            if not os.path.isdir(target_path):
                continue

            # destination_preview = os.path.join(target_path, "folder.jpg")
            # if os.path.exists(destination_preview) and raw_path.lower().endswith(".lnk") and os.path.getmtime(destination_preview) > os.path.getmtime(raw_path):
            #     print(f"  [Cache Sync] folder.jpg is newer than shortcut {os.path.basename(raw_path)}. Refreshing thumbnail...")
            #     evict_windows_thumbnail_cache(target_path)
            #     force_windows_shell_refresh(target_path, is_item=True)
            #     evict_windows_thumbnail_cache(raw_path)
            #     force_windows_shell_refresh(raw_path, is_item=True)
            #     continue

            sub_folder = os.path.join(target_path, "'")
            if not os.path.isdir(sub_folder):
                print(
                    f"  [-] Subfolder ''' not found in: {os.path.basename(target_path)}"
                )
                messagebox.showwarning(
                    "Missing Subfolder",
                    f"Subfolder ''' not found in:\n{os.path.basename(target_path)}",
                )
                continue

            valid_crops = []
            for file in os.listdir(sub_folder):
                file_lower = file.lower()
                if file_lower.endswith(IMAGE_EXTENSIONS):
                    full_path = os.path.join(sub_folder, file)

                    cropped_img = crop_face_preview(full_path)
                    if cropped_img:
                        valid_crops.append((full_path, cropped_img))

            if not valid_crops:
                print(
                    f"  [-] No processable images found inside ''' for {os.path.basename(target_path)}"
                )
                continue

            final_preview = pick_image_interactive(valid_crops, main_root)

            if final_preview:
                print(
                    f"  [Processing] Saving custom-adjusted face preview for {os.path.basename(target_path)}"
                )
                updated_count += 1

                # Apply pi/2 CCW rotation (90 degrees counter-clockwise) before saving
                final_preview = final_preview.rotate(90, expand=True)

                destination_preview = os.path.join(target_path, "folder.jpg")

                if os.path.exists(destination_preview):
                    os.system(f'attrib -h -s "{destination_preview}"')

                final_preview.convert("RGB").save(destination_preview, "JPEG")
                os.system(f'attrib +h +s "{destination_preview}"')

                evict_windows_thumbnail_cache(target_path)
                force_windows_shell_refresh(target_path, is_item=True)

                if raw_path.lower().endswith(".lnk"):
                    evict_windows_thumbnail_cache(raw_path)
                    force_windows_shell_refresh(raw_path, is_item=True)

        if updated_count > 0:
            print(f"Done! {updated_count} folder preview(s) updated successfully.")
        else:
            print(
                "[-] No folder previews were updated (skipped or missing source images)."
            )
    except Exception as e:  # noqa: BLE001
        print(f"Error processing face previews: {e}")
    finally:
        main_root.destroy()
else:
    print("[-] No folders selected or not in Windows Explorer.")
