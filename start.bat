@echo off
setlocal
cd /d "%~dp0" || goto :failed
title BIRGE
set "BIRGE_PYTHON=.venv\Scripts\python.exe"
if exist "%BIRGE_PYTHON%" goto :dependencies

echo Creating the Python environment...
py -3 -m venv .venv || python -m venv .venv || goto :failed

:dependencies
echo Checking Python dependencies...
"%BIRGE_PYTHON%" -m pip install --disable-pip-version-check --no-input --quiet -r requirements.txt || goto :failed
"%BIRGE_PYTHON%" -m scripts.start_local %* || goto :failed
exit /b 0

:failed
echo.
echo BIRGE could not start. See the error above.
if /i not "%~1"=="--no-browser" pause
exit /b 1
