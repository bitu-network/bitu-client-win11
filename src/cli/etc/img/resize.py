# file: src/cli/etc/img/resize.py
import os
import sys
import io
from PIL import Image

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}

def resize_image(image_path, new_width=None, new_height=None, max_bytes=None):
    with Image.open(image_path) as img:
        width, height = img.size

        # Determine new dimensions while keeping aspect ratio if needed
        if new_width and not new_height:
            ratio = new_width / width
            new_height = int(height * ratio)
        elif new_height and not new_width:
            ratio = new_height / height
            new_width = int(width * ratio)
        elif not new_width or not new_height:
            raise ValueError("Either width or height must be specified.")

        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        if max_bytes:
            quality = 95
            buffer = io.BytesIO()
            resized_img.save(buffer, format=img.format, quality=quality)
            while buffer.getbuffer().nbytes > max_bytes and quality > 10:
                buffer = io.BytesIO()
                quality -= 5
                resized_img.save(buffer, format=img.format, quality=quality)
            with open(image_path, "wb") as f:
                f.write(buffer.getvalue())
        else:
            resized_img.save(image_path)

        print(f"Resized: {image_path} → {new_width}x{new_height}")

def parse_args():
    width = None
    height = None
    max_bytes = None

    for arg in sys.argv[1:]:
        if arg.startswith(("-w=", "--width=")):
            try:
                width = int(arg.split("=", 1)[1])
            except ValueError:
                print("Error: width must be an integer.")
                sys.exit(1)
        elif arg.startswith(("-h=", "--height=")):
            try:
                height = int(arg.split("=", 1)[1])
            except ValueError:
                print("Error: height must be an integer.")
                sys.exit(1)
        elif arg.startswith("--max="):
            try:
                max_bytes = int(arg.split("=", 1)[1])
            except ValueError:
                print("Error: max_bytes must be an integer.")
                sys.exit(1)
        else:
            print(f"Unknown argument: {arg}")
            sys.exit(1)

    if not width and not height:
        print("Error: you must specify either -w=<pixels> or -h=<pixels>.")
        sys.exit(1)

    return width, height, max_bytes

def main():
    width, height, max_bytes = parse_args()

    files = sorted(os.listdir("."))
    for filename in files:
        name, ext = os.path.splitext(filename)
        if ext.lower() in IMAGE_EXTS:
            resize_image(filename, width, height, max_bytes)

if __name__ == "__main__":
    main()
