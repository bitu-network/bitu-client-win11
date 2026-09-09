# file: src/cli/etc/yt-dlp.py
#!/usr/bin/env python3
import os
import json
from yt_dlp import YoutubeDL

def main(url):
    ydl_opts = {
        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "merge_output_format": "mp4",
        "outtmpl": "%(title)s.%(ext)s",  # temporary name
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    # Extract metadata
    title = info.get("title", "unknown_title")
    ext = info.get("ext", "mp4")
    video_id = info.get("id", "unknown_id")
    upload_date = info.get("upload_date", "00000000")
    duration = info.get("duration", 0)  # seconds

    # Round to nearest minute, 3 digits
    minutes = int(round(duration / 60.0))
    length_tag = f"{minutes:03d}"

    # Format upload date as YYYY.MM.DD if available
    if len(upload_date) == 8:
        upload_date_fmt = f"{upload_date[:4]}.{upload_date[4:6]}.{upload_date[6:]}"
    else:
        upload_date_fmt = "0000.00.00"

    # Build final filename
    final_name = f"[{upload_date_fmt}~][{length_tag}] {title} [{video_id}].{ext}"

    # Rename downloaded file
    original = f"{title}.{ext}"
    if os.path.exists(original):
        os.rename(original, final_name)
        print(f"Renamed to: {final_name}")
    else:
        print(f"Downloaded file not found: {original}")

    # Save metadata to JSON
    # json_filename = f"[{upload_date_fmt}~][{length_tag}] {title} [{video_id}].json"
    # with open(json_filename, "w", encoding="utf-8") as f:
    #     json.dump(info, f, ensure_ascii=False, indent=4)
    # print(f"Metadata saved to: {json_filename}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python download_with_tag.py <URL>")
        sys.exit(1)
    main(sys.argv[1])
