@echo off
echo =======================================================
echo Building RS232-TCP to USB-KBD Wedge Executable (.exe)
echo =======================================================
echo.

:: Check for Python installation
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to your system PATH.
    echo Please install Python 3.x and check "Add to PATH".
    pause
    exit /b 1
)

echo [1/3] Installing/Upgrading required packages...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo [2/3] Compiling standalone executable via PyInstaller...
echo Creating single-file EXE without console window...
python -m PyInstaller --clean --onefile --noconsole --name="RS232_TCP_to_USB_Wedge" main.py
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller failed to compile the application.
    pause
    exit /b 1
)

echo.
echo [3/3] Build completed successfully!
echo The standalone executable can be found in the "dist" folder:
echo dist\RS232_TCP_to_USB_Wedge.exe
echo.
pause
