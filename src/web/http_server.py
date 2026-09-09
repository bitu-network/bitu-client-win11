# file: src/web/http_server.py

import argparse
import importlib.util
from pathlib import Path
from flask import Flask, send_from_directory, abort, request, redirect

# --- Self-Contained Path & Configuration Setup ---
BIND_HOST = "127.0.0.1"
DEFAULT_LOCAL_PORT = 8000
DEFAULT_PUBLIC_PORT = 9000

# Resolves src/ from src/web/http_server.py[cite: 2]
SRC_ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = SRC_ROOT / "web"
ASSETS_ROOT = WEB_ROOT / "assets"
LOCAL_ROOT = WEB_ROOT / "local"
PUBLIC_ROOT = WEB_ROOT / "public"


def create_app(target_dir: Path) -> Flask:
    app = Flask(__name__)

    # Shared static assets (CSS, JS, fonts)[cite: 2]
    @app.route("/assets/<path:filename>")
    def serve_assets(filename: str):
        asset_path = ASSETS_ROOT / filename
        if asset_path.is_file():
            return send_from_directory(ASSETS_ROOT, filename)
        abort(404)

    # Global Favicon Route (Zero HTML configuration required)
    @app.route("/favicon.ico")
    def serve_favicon():
        favicon_path = ASSETS_ROOT / "favicon" / "favicon.ico"
        if favicon_path.is_file():
            return send_from_directory(favicon_path.parent, favicon_path.name)
        abort(404)

    # Direct 1:1 File, Index, and Python Handler Router
    @app.route("/", defaults={"req_path": ""})
    @app.route("/<path:req_path>")
    def serve(req_path: str):
        target_path = target_dir / req_path

        if not request.path.endswith("/") and target_path.is_dir():
            return redirect(request.path + "/")

        # 0. Direct Python file execution (e.g., api.py)
        if target_path.is_file() and target_path.suffix == ".py":
            return execute_python_handler(target_path)

        # 1. Exact static file match (e.g., /about.html, /index.js)
        if target_path.is_file():
            return send_from_directory(target_path.parent, target_path.name)

        # 2. Directory index.py match (prioritized dynamic page generator)
        index_py_path = target_path / "index.py"
        if index_py_path.is_file():
            return execute_python_handler(index_py_path)

        # 3. Directory index.html match (static layout fallback)
        index_path = target_path / "index.html"
        if index_path.is_file():
            return send_from_directory(index_path.parent, index_path.name)

        # 4. Extension-less Python handler fallback (e.g., /foo/api -> /foo/api.py)
        py_path = target_dir / f"{req_path}.py"
        if py_path.is_file():
            return execute_python_handler(py_path)

        # 5. Extension-less HTML file fallback (e.g., /about -> /about.html)
        html_path = target_dir / f"{req_path}.html"
        if html_path.is_file():
            return send_from_directory(html_path.parent, html_path.name)

        abort(404)

    def execute_python_handler(py_path: Path):
        """Helper to safely load and execute a dynamic python handler module."""
        try:
            spec = importlib.util.spec_from_file_location("dynamic_route", py_path)
            if spec is not None and spec.loader is not None:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "handle"):
                    return mod.handle()
                elif hasattr(mod, "main"):
                    return mod.main()
                else:
                    abort(500, description="Handler module missing handle() or main()")
            else:
                abort(500, description="Could not load dynamic module specification")
        except Exception as e:
            abort(500, description=str(e))

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run HTTP Server")
    parser.add_argument(
        "--mode",
        choices=["public", "local"],
        required=True,
        help="Server target root mode",
    )
    parser.add_argument("--host", default=BIND_HOST, help="Host interface to bind")
    parser.add_argument("--port", type=int, help="Port to listen on")

    args = parser.parse_args()

    if args.mode == "public":
        target_directory = PUBLIC_ROOT
        port = args.port or DEFAULT_PUBLIC_PORT
    else:
        target_directory = LOCAL_ROOT
        port = args.port or DEFAULT_LOCAL_PORT

    app = create_app(target_directory)
    app.run(host=args.host, port=port, debug=True)
