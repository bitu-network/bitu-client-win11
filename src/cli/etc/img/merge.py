# file: src/cli/etc/img/merge.py
import os
import sys
from PIL import Image

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}

def merge_images(image_files, direction):
    images = [Image.open(img).convert("RGBA") for img in image_files]

    # Normalize dimensions
    if direction == "horizontal":
        # Make all images the same height
        min_height = min(img.height for img in images)
        resized = [
            img.resize(
                (int(img.width * min_height / img.height), min_height),
                Image.Resampling.LANCZOS,
            )
            for img in images
        ]
        total_width = sum(img.width for img in resized)
        merged = Image.new("RGBA", (total_width, min_height))
        x = 0
        for img in resized:
            merged.paste(img, (x, 0))
            x += img.width
    else:
        # Make all images the same width
        min_width = min(img.width for img in images)
        resized = [
            img.resize(
                (min_width, int(img.height * min_width / img.width)),
                Image.Resampling.LANCZOS,
            )
            for img in images
        ]
        total_height = sum(img.height for img in resized)
        merged = Image.new("RGBA", (min_width, total_height))
        y = 0
        for img in resized:
            merged.paste(img, (0, y))
            y += img.height

    return merged

def main():
    if len(sys.argv) < 2:
        print("Usage: python merge_images.py [-h|--horizontal | -v|--vertical]")
        sys.exit(1)

    arg = sys.argv[1].lower()
    if arg in ("-h", "--horizontal"):
        direction = "horizontal"
    elif arg in ("-v", "--vertical"):
        direction = "vertical"
    else:
        print("Error: must specify -h/--horizontal or -v/--vertical")
        sys.exit(1)

    files = sorted(os.listdir("."))
    image_files = [f for f in files if os.path.splitext(f)[1].lower() in IMAGE_EXTS]

    if not image_files:
        print("No images found in current directory.")
        sys.exit(1)

    merged = merge_images(image_files, direction)
    output_name = f"merged_{direction}.png"
    merged.save(output_name)
    print(f"Merged image saved as: {output_name}")

if __name__ == "__main__":
    main()
