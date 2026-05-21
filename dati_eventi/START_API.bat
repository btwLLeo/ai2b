@echo off
REM ============================================================
REM Hybrid Geospatial Retrieval API - Windows Launcher
REM ============================================================
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ============================================================
echo Hybrid Geospatial Retrieval API - Launcher
echo ============================================================
echo.

REM Check Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org
    pause
    exit /b 1
)

echo Checking dependencies...
python -c "import flask" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installing Flask...
    python -m pip install flask -q
)

python -c "import qdrant_client" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installing Qdrant Client...
    python -m pip install qdrant-client -q
)

python -c "import numpy" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installing NumPy...
    python -m pip install numpy -q
)

echo.
echo Starting API Server...
echo.
python run_server.py

pause
