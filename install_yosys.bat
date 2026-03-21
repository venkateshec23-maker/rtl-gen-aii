@REM install_yosys.bat
@REM Quick Yosys installation via Conda

@echo off
setlocal enabledelayedexpansion

echo.
echo ==================================================
echo  Installing Yosys via Conda...
echo ==================================================
echo.

REM Check if conda is available
where conda >nul 2>&1
if errorlevel 1 (
    echo ERROR: Conda not found in PATH
    echo.
    echo Install Miniconda from: https://docs.conda.io/projects/miniconda/en/latest/
    echo.
    pause
    exit /b 1
)

echo Installing yosys from conda-forge...
conda install -c conda-forge yosys -y

if errorlevel 1 (
    echo.
    echo ERROR: Installation failed
    pause
    exit /b 1
)

echo.
echo ==================================================
echo  Installation Complete!
echo ==================================================
echo.

REM Test installation in a new shell
echo Testing installation...
for /f "tokens=*" %%i in ('conda run yosys -version 2^>^&1') do (
    echo   %%i
    goto :success
)

:success
echo.
echo SUCCESS - Yosys is ready!
echo.
echo Next: python validate_pipeline.py
echo.
pause
