@echo off
REM ============================================================
REM SparkMiner - CYD 2-USB Simple Flash (Legacy Wrapper)
REM
REM This script now redirects to the unified flash.bat tool.
REM For full options, use: flash.bat --help
REM ============================================================

cd /d "%~dp0"

echo.
echo [INFO] Redirecting to unified flash tool with CYD 2-USB board...
echo.

if /i "%~1"=="build" (
    call flash.bat --board cyd-2usb --build
    call flash.bat --board cyd-2usb --all -y
) else (
    call flash.bat --board cyd-2usb --all -y
)
