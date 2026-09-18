# file: src/server/file_server.py
# description: per-drive live SHA-256 file index. Scans <drive>:\-\ for files, keeps
# a sqlite index cached on the OS drive (fast queries) mirrored back onto the drive
# itself (portability), and serves the index to other BITU services (e.g. a future
# dedupe service) over a local TCP socket.
#
# Launched once per drive by cli/start.py, only for drives with a valid
# <drive>:\I\-\bitu\config.json (see lib/drives.py). Not meant to be run directly
# without a drive-letter argument.

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import socketserver
import sqlite3
import sys
import threading
import time
from pathlib import Path

from lib.drives import load_drive_config

INDEX_MIRROR_REL_PATH = Path("I") / "-" / "bitu" / "index.sqlite"
SCAN_ROOT_REL = Path("-")  # <drive>:\-\

RESCAN_INTERVAL_SECONDS = 30
MIRROR_INTERVAL_SECONDS = 300
HASH_CHUNK_SIZE = 1024 * 1024


def _get_volume_id(drive_root: Path) -> str:
    """Stable-ish identifier for a drive's *contents*, independent of its current
    drive letter -- so the OS-drive cache maps to the right thumbdrive even if it
    gets a different letter next time, or is plugged into a different machine.
    Falls back to the drive letter if the volume serial can't be read.
    """
    kernel32 = ctypes.windll.kernel32
    vol_name_buf = ctypes.create_unicode_buffer(1024)
    fs_name_buf = ctypes.create_unicode_buffer(1024)
    serial = ctypes.c_uint(0)
    max_len = ctypes.c_uint(0)
    flags = ctypes.c_uint(0)
    ok = kernel32.GetVolumeInformationW(
        ctypes.c_wchar_p(str(drive_root)),
        vol_name_buf, ctypes.sizeof(vol_name_buf),
        ctypes.byref(serial), ctypes.byref(max_len), ctypes.byref(flags),
        fs_name_buf, ctypes.sizeof(fs_name_buf),
    )
    if not ok:
        return drive_root.drive.rstrip(":\\").upper()
    return f"{serial.value:08X}"


class FileIndex:
    """Owns the sqlite index for one drive: schema, scanning, and the OS-drive
    cache <-> on-drive mirror relationship.
    """

    def __init__(self, cache_db_path: Path, mirror_db_path: Path, scan_root: Path):
        self.cache_db_path = cache_db_path
        self.mirror_db_path = mirror_db_path
        self.scan_root = scan_root
        self.cache_db_path.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self.cache_db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._init_schema()

    def _init_schema(self):
        with self._lock:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    path TEXT PRIMARY KEY,
                    size INTEGER NOT NULL,
                    mtime REAL NOT NULL,
                    sha256 TEXT,
                    last_seen REAL NOT NULL
                )
            """)
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_files_sha256 ON files(sha256)")
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            self._conn.commit()
        self._set_status("scanning")

    def _set_status(self, status: str):
        with self._lock:
            self._conn.execute(
                "INSERT INTO meta (key, value) VALUES ('status', ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (status,),
            )
            if status == "ready":
                self._conn.execute(
                    "INSERT INTO meta (key, value) VALUES ('last_full_scan_completed_at', ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (str(time.time()),),
                )
            self._conn.commit()

    def get_status(self) -> dict:
        with self._lock:
            rows = self._conn.execute(
                "SELECT key, value FROM meta WHERE key IN ('status', 'last_full_scan_completed_at')"
            ).fetchall()
        return dict(rows)

    @staticmethod
    def _hash_file(path: Path) -> str | None:
        h = hashlib.sha256()
        try:
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(HASH_CHUNK_SIZE), b""):
                    h.update(chunk)
            return h.hexdigest()
        except OSError:
            return None

    def scan_once(self):
        if not self.scan_root.is_dir():
            return

        with self._lock:
            existing = {
                path: (size, mtime)
                for path, size, mtime in self._conn.execute(
                    "SELECT path, size, mtime FROM files"
                ).fetchall()
            }

        now = time.time()
        seen_paths = set()

        for root, _dirs, files in os.walk(self.scan_root):
            for name in files:
                full_path = Path(root) / name
                try:
                    st = full_path.stat()
                except OSError:
                    continue

                path_str = str(full_path)
                seen_paths.add(path_str)
                size, mtime = st.st_size, st.st_mtime

                prev = existing.get(path_str)
                if prev is not None and prev[0] == size and abs(prev[1] - mtime) < 1e-6:
                    with self._lock:
                        self._conn.execute(
                            "UPDATE files SET last_seen=? WHERE path=?", (now, path_str)
                        )
                    continue

                digest = self._hash_file(full_path)
                with self._lock:
                    self._conn.execute(
                        "INSERT INTO files (path, size, mtime, sha256, last_seen) "
                        "VALUES (?, ?, ?, ?, ?) "
                        "ON CONFLICT(path) DO UPDATE SET "
                        "size=excluded.size, mtime=excluded.mtime, "
                        "sha256=excluded.sha256, last_seen=excluded.last_seen",
                        (path_str, size, mtime, digest, now),
                    )
            with self._lock:
                self._conn.commit()

        stale = [p for p in existing if p not in seen_paths]
        if stale:
            with self._lock:
                self._conn.executemany("DELETE FROM files WHERE path=?", [(p,) for p in stale])
                self._conn.commit()

        self._set_status("ready")

    def scan_loop(self):
        while True:
            try:
                self.scan_once()
            except Exception as e:
                print(f"[file_server] Scan error: {e}", file=sys.stderr, flush=True)
            time.sleep(RESCAN_INTERVAL_SECONDS)

    def mirror_to_drive(self):
        """Copy the working index onto the drive itself, so it travels with the
        drive rather than only existing on this machine's OS drive.
        """
        with self._lock:
            self.mirror_db_path.parent.mkdir(parents=True, exist_ok=True)
            dest_conn = sqlite3.connect(str(self.mirror_db_path))
            try:
                self._conn.backup(dest_conn)
            finally:
                dest_conn.close()

    def mirror_loop(self):
        while True:
            time.sleep(MIRROR_INTERVAL_SECONDS)
            try:
                self.mirror_to_drive()
            except OSError as e:
                # Drive may have been unplugged -- don't crash the service over it.
                print(f"[file_server] Mirror error (drive may be disconnected): {e}",
                      file=sys.stderr, flush=True)

    def get_duplicates(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute("""
                SELECT sha256, GROUP_CONCAT(path, char(10)) AS paths, COUNT(*) AS cnt
                FROM files
                WHERE sha256 IS NOT NULL
                GROUP BY sha256
                HAVING cnt > 1
            """).fetchall()
        return [
            {"sha256": sha256, "paths": paths.split("\n"), "count": count}
            for sha256, paths, count in rows
        ]


class RequestHandler(socketserver.StreamRequestHandler):
    """Newline-delimited JSON request/response protocol.

    Requests:  {"cmd": "status"}
               {"cmd": "duplicates"}
    """

    def handle(self):
        index: FileIndex = self.server.index  # type: ignore[attr-defined]
        try:
            raw = self.rfile.readline()
            if not raw:
                return
            request = json.loads(raw.decode("utf-8"))
            cmd = request.get("cmd")

            if cmd == "status":
                response = index.get_status()
            elif cmd == "duplicates":
                response = {"duplicates": index.get_duplicates()}
            else:
                response = {"error": f"unknown cmd: {cmd!r}"}
        except Exception as e:
            response = {"error": str(e)}

        self.wfile.write((json.dumps(response) + "\n").encode("utf-8"))


class FileServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, addr, handler, index: FileIndex):
        super().__init__(addr, handler)
        self.index = index


def main():
    if len(sys.argv) < 2:
        print("[file_server] Usage: file_server.py <drive-letter, e.g. D:>", file=sys.stderr)
        sys.exit(1)

    drive_letter = sys.argv[1].rstrip("\\/").upper()
    if not drive_letter.endswith(":"):
        drive_letter += ":"
    drive_root = Path(drive_letter + "\\")

    config = load_drive_config(drive_root)
    if not config:
        # Drive's config disappeared/became invalid between start.py's check and
        # now (e.g. drive was unplugged). Exit quietly -- this isn't an error.
        print(f"[file_server] No valid config for {drive_root}; exiting.", flush=True)
        sys.exit(0)

    port = config["port"]
    volume_id = _get_volume_id(drive_root)

    os_drive_root = Path(os.environ.get("SystemDrive", "C:") + "\\")
    cache_db_path = os_drive_root / "I" / "-" / "bitu" / volume_id / "index.sqlite"
    mirror_db_path = drive_root / INDEX_MIRROR_REL_PATH
    scan_root = drive_root / SCAN_ROOT_REL

    index = FileIndex(cache_db_path, mirror_db_path, scan_root)

    threading.Thread(target=index.scan_loop, daemon=True).start()
    threading.Thread(target=index.mirror_loop, daemon=True).start()

    server = FileServer(("127.0.0.1", port), RequestHandler, index)
    print(f"[file_server] {drive_root} -> 127.0.0.1:{port} "
          f"(cache={cache_db_path}, mirror={mirror_db_path}, scan_root={scan_root})", flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
