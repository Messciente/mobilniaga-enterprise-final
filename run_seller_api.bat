@echo off
cd /d %~dp0
if exist venv\Scripts\activate.bat call venv\Scripts\activate.bat
python -m uvicorn seller_api:app --port 8002 --reload
pause
