@echo off
cd /d c:\Users\matta\Desktop\dati_eventi
echo Checking Python and Flask installation...
python -c "import flask; print('Flask is installed')"
if %ERRORLEVEL% EQU 0 (
    echo Starting API Server...
    python api_server.py
) else (
    echo Installing Flask...
    pip install flask
    python api_server.py
)
