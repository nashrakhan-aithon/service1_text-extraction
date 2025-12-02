@echo off
REM Service 1: Test Script Wrapper for Windows
REM ============================================
REM This bypasses PowerShell execution policy

if "%~1"=="" (
    echo Usage: test-service1.bat "C:\path\to\your\document.pdf"
    exit /b 1
)

powershell.exe -ExecutionPolicy Bypass -File "%~dp0test-service1.ps1" "%~1"

