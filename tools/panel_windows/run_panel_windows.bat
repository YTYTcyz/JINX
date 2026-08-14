@echo off
setlocal
chcp 65001 >nul

REM 进入项目根目录（JINX）
cd /d "%~dp0\..\.."

set "VENV_PY=.venv\Scripts\python.exe"
set "DEPS_MARKER=.venv\.panel_windows_deps_ok"

REM 1) 检查 Python
where py >nul 2>&1
if %errorlevel%==0 (
  set "PY_CMD=py -3"
) else (
  where python >nul 2>&1
  if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    echo 下载: https://www.python.org/downloads/windows/
    pause
    exit /b 1
  )
  set "PY_CMD=python"
)

REM 2) 首次运行自动创建虚拟环境
if not exist "%VENV_PY%" (
  echo [信息] 正在创建虚拟环境 .venv ...
  %PY_CMD% -m venv .venv
  if errorlevel 1 (
    echo [错误] 创建虚拟环境失败
    pause
    exit /b 1
  )
)

REM 3) 首次安装依赖（后续不会重复安装）
if not exist "%DEPS_MARKER%" (
  echo [信息] 正在安装依赖（首次可能需要几分钟）...
  "%VENV_PY%" -m pip install --upgrade pip
  "%VENV_PY%" -m pip install -r requirements.txt
  "%VENV_PY%" -m pip install pillow
  if errorlevel 1 (
    echo [错误] 依赖安装失败，请检查网络后重试
    pause
    exit /b 1
  )
  type nul > "%DEPS_MARKER%"
)

REM 4) 启动程序
echo [信息] 启动股票悬浮窗...
"%VENV_PY%" "tools\panel_windows\stock_floating_widget_windows.py"
if errorlevel 1 (
  echo [错误] 启动失败
  pause
  exit /b 1
)
