"""getprice 样例：直接运行本文件即可试拉行情。

用法（在 JINX 根目录）:
  pip install -e .
  python -m store_skill.test.test_getprice
  JINX_QUOTE_PRIMARY=sina python -m store_skill.test.test_getprice
"""

from __future__ import annotations

import json
import os
import sys

from store_skill.getprice import QuoteConfig, get_quote, get_quotes


def _print_result(title: str, result) -> None:
    print("=" * 60)
    print(title)
    print("ok:", result.ok)
    if result.error:
        print("error:", result.error)
    if result.meta:
        print("meta:", result.meta)
    print("data:", json.dumps(result.data, ensure_ascii=False, indent=2, default=str))


def main() -> int:
    symbol = os.getenv("JINX_TEST_SYMBOL", "600519")
    print(f"primary env = {os.getenv('JINX_QUOTE_PRIMARY', '(default eastmoney)')}")
    print(f"fallback env = {os.getenv('JINX_QUOTE_FALLBACK', '(default sina,xueqiu)')}")

    # 1) 默认 CONFIG
    r1 = get_quote(symbol)
    _print_result(f"get_quote({symbol!r}) default config", r1)

    # 2) 强制新浪
    r2 = get_quote(symbol, config=QuoteConfig(primary="sina", fallback=[]))
    _print_result(f"get_quote({symbol!r}) primary=sina only", r2)

    # 3) 批量
    r3 = get_quotes(["600519", "000001", "300750"])
    _print_result("get_quotes(['600519','000001','300750'])", r3)

    ok = r1.ok or r2.ok or r3.ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
