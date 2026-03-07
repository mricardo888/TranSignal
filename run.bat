@echo off
setlocal

rem run.bat — Start TranSignal on Windows
rem Usage: run.bat

set "SCRIPT_DIR=%~dp0"
set "PYTHON_DIR=%SCRIPT_DIR%python"

echo 🚀 Starting FastAPI Backend (which includes the autonomous daemon)...
rem Start the backend inside a new command prompt window so it runs in the background
start "TranSignal Backend API" cmd /c "cd /d "%PYTHON_DIR%" && call .venv\Scripts\activate.bat && python -m uvicorn api:app --host 0.0.0.0 --port 8000"

echo 🌐 Launching Streamlit Command Center...
rem Run the frontend in the current window
cd /d "%PYTHON_DIR%"
call .venv\Scripts\activate.bat
python -m streamlit run app.py --browser.gatherUsageStats false

echo.
echo 🛑 Streamlit stopped. Please close the "TranSignal Backend API" window to fully shut down.
endlocal
