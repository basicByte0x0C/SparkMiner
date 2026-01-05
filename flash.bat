@echo off
REM ============================================================
REM SparkMiner - Universal Flash Tool
REM
REM All-in-one build and flash tool supporting multiple boards:
REM   - CYD 1-USB / 2-USB variants
REM   - Freenove ESP32-S3 Display
REM   - ESP32 Headless variants
REM
REM Usage:
REM   flash.bat                      - Interactive mode
REM   flash.bat --list               - List available boards
REM   flash.bat --board cyd-2usb     - Select board directly
REM   flash.bat --board freenove-s3 --all  - Build+Flash+Monitor
REM ============================================================

cd /d "%~dp0"

REM Check for venv Python
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe flash.py %*
) else (
    REM Fall back to system Python
    python flash.py %*
)

if %ERRORLEVEL% neq 0 (
    echo.
    echo Press any key to exit...
    pause >nul
)
