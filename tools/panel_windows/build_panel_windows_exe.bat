@echo off
setlocal
chcp 65001 >nul

REM Enter project root (JINX)
cd /d "%~dp0\..\.."

set "VENV_PY=.venv\Scripts\python.exe"
set "PY_CMD="

REM 1) Check Python command
if defined CONDA_PREFIX if exist "%CONDA_PREFIX%\python.exe" (
  set "PY_CMD="%CONDA_PREFIX%\python.exe""
)
if not defined PY_CMD (
  for %%I in (python.exe) do if not "%%~$PATH:I"=="" set "PY_CMD="%%~$PATH:I""
)
if not defined PY_CMD (
  where py >nul 2>&1
  if %errorlevel%==0 set "PY_CMD=py -3"
)
if not defined PY_CMD (
  where python >nul 2>&1
  if %errorlevel%==0 set "PY_CMD=python"
)
if not defined PY_CMD (
  echo [ERROR] Python not found. Please install Python 3.10+ first.
  echo Download: https://www.python.org/downloads/windows/
  pause
  exit /b 1
)
echo [INFO] Using Python command: %PY_CMD%

REM 2) Require Python >= 3.10
%PY_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python version is too low. Need Python 3.10+.
  echo Download: https://www.python.org/downloads/windows/
  pause
  exit /b 1
)

REM 3) Create virtual environment if needed
if not exist "%VENV_PY%" (
  echo [INFO] Creating virtual environment .venv ...
  %PY_CMD% -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
  )
)

REM 4) Install build dependencies
echo [INFO] Installing/upgrading build dependencies...
"%VENV_PY%" -m pip install --upgrade pip
"%VENV_PY%" -m pip install -r requirements.txt
"%VENV_PY%" -m pip install pillow pyinstaller
if errorlevel 1 (
  echo [ERROR] Failed to install dependencies. Check network and retry.
  pause
  exit /b 1
)

REM 5) Cleanup old build outputs
if exist "tools\panel_windows\build" rmdir /s /q "tools\panel_windows\build"
if exist "tools\panel_windows\dist" rmdir /s /q "tools\panel_windows\dist"
if exist "tools\panel_windows\JinxStockPanel.spec" del /f /q "tools\panel_windows\JinxStockPanel.spec"

REM 6) Build exe (without console window)
echo [INFO] Building exe. Please wait...
"%VENV_PY%" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name JinxStockPanel ^
  --paths . ^
  --hidden-import PIL.ImageGrab ^
  --hidden-import PIL.ImageTk ^
  --distpath "tools\panel_windows\dist" ^
  --workpath "tools\panel_windows\build" ^
  --specpath "tools\panel_windows" ^
  "tools\panel_linux\stock_floating_widget.py"
if errorlevel 1 (
  echo [ERROR] Build failed.
  pause
  exit /b 1
)

echo [SUCCESS] Build complete:
echo tools\panel_windows\dist\JinxStockPanel.exe
pause
