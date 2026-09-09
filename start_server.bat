@echo off
set "PYTHONPATH=%~dp0src"
set "PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"

REM --- LOCAL ENVIRONMENT (6-Series Duality) ---
start "BITU - Local HTTP" cmd /k ""%PYTHON%" "%~dp0src\web\http_server.py" --mode local --port 8000"
@REM start "BITU - Local WebSocket" cmd /k ""%PYTHON%" "%~dp0src\web\ws_server.py" --host 127.0.0.1 --port 8888 --mode local"

REM --- PUBLIC ENVIRONMENT (9-Series Duality) ---
@REM start "BITU - Public HTTP" cmd /k ""%PYTHON%" "%~dp0src\web\http_server.py" --mode public --port 9000"
@REM start "BITU - Public WebSocket" cmd /k ""%PYTHON%" "%~dp0src\web\ws_server.py" --host 127.0.0.1 --port 9999 --mode public"

REM --- CLOUDFLARE TUNNEL ---
REM start "BITU - Cloudflare Tunnel" cloudflared tunnel --config cloudflare.yml run bitu-public-tunnel
