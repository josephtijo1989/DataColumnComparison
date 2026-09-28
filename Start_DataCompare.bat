@echo off
echo Starting Data Comparison Tool...
python -m uvicorn app:app --host 127.0.0.1 --port 8002 --reload
pause
