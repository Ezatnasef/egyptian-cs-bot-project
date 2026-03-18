@echo off
chcp 65001 >nul
echo ====================================
echo  Egyptian CS Bot - Starting Server
echo ====================================
echo.

cd /d "%~dp0"

:: Add custom FFmpeg path (Added automatically based on user input)
set "PATH=%PATH%;C:\Users\Nasef\Downloads\ffmpeg-8.1\bin"

:: Check if venv exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate venv
call venv\Scripts\activate

:: Check for FFmpeg before proceeding
echo.
echo 🔍 Checking for FFmpeg installation...
ffmpeg -version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ ERROR: 'ffmpeg' command not found in this terminal session.
    echo This usually means you need to RESTART your terminal/PowerShell window after installation.
    echo.
    echo 👉 Please CLOSE this window and run 'run.bat' again from a NEW terminal.
    pause
    exit /b
)
echo ✅ FFmpeg found successfully!
echo.

:: Install dependencies
echo Installing dependencies (This may take a while, please be patient)...
pip install -r requirements.txt

:: Load .env
if exist .env (
    for /f "tokens=1,2 delims==" %%a in (.env) do (
        set "%%a=%%b"
    )
) else (
    echo Warning: .env file not found. Running in default mode.
)

:: Start server
echo.
echo 🚀 Server is starting...
echo 👉 Open your browser at: http://localhost:8000
echo.
cd backend
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Server crashed or failed to start.
    pause
)
