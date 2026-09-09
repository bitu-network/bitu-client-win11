# file: src/lib/player.py
import subprocess
import requests
import re
import time
from pathlib import Path

MPC_VARIABLES_URL = "http://localhost:13579/variables.html"

def extract_var(html_text, var_id):
    pattern = rf'<p\s+id="{re.escape(var_id)}">(.*?)</p>'
    match = re.search(pattern, html_text, re.DOTALL | re.IGNORECASE)
    if not match:
        raise ValueError(f"Variable '{var_id}' not found in HTML")
    return match.group(1).strip()

def get_current_file_and_position():
    resp = requests.get(MPC_VARIABLES_URL)
    resp.raise_for_status()
    html = resp.text

    file_path_line = extract_var(html, "filepath")
    file_path = Path(file_path_line).resolve()
    position_ms = int(extract_var(html, "position"))

    return file_path, position_ms


def open_file(file_path, paused=True, wait_ms=500):
    file_path = Path(file_path).resolve()
    try:
        # Open file
        requests.get(f"{MPC_VARIABLES_URL}?wm_command=100&value={file_path}", timeout=1)
        if paused:
            requests.get(f"{MPC_VARIABLES_URL}?wm_command=896", timeout=1)  # pause
    except requests.RequestException:
        pass
    time.sleep(wait_ms / 1000.0)




def close():
    """
    Closes MPC-HC using Windows taskkill.
    """
    try:
        subprocess.run(["taskkill", "/IM", "mpc-hc64.exe", "/F"], check=True)
        print("Player closed.")
    except subprocess.CalledProcessError as e:
        print("Failed to close player:", e)
