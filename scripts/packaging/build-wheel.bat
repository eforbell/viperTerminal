@echo off
REM
REM Build wheel distribution for Viper Terminal (Windows)
REM
REM Usage: scripts\build\build-wheel.bat
REM
REM Output: dist\viper_terminal-X.X.X-py3-none-any.whl
REM

setlocal

echo === Building Viper Terminal Wheel ===
echo.

REM Get the project root directory
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%\..\.."
set "PROJECT_ROOT=%CD%"
popd

cd /d "%PROJECT_ROOT%"

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: python not found. Please install Python 3.10 or higher.
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python version: %PYTHON_VERSION%

REM Install build dependencies
echo.
echo Installing build dependencies...
python -m pip install --quiet --upgrade pip build

REM Clean previous builds
echo.
echo Cleaning previous builds...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
for /d %%i in (*.egg-info) do rmdir /s /q "%%i"

REM Build the wheel
echo.
echo Building wheel...
python -m build --wheel

REM Show result
echo.
echo === Build Complete ===
echo.
echo Wheel created:
dir dist\*.whl
echo.
echo To install:
echo   pip install dist\viper_terminal-X.X.X-py3-none-any.whl
echo.

endlocal
