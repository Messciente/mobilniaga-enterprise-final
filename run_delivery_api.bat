@echo off
cd /d %~dp0
if exist venv\Scripts\activate.bat call venv\Scripts\activate.bat
python -m uvicorn delivery_api:app --port 8004 --reload
pause
