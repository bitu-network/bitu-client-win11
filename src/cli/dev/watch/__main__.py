# file: src/cli/dev/watch/__main__.py

import threading

from cli.dev.watch import filepath_header_injector, tree_snapshot
from project import get_project_root

if __name__ == "__main__":
    project_root = get_project_root()
    tree_out_path = project_root / tree_snapshot.DEFAULT_OUT_DIR / tree_snapshot.DEFAULT_OUT_NAME
    tree_out_path.parent.mkdir(parents=True, exist_ok=True)

    threading.Thread(
        target=tree_snapshot.watch_loop,
        args=(project_root, tree_out_path),
        daemon=True,
    ).start()

    # Blocks forever, keeping the process (and the daemon thread above) alive.
    filepath_header_injector.main()