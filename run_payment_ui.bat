@echo off
cd /d %~dp0
if exist venv\Scripts\activate.bat call venv\Scripts\activate.bat
python -m streamlit run app_payment_gateway.py --server.port 8503
pause
