@echo off
REM ============================================================
REM SparkMiner - Freenove ESP32-S3 Display Flash Tool (Legacy Wrapper)
REM
REM This script now redirects to the unified flash.bat tool.
REM For full options, use: flash.bat --help
REM ============================================================

cd /d "%~dp0"

echo.
echo [INFO] Redirecting to unified flash tool with Freenove ESP32-S3 board...
echo.

if "%~1"=="--build" (
    call flash.bat --board freenove-s3 --build
) else if "%~1"=="--flash" (
    call flash.bat --board freenove-s3 --flash %2
) else if "%~1"=="--monitor" (
    call flash.bat --board freenove-s3 --monitor %2
) else if "%~1"=="--all" (
    call flash.bat --board freenove-s3 --all %2
) else (
    REM Interactive mode
    call flash.bat --board freenove-s3
)
