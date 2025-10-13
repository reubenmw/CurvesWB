@echo off
REM Translation Update Script for CurvesWB (Windows)
REM This batch file runs the Python translation update script

echo ============================================================
echo CurvesWB Translation Update Script (Windows)
echo ============================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3 and add it to your system PATH
    pause
    exit /b 1
)

REM Run the Python translation script
python "%~dp0update_translations.py"

if errorlevel 1 (
    echo.
    echo ERROR: Translation update failed
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Translation update completed successfully!
echo ============================================================
pause
