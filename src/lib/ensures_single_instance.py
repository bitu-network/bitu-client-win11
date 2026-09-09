# file: src/lib/ensures_single_instance.py
import os
import tempfile
import atexit

if os.name == "nt":
    import msvcrt
else:
    import fcntl

class SingleInstance:
    """Ensures that only one instance of a program runs per machine."""

    def __init__(self, name: str):
        """
        :param name: Unique name for the lock file, e.g., "my_program"
        """
        temp_dir = tempfile.gettempdir()
        self.lockfile = os.path.join(temp_dir, f"{name}.lock")
        self.fp = None

    def acquire(self) -> bool:
        """Try to acquire the lock. Returns True if first instance, False if another is already running."""
        try:
            self.fp = open(self.lockfile, "w")
            if os.name == "nt":
                msvcrt.locking(self.fp.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(self.fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Optionally write PID for reference
            self.fp.write(str(os.getpid()))
            self.fp.flush()
            return True
        except (OSError, IOError):
            return False

    def release(self):
        """Release the lock and remove the lock file."""
        try:
            if self.fp:
                if os.name == "nt":
                    self.fp.seek(0)
                    msvcrt.locking(self.fp.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(self.fp, fcntl.LOCK_UN)
                self.fp.close()
                os.remove(self.lockfile)
        except Exception:
            pass

def ensure_single_instance(name: str) -> bool:
    """
    Convenience function to ensure only one instance of a program is running.
    
    :param name: Unique name for the lock file
    :return: True if this is the first instance, False if another is already running
    """
    singleton = SingleInstance(name)
    if singleton.acquire():
        # Keep lock until process exits
        atexit.register(singleton.release)
        return True
    return False
