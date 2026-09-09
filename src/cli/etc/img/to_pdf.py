# file: src/cli/etc/img/to_pdf.py
import os
from PIL import Image

def main():
    # Supported image extensions
    supported_exts = {".jpg", ".jpeg", ".png", ".bmp", ".tiff",".avif",".webp"}

    # Collect and sort image files
    image_files = sorted(
        [f for f in os.listdir(".") if os.path.splitext(f)[1].lower() in supported_exts]
    )

    if not image_files:
        print("No image files found.")
        return

    images = []
    for i, file in enumerate(image_files):
        img = Image.open(file)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        images.append(img)
        print(f"[{i+1}/{len(image_files)}] Added: {file}")

    # Save all as a single PDF
    output_pdf = "combined.pdf"
    first_image = images[0]
    if len(images) > 1:
        first_image.save(output_pdf, save_all=True, append_images=images[1:])
    else:
        first_image.save(output_pdf)

    print(f"\n✅ Created single PDF: {output_pdf}")

if __name__ == "__main__":
    main()
