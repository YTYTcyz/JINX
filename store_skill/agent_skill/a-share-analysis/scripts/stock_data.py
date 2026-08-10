#!/usr/bin/env python3
"""Fetch A-share quote and K-line data as JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT))

from store_skill.getkline import PERIODS, get_kline  # noqa: E402
from store_skill.getprice import get_quote  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="获取 A 股或 ETF 行情")
    parser.add_argument("symbol", help="六位证券代码，例如 600519")
    parser.add_argument(
        "--period",
        choices=PERIODS,
        default="daily",
        help="K 线周期，默认 daily",
    )
    parser.add_argument("--quote-only", action="store_true", help="只获取实时价格")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    quote = get_quote(args.symbol)
    payload = {"quote": quote.to_dict()}

    if not args.quote_only:
        payload["kline"] = get_kline(args.symbol, args.period).to_dict()

    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    succeeded = quote.ok or payload.get("kline", {}).get("ok", False)
    return 0 if succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
