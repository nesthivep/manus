@echo off
echo Starting OpenManus Web Interface...

REM Try to activate conda environment
call conda activate open_manus || echo Failed to activate conda environment, trying to start service directly

REM Start the original service (main.py) first with visible window
echo Starting the original service (main.py)...
start "OpenManus Main Service" cmd /k python main.py

REM Wait a few seconds for the original service to start
timeout /t 5 /nobreak > nul
echo Original service started

REM Start web server in a separate window
echo Starting web server, please visit http://localhost:8000 in your browser
start "OpenManus Web Server" cmd /k python web_server.py

echo Both services started. Check the open command windows for logs.
echo Press any key to stop all services...
pause

REM When user presses a key, kill all related processes
taskkill /F /FI "WINDOWTITLE eq OpenManus*" /T