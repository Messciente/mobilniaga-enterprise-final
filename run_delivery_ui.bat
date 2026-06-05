@echo off
cd /d %~dp0
if exist venv\Scripts\activate.bat call venv\Scripts\activate.bat
python -m streamlit run app_delivery.py --server.port 8504
pause
