@echo off
echo Starting OpenManus Web Interface...

REM Try to activate conda environment
call conda activate open_manus || echo Failed to activate conda environment, trying to start service directly

REM Start web server
echo Starting web server, please visit http://localhost:8000 in your browser
python web_server.py

REM If the server fails to start, pause to show error messages
if %ERRORLEVEL% NEQ 0 (
    echo Web server failed to start, please check error messages above
    pause
)