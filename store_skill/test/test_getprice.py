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
import unittest
from unittest.mock import patch

from store_skill.getprice.normalize import normalize_symbol
from store_skill.getprice.sources.base import finalize_quote
from store_skill.getprice.sources.yahoo import YahooSource, format_yahoo_time

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
    print(f"fallback env = {os.getenv('JINX_QUOTE_FALLBACK', '(default sina,yahoo,yahoo_alt,xueqiu)')}")

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


class _MockSource:
    name = "mock"

    def fetch_one(self, info, *, timeout, source_config):
        if info.market == "US":
            raise RuntimeError("upstream unavailable")
        return finalize_quote({"name": info.symbol, "price": "123.45", "pre_close": "120", "time": "2026-08-25 15:00:00"}, info, self.name)

    def fetch_many(self, infos, *, timeout, source_config):
        return [self.fetch_one(i, timeout=timeout, source_config=source_config) for i in infos]


class GetpriceMockedTests(unittest.TestCase):
    def test_market_formats_preserve_a_share_and_add_hk_us(self):
        self.assertEqual(normalize_symbol("600519").market, "SH")
        hk = normalize_symbol("HK:00700")
        self.assertEqual((hk.symbol, hk.market, hk.yahoo_code), ("00700", "HK", "0700.HK"))
        self.assertEqual(normalize_symbol("HK:00005").yahoo_code, "0005.HK")
        self.assertEqual(normalize_symbol("HK:09988").yahoo_code, "9988.HK")
        self.assertEqual(normalize_symbol("00700.HK"), hk)
        us = normalize_symbol("US:AAPL")
        self.assertEqual((us.symbol, us.market, us.yahoo_code), ("AAPL", "US", "AAPL"))
        self.assertEqual(normalize_symbol("AAPL.US"), us)

    def test_mixed_markets_partial_success_and_metadata(self):
        from store_skill.getprice import QuoteConfig, get_quotes
        config = QuoteConfig(primary="mock", fallback=[], sources={"mock": {"enabled": True}})
        with patch.dict("store_skill.getprice.quote.SOURCE_REGISTRY", {"mock": _MockSource()}):
            result = get_quotes(["600519", "HK:00700", "US:AAPL"], config=config)
        self.assertTrue(result.ok)
        self.assertEqual([row["market"] for row in result.data], ["SH", "HK"])
        self.assertTrue(result.error)
        self.assertTrue(result.meta["partial"])
        self.assertEqual(result.meta["sources"], ["mock"])
        self.assertIn("SH", result.data[0]["market"])
        self.assertEqual([row["symbol"] for row in result.data], ["600519", "00700"])
        self.assertEqual(set(result.meta["times"]), {"SH:600519", "HK:00700"})
        json.dumps(result.to_dict())


    def test_invalid_symbol_is_partial_error(self):
        config = QuoteConfig(primary="mock", fallback=[], sources={"mock": {"enabled": True}})
        with patch.dict("store_skill.getprice.quote.SOURCE_REGISTRY", {"mock": _MockSource()}):
            result = get_quotes(["US:AAPL", "not-a-symbol", "HK:00700"], config=config)
        self.assertTrue(result.ok)
        self.assertTrue(result.error)
        self.assertEqual([row["symbol"] for row in result.data], ["00700"])

    def test_hk_us_fallback_and_incompatible_sources_are_skipped(self):
        calls = []

        class Source:
            def __init__(self, name, succeed=False):
                self.name = name
                self.succeed = succeed

            def fetch_one(self, info, *, timeout, source_config):
                calls.append((self.name, info.market))
                if self.name == "yahoo":
                    raise RuntimeError("primary failed")
                return finalize_quote({"price": "10", "time": "2026-08-25 12:00:00"}, info, self.name)

        config = QuoteConfig(
            primary="yahoo",
            fallback=["yahoo_alt", "sina", "eastmoney"],
            sources={"yahoo": {"enabled": True}, "yahoo_alt": {"enabled": True}},
        )
        registry = {"yahoo": Source("yahoo"), "yahoo_alt": Source("yahoo_alt"), "sina": Source("sina"), "eastmoney": Source("eastmoney")}
        with patch.dict("store_skill.getprice.quote.SOURCE_REGISTRY", registry):
            result = get_quotes(["HK:00700", "US:AAPL"], config=config)
        self.assertTrue(result.ok)
        self.assertEqual([row["source"] for row in result.data], ["yahoo_alt", "yahoo_alt"])
        self.assertEqual(calls, [("yahoo", "HK"), ("yahoo_alt", "HK"), ("yahoo", "US"), ("yahoo_alt", "US")])


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class YahooTests(unittest.TestCase):
    def test_yahoo_time_and_parsing(self):
        self.assertEqual(format_yahoo_time(0), None)
        self.assertIn("2026-", format_yahoo_time(1787652000, "Asia/Hong_Kong"))
        payload = {"chart": {"result": [{"meta": {"regularMarketPrice": 100, "previousClose": 95, "regularMarketTime": 1787652000, "exchangeTimezoneName": "Asia/Hong_Kong", "shortName": "Tencent"}}]}}
        with patch("store_skill.getprice.sources.yahoo.requests.get", return_value=_Response(payload)) as request:
            row = YahooSource().fetch_one(normalize_symbol("HK:00700"), timeout=1, source_config=None)
        request.assert_called_once()
        self.assertIn("0700.HK", request.call_args.args[0])
        self.assertEqual(row["source"], "yahoo")
        self.assertAlmostEqual(row["change_pct"], 5.2632, places=3)
        self.assertNotIsInstance(row["time"], int)


if __name__ == "__main__":
    sys.exit(main())
