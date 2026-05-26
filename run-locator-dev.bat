@echo off
echo ========================================================
echo   SODIGAZ - STARTING DEDICATED LOCATOR BACKEND DEV
echo ========================================================
echo.
echo [1/2] Checking dependencies...
python -m pip install -r requirements.txt
echo.
echo [2/2] Launching FastAPI local server on port 8002...
echo Swagger UI will be available at http://127.0.0.1:8002/docs
echo.
uvicorn app.main:app --reload --port 8002
pause
