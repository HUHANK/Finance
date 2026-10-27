@echo off
REM Dev mode: backend :8000 + frontend vite :5173 (keep this file ASCII-only, cmd parses bat as ANSI)
cd /d %~dp0..
start "backend" cmd /k "backend\.venv\Scripts\python.exe backend\run.py"
start "frontend" cmd /k "cd frontend && set PATH=%~dp0..\.tools\node;%%PATH%% && npm run dev"
echo.
echo  backend : http://127.0.0.1:8000
echo  frontend: http://127.0.0.1:5173   (open this in browser while developing)
