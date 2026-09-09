# file: src/cli/yt-dlp.py
import sys
import yt_dlp

if __name__ == "__main__":
    try:
        sys.exit(yt_dlp.main())
    except Exception as e:
        print(f"[ERROR] {e}")
        if sys.platform == "win32":
            input("\n[!] Press Enter to close...")
        sys.exit(1)