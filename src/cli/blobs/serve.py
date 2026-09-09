# file: src/cli/blobs/serve.py
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from pod.paths import get_blobs_root

PORT = 8080


def blob_exists(blobs_root: Path, blob_hash: str) -> Path | None:
    """
    Return blob file path if blob exists, else None.
    """
    blob_dir = blobs_root / blob_hash
    if not blob_dir.is_dir():
        return None

    files = list(blob_dir.glob(".*"))  # hidden file inside hash folder
    return files[0] if files else None


class ArchiveHandler(BaseHTTPRequestHandler):

    def do_HEAD(self):
        blob_hash = self.path.strip("/")
        blobs_root = get_blobs_root(Path.cwd())

        if not blobs_root or len(blob_hash) != 64:
            self.send_error(404)
            return

        blob_file = blob_exists(blobs_root, blob_hash)
        if not blob_file:
            self.send_error(404)
            return

        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"""
                <html><body>
                <h2>Archive Server</h2>
                <p>GET /&lt;sha256&gt; to fetch a blob</p>
                <p>HEAD /&lt;sha256&gt; to test existence</p>
                </body></html>
            """)
            return

        blob_hash = self.path.strip("/")
        blobs_root = get_blobs_root(Path.cwd())

        if not blobs_root or len(blob_hash) != 64:
            self.send_error(404)
            return

        blob_file = blob_exists(blobs_root, blob_hash)
        if not blob_file:
            self.send_error(404, "Blob not found on this pod")
            return

        # Serve the blob and inform client of original filename/extension
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header(
            "Content-Disposition",
            f'attachment; filename="{blob_file.name}"'
        )
        self.end_headers()

        try:
            with blob_file.open("rb") as f:
                self.wfile.write(f.read())
        except ConnectionAbortedError:
            pass


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), ArchiveHandler)
    print(f"[✓] Blob server running at http://127.0.0.1:{PORT}/")
    server.serve_forever()
