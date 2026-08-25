# panel_windows

Windows 启动入口目录。

## 与 Linux 功能一致性

- `stock_floating_widget_windows.py` 直接加载 `tools/panel_linux/stock_floating_widget.py`。
- 因此 Windows 与 Linux 的功能、外观、参数逻辑保持一致。

## 一键启动（推荐）

- 双击 `run_panel_windows.bat`
- 脚本会自动完成：
  - 检测 Python
  - 创建 `.venv` 虚拟环境（首次）
  - 安装依赖（首次或升级时）
  - 启动悬浮窗

## 给“不会改代码”的同事：Windows 快速部署

1. 安装 Python 3.10+（勾选 `Add Python to PATH`）
2. 把整个 `JINX` 文件夹拷贝到同事电脑（不要只拷 `panel_windows`）
3. 同事双击：`tools\panel_windows\run_panel_windows.bat`
4. 首次启动会自动安装依赖，稍慢；后续启动会快很多

## 备用命令行启动

```bat
cd /d <你的JINX路径>
python tools\panel_windows\stock_floating_widget_windows.py
```

## 打包成 exe（给无 Python 环境同事）

1. 在项目根目录双击或命令行运行：
   - `tools\panel_windows\build_panel_windows_exe.bat`
2. 打包成功后产物在：
   - `tools\panel_windows\dist\JinxStockPanel.exe`
3. 把 `JinxStockPanel.exe` 发给同事即可直接运行（无需预装 Python）

> 说明：exe 启动后会在 exe 同目录生成 `.stock_floating_widget_settings.json` 用于保存界面设置。
