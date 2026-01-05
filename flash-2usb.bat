@echo off
REM ============================================================
REM SparkMiner - CYD 2-USB Flash Tool (Legacy Wrapper)
REM
REM This script now redirects to the unified flash.bat tool.
REM For full options, use: flash.bat --help
REM ============================================================

cd /d "%~dp0"

echo.
echo [INFO] Redirecting to unified flash tool with CYD 2-USB board...
echo.

if "%~1"=="" (
    REM No arguments - interactive mode for cyd-2usb
    call flash.bat --board cyd-2usb
) else (
    REM Pass COM port for flashing
    call flash.bat --board cyd-2usb --all %1
)
