# file: src/cli/dev/ttt/download_blob.py
import sys
from pathlib import Path
import requests


def download_blob(server_url: str, blob_hash: str):
    """
    Download a blob from the given server URL and save it in the current folder
    using <hash>.<extension>.
    """
    url = f"{server_url}/{blob_hash}"
    resp = requests.get(url)
    if resp.status_code != 200:
        print(f"[x] Failed to download: HTTP {resp.status_code}")
        return

    # Extract extension from Content-Disposition filename
    cd = resp.headers.get("Content-Disposition", "")
    ext = ""
    if "filename=" in cd:
        original_name = cd.split("filename=")[1].strip('"')
        # Handle hidden file starting with a dot
        name_part = Path(original_name).name
        if "." in name_part:
            ext = "." + name_part.split(".")[-1]
        else:
            ext = ""

    filename = blob_hash + ext
    out_path = Path.cwd() / filename
    out_path.write_bytes(resp.content)
    print(f"[✓] Blob saved to {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python download_blobs.py <server_url> <blob_hash>")
        sys.exit(1)

    server_url = sys.argv[1]
    blob_hash = sys.argv[2]
    download_blob(server_url, blob_hash)
