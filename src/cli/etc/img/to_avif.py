# file: src/cli/etc/img/to_avif.py
import os
from PIL import Image

# Make sure you have Pillow >= 10.0.0 for AVIF support
# pip install --upgrade pillow

# Supported input formats
input_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif', '.webp')

for filename in os.listdir('.'):
    if filename.lower().endswith(input_formats):
        try:
            with Image.open(filename) as img:
                new_filename = os.path.splitext(filename)[0] + '.avif'
                img.save(new_filename, format='AVIF', quality=80)  # adjust quality if needed
                print(f'Converted {filename} → {new_filename}')
        except Exception as e:
            print(f'Failed to convert {filename}: {e}')
