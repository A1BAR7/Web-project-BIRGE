@echo off
setlocal
cd /d "%~dp0"
title BIRGE
if not exist ".venv\Scripts\python.exe" (
    echo Python environment not found: .venv
    pause
    exit /b 1
)
echo Starting BIRGE. Close this window to stop the server.
".venv\Scripts\python.exe" -c "import threading, webbrowser, uvicorn; timer = threading.Timer(2.0, webbrowser.open, args=('http://127.0.0.1:8000/app/',)); timer.daemon = True; timer.start(); uvicorn.run('app.main:app', host='127.0.0.1', port=8000)"
if errorlevel 1 pause
