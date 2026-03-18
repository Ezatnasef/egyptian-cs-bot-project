@echo off
echo 🔧 Professional Setup Started...
echo.

echo 📦 1/6 Install virtualenv...
pip install virtualenv

echo 🗂️ 2/6 Create virtual environment...
python -m venv egyptian_cs_env

echo 🎭 3/6 Activate environment...
call egyptian_cs_env\Scripts\activate.bat

echo 📥 4/6 Install requirements...
pip install -r requirements.txt --upgrade

echo 🔧 5/6 Install extras...
pip install ffmpeg-python uvicorn[standard] fastapi

echo 🚀 6/6 Start Backend...
cd backend
uvicorn app:app --reload --port 8000

pause

