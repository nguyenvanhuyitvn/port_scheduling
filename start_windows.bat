@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe py -3 -m venv .venv
if errorlevel 1 goto error
.venv\Scripts\python.exe -m pip install -e .
if errorlevel 1 goto error
.venv\Scripts\python.exe -m streamlit run app.py
goto end
:error
echo Installation failed. Check Python and Internet connection. See docs/STREAMLIT_GUIDE.md.
pause
:end
