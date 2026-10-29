@echo off
title CloudDataGuard Server
cd /d "%~dp0"
echo ====================================================
echo Starting CloudDataGuard Server...
echo URL: http://127.0.0.1:8000/frontend/index.html
echo API Docs: http://127.0.0.1:8000/docs
echo ====================================================
.\venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
pause

