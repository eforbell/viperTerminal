@echo off
REM
REM Build standalone binary for Viper Terminal using PyInstaller (Windows)
REM
REM Usage: scripts\build\build-binary.bat
REM
REM Output: dist\viper.exe
REM
REM Prerequisites:
REM   - Python 3.10+
REM   - pip install pyinstaller
REM

setlocal enabledelayedexpansion

echo === Building Viper Terminal Standalone Binary ===
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
    echo Make sure to check "Add Python to PATH" during installation.
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python version: %PYTHON_VERSION%

REM Check for PyInstaller
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo.
    echo PyInstaller not found. Installing...
    python -m pip install --quiet pyinstaller
)

REM Install viper dependencies
echo.
echo Installing dependencies...
python -m pip install --quiet .

REM Clean previous builds
echo.
echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Build the binary
echo.
echo Building binary (this may take a few minutes)...
python -m PyInstaller scripts\build\viper.spec --noconfirm

REM Check if build succeeded
if exist "dist\viper.exe" (
    REM Rename with platform suffix
    move "dist\viper.exe" "dist\viper-windows.exe" >nul

    echo.
    echo === Build Complete ===
    echo.
    echo Binary created:
    dir "dist\viper-windows.exe"
    echo.
    echo To run:
    echo   dist\viper-windows.exe
    echo.
    echo To distribute, copy this single file to the target machine.
) else (
    echo.
    echo Error: Build failed. Check the output above for errors.
    exit /b 1
)

endlocal
