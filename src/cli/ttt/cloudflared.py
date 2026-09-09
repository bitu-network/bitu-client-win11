# file: src/cli/ttt/cloudflared.py


import subprocess

subprocess.Popen(
    ["cloudflared", "tunnel", "--url", "http://127.0.0.1:8000"]
)