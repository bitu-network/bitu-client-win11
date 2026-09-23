@echo off
title BITU
cd /d "C:\I\-\bitu\bitu-project"
set "PYTHONPATH=src"
set "PYTHONUNBUFFERED=1"
set "BITU_EXPLORER_DEBUG=1"
"C:\I\-\bitu\bitu-project\.venv\Scripts\python.exe" -m cli.start
if errorlevel 1 pause