# file: src/cli/ttt/webpage.py
import http.server
import socketserver
from pathlib import Path

PORT = 8080
HTML_NAME = "index.html"

HTML_FILE = Path.cwd() / HTML_NAME

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", f"/{HTML_NAME}"):
            if not HTML_FILE.exists():
                self.send_error(404, f"{HTML_NAME} not found in cwd")
                return

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            with open(HTML_FILE, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404)

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        httpd.serve_forever()