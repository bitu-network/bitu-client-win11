# file: src/cli/show/clipboard_as_qrcode.py
import sys
import pyperclip
import qrcode
from qrcode.constants import ERROR_CORRECT_L
from qrcode.image.pil import PilImage  # Fix: Explicitly import the Pillow image factory

def clipboard_to_qrcode():
    # Retrieve text from the clipboard
    text = pyperclip.paste()
    
    # Check if the clipboard is empty or only contains whitespace
    if not text or text.strip() == "":
        print("Error: Clipboard is empty or does not contain valid text.")
        return

    print(f"Content found in clipboard (first 50 chars): {text[:50]}...")
    print("Generating and displaying QR code...")

    # Configure the QR code settings
    qr = qrcode.QRCode(
        version=1,
        error_correction=ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    # Add data and build the matrix
    qr.add_data(text)
    qr.make(fit=True)

    # Fix: Pass image_factory=PilImage to guarantee standard Pillow behavior
    img = qr.make_image(image_factory=PilImage, fill_color="black", back_color="white")
    
    # Display the image on screen using your OS default image viewer
    img.show()

if __name__ == "__main__":
    clipboard_to_qrcode()
