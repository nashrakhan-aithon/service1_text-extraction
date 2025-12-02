@echo off
echo ========================================
echo Service 1 Package Verification
echo ========================================
echo.

if not exist "Dockerfile" (
    echo ERROR: Dockerfile not found!
    echo Make sure you are in the service1-standalone-1.0.0 directory
    pause
    exit /b 1
)

echo Checking Dockerfile...
echo.

echo [1] Checking requirements.txt path (should be line 23):
findstr /n "COPY requirements.txt" Dockerfile
echo.

echo [2] Checking start_api.py path (should be line 33):
findstr /n "COPY start_api.py" Dockerfile
echo.

echo [3] Verifying correct paths...
findstr "COPY requirements.txt ./" Dockerfile >nul
if %errorlevel% equ 0 (
    echo    ✅ requirements.txt path is CORRECT
) else (
    echo    ❌ requirements.txt path is WRONG - you have OLD package!
    echo    Expected: COPY requirements.txt ./
    echo    Found: COPY backend/services/document_text_extraction/requirements.txt
    pause
    exit /b 1
)

findstr "COPY start_api.py ./" Dockerfile >nul
if %errorlevel% equ 0 (
    echo    ✅ start_api.py path is CORRECT
) else (
    echo    ❌ start_api.py path is WRONG - you have OLD package!
    echo    Expected: COPY start_api.py ./
    echo    Found: COPY backend/services/document_text_extraction/start_api.py
    pause
    exit /b 1
)

echo.
echo ========================================
echo ✅ Package is CORRECT and ready to use!
echo ========================================
echo.
echo You can now run:
echo   docker-compose -f docker-compose-standalone.yml up -d
echo.
pause
