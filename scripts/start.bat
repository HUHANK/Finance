@echo off
REM Single-port mode: serve built frontend at http://127.0.0.1:8000 (keep this file ASCII-only)
cd /d %~dp0..
if not exist frontend\dist\index.html (
  echo Building frontend first...
  pushd frontend
  set "PATH=%~dp0..\.tools\node;%%PATH%%"
  call npm run build
  popd
)
backend\.venv\Scripts\python.exe backend\run.py
