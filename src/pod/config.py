# file: src/pod/config.py

import sqlite3
from pathlib import Path
from typing import Any
import sys

if sys.platform == "win32":
    import win32crypt
else:
    win32crypt = None  # placeholder, implement alternative for Linux/Mac

DEFAULT_POD_PATH = Path.cwd() / ".pod"  # default pod file containing config table

class ConfigError(Exception):
    pass

class Config:
    def __init__(self, pod_path: Path = DEFAULT_POD_PATH):
        self.pod_path = pod_path

    def set_value(self, key: str, value: Any, encrypt: bool = False) -> None:
        val_to_store = str(value)
        if encrypt:
            if not win32crypt:
                raise ConfigError("Encryption not supported on this platform")
            val_to_store = win32crypt.CryptProtectData(
                val_to_store.encode("utf-8"), "", None, None, None, 0
            )
        try:
            conn = sqlite3.connect(self.pod_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO config(key, value) VALUES(?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """, (key, val_to_store))
            conn.commit()
            conn.close()
        except Exception as e:
            raise ConfigError(f"Failed to set value in config: {e}") from e

    def get_value(self, key: str, decrypt: bool = False, default: Any = None) -> Any:
        try:
            conn = sqlite3.connect(self.pod_path)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM config WHERE key=?", (key,))
            row = cursor.fetchone()
            conn.close()
            if not row:
                return default
            val = row[0]
            if decrypt:
                if not win32crypt:
                    raise ConfigError("Decryption not supported on this platform")
                val = win32crypt.CryptUnprotectData(val, None, None, None, 0)[1].decode("utf-8")
            return val
        except Exception as e:
            raise ConfigError(f"Failed to get value from config: {e}") from e

    def delete_value(self, key: str) -> None:
        try:
            conn = sqlite3.connect(self.pod_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM config WHERE key=?", (key,))
            conn.commit()
            conn.close()
        except Exception as e:
            raise ConfigError(f"Failed to delete value from config: {e}") from e


if __name__ == "__main__":
    cfg = Config()
    cfg.set_value("api_key", "ABC123", encrypt=True)
    cfg.set_value("counter", 42)
    print("api_key:", cfg.get_value("api_key", decrypt=True))
    print("counter:", cfg.get_value("counter"))
