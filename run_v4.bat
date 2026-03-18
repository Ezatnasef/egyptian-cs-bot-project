@echo off
echo 🚀 Launching Egyptian CS Bot V4 (API Driven)...
cd backend
python -m uvicorn app:app --port 8000
pause
