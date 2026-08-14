from __future__ import annotations

from pathlib import Path
import runpy


def _load_shared_main():
    shared_path = Path(__file__).resolve().parents[1] / "panel_linux" / "stock_floating_widget.py"
    if not shared_path.exists():
        raise FileNotFoundError(f"未找到共享脚本: {shared_path}")
    namespace = runpy.run_path(str(shared_path))
    main_func = namespace.get("main")
    if not callable(main_func):
        raise AttributeError("共享脚本缺少 main() 入口")
    return main_func


def main() -> None:
    shared_main = _load_shared_main()
    shared_main()


if __name__ == "__main__":
    main()
