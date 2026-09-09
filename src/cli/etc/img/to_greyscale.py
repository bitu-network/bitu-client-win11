# file: src/cli/etc/img/to_greyscale.py
# from PIL import Image

# # adjustable parameters
# QUALITY = 75          # AVIF compression quality (0–100)
# GRAY_LEVELS = 16      # number of gray shades (lower = smaller file, 16–64 recommended)

# # supported formats
# input_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif', '.webp')

# def posterize_gray(img, levels):
#     step = 256 // levels
#     return img.point(lambda x: int(x // step) * step)

# for filename in os.listdir('.'):
#     if filename.lower().endswith(input_formats):
#         try:
#             with Image.open(filename) as img:
#                 # convert to grayscale
#                 gray = img.convert('L')
#                 # apply tone reduction (keeps smooth but compact shades)
#                 gray = posterize_gray(gray, GRAY_LEVELS)
#                 # overwrite with compact AVIF version
#                 gray.save(filename, format='AVIF', quality=QUALITY, bits=8)
#                 print(f"Replaced {filename} with compact grayscale AVIF")
#         except Exception as e:
#             print(f"Failed to process {filename}: {e}")

# --quality = 0-100
# --level = 2 to 256

import os
import argparse
from PIL import Image

# Supported input formats
INPUT_FORMATS = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif', '.webp')

def posterize_gray(img, levels):
    step = 256 // levels
    return img.point(lambda x: int(x // step) * step)

def main():
    parser = argparse.ArgumentParser(
        description="Convert all images in current directory to compact grayscale AVIF."
    )
    parser.add_argument("--level", type=int, default=32, help="Number of gray shades (default: 32)")
    parser.add_argument("--quality", type=int, default=75, help="AVIF compression quality 0–100 (default: 75)")
    args = parser.parse_args()

    print(f"Using {args.level} gray levels and quality={args.quality}")

    for filename in os.listdir('.'):
        if filename.lower().endswith(INPUT_FORMATS):
            try:
                with Image.open(filename) as img:
                    gray = img.convert('L')
                    gray = posterize_gray(gray, args.level)
                    gray.save(filename, format='AVIF', quality=args.quality, bits=8)
                    print(f"Replaced {filename} with compact grayscale AVIF")
            except Exception as e:
                print(f"Failed to process {filename}: {e}")

if __name__ == "__main__":
    main()
