@echo off
echo Starting OpenManus Web Interface...

REM Try to activate conda environment
call conda activate open_manus || echo Failed to activate conda environment, trying to start service directly

REM Start the original service (main.py) first
echo Starting the original service (main.py)...
start cmd /k python main.py

REM Wait a few seconds for the original service to start
timeout /t 5 /nobreak > nul
echo Original service started

REM Start web server
echo Starting web server, please visit http://localhost:8000 in your browser
python web_server.py

REM If the server fails to start, pause to show error messages
if %ERRORLEVEL% NEQ 0 (
    echo Web server failed to start, please check error messages above
    pause
)