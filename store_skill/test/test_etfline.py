import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from web.pages.etfline.router import LinesRequest, lines, lines_post

from store_skill.etfline.etfline import (
    _namespace_code, _parse_line_payload, _parse_market_payload, _parse_sector_list, _parse_sina_market_payload, _parse_sina_payload,
    _parse_ths_html, _read_ths_lines, _write_ths_snapshot, get_market_lines, get_sector_lines, list_sectors,
)

THS_HTML = """<table><tr><th>序号</th><th>行业</th><th>行业指数</th><th>涨跌幅</th><th>流入资金(亿)</th><th>流出资金(亿)</th><th>净额(亿)</th><th>公司家数</th></tr><tr><td>1</td><td>银行</td><td>1234</td><td>1.2%</td><td>2.1</td><td>1</td><td>1.1</td><td>10</td></tr></table>"""

class EtflineTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"JINX_ETFLINE_CACHE_DIR": self.temp.name})
        self.env.start()

    def tearDown(self):
        self.env.stop(); self.temp.cleanup()

    def test_eastmoney_parsers(self):
        payload = {"data": {"diff": [{"f12": "BK0475", "f14": "银行Ⅱ", "f2": "1245.67", "f3": 1.25, "f62": "246800000"}, None]}}
        self.assertEqual(_parse_sector_list(payload)[0]["main_net"], 246800000.0)
        line = _parse_line_payload({"data": {"code": "BK0475", "klines": ["2026-08-18 09:31,100.5", "2026-08-17 15:00,12"]}}, "2026-08-18")
        self.assertEqual(line["points"], [{"time": "2026-08-18 09:31", "value": 100.5}])

    def test_ths_html_uses_namespace_and_converts_yi(self):
        item = _parse_ths_html(THS_HTML, "industry")[0]
        self.assertTrue(item["code"].startswith("THS-"))
        self.assertEqual(item["main_net"], 110000000.0)
        self.assertEqual(item["change_pct"], 1.2)

    def test_ths_cache_round_trip_keeps_only_real_buckets(self):
        code = _namespace_code("THS", "industry", "银行")
        items = [{"code": code, "name": "银行", "main_net": 100.0}]
        self.assertIsNone(_write_ths_snapshot(items, "industry", datetime(2026, 8, 18, 9, 32)))
        items[0]["main_net"] = 150.0
        _write_ths_snapshot(items, "industry", datetime(2026, 8, 18, 9, 36))
        lines, failures = _read_ths_lines([code], "2026-08-18")
        self.assertFalse(failures)
        self.assertEqual(lines[0]["points"], [{"time": "2026-08-18 09:30", "value": 100.0}, {"time": "2026-08-18 09:35", "value": 150.0}])

    def test_ths_after_close_uses_market_close_and_ignores_invalid_time(self):
        code = _namespace_code("THS", "industry", "银行")
        items = [{"code": code, "name": "银行", "main_net": 200.0}]
        _write_ths_snapshot(items, "industry", datetime(2026, 8, 18, 16, 57))
        path = Path(self.temp.name) / "ths-2026-08-18.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["samples"][code]["points"]["2026-08-18 08:55"] = 1.0
        path.write_text(json.dumps(payload), encoding="utf-8")
        lines, _ = _read_ths_lines([code], "2026-08-18")
        self.assertEqual(lines[0]["points"], [{"time": "2026-08-18 15:00", "value": 200.0}])

    def test_sina_is_quote_only(self):
        item = _parse_sina_payload('var x={"new_blhy_bank":"bank,银行,10,12.3,0.1,1.2,1,2"}', "industry")[0]
        self.assertIsNone(item["main_net"])
        result = get_sector_lines([item["code"]], "2026-08-18", "sina")
        self.assertFalse(result.ok); self.assertIn("不含真实主力净流入", result.error)

    def test_validation_never_uses_network(self):
        with patch("store_skill.etfline.etfline.requests.get") as get:
            self.assertFalse(list_sectors("region").ok)
            self.assertFalse(list_sectors(source="bad").ok)
            self.assertFalse(get_sector_lines(["BK0475"], source="ths").ok)
            get.assert_not_called()

    @patch("store_skill.etfline.etfline.requests.get")
    def test_eastmoney_default_is_backward_compatible(self, get):
        response = Mock(); response.raise_for_status.return_value = None
        response.json.return_value = {"rc": 0, "data": {"diff": [{"f12": "BK0475", "f14": "银行", "f62": 1}]}}
        get.return_value = response
        result = list_sectors("industry")
        self.assertTrue(result.ok); self.assertEqual(result.data["source"], "eastmoney")
        self.assertEqual(result.meta["requested_source"], "auto"); self.assertEqual(result.meta["update_interval"], 60)

    @patch("store_skill.etfline.etfline._sina_list")
    @patch("store_skill.etfline.etfline._ths_list")
    @patch("store_skill.etfline.etfline._eastmoney_list")
    def test_auto_fallback_chain(self, eastmoney, ths, sina):
        eastmoney.side_effect = ValueError("down")
        ths.return_value = [{"code": "THS-A", "name": "银行", "price": 1, "change_pct": 1, "main_net": 2}]
        result = list_sectors(source="auto")
        self.assertTrue(result.ok); self.assertEqual(result.data["source"], "ths")
        self.assertEqual(result.meta["fallbacks"], ["eastmoney -> ths"]); sina.assert_not_called()
        self.assertTrue(list(Path(self.temp.name).glob("ths-*.json")))

    @patch("store_skill.etfline.etfline.requests.get")
    def test_lines_partial_success(self, get):
        good = Mock(); good.raise_for_status.return_value = None
        good.json.return_value = {"rc": 0, "data": {"name": "银行", "klines": ["2026-08-18 09:31,100"]}}
        empty = Mock(); empty.raise_for_status.return_value = None
        empty.json.return_value = {"rc": 0, "data": {"name": "农业", "klines": []}}
        get.side_effect = [good, empty]
        result = get_sector_lines(["BK0475", "BK0433"], "2026-08-18")
        self.assertTrue(result.ok); self.assertEqual(result.meta["granularity"], "minute")
        self.assertEqual(result.meta["returned"], 1); self.assertTrue(result.meta["warnings"])

    @patch("store_skill.etfline.etfline._eastmoney_lines")
    def test_more_than_ten_codes_reach_mock_flow(self, fetch):
        codes = [f"BK{i:04d}" for i in range(11)]
        fetch.return_value = ([{"code": code, "name": code, "points": [{"time": "2026-08-18 09:31", "value": 1}]} for code in codes], [])
        result = get_sector_lines(codes, "2026-08-18", "eastmoney")
        self.assertTrue(result.ok); self.assertEqual(result.meta["requested_count"], 11); fetch.assert_called_once_with(codes, "2026-08-18")

    def test_market_parsers(self):
        em = _parse_market_payload({"data": {"trends": ["2026-08-18 09:31,1,3201.5,3", "2026-08-17 15:00,1,2"]}}, "000001", "上证指数", "2026-08-18")
        self.assertEqual(em["points"], [{"time": "2026-08-18 09:31", "value": 3201.5}])
        sina = _parse_sina_market_payload('var _market=([{"day":"2026-08-18 09:32:00","close":"1001.2"}]);', "000680", "科创综指", "2026-08-18")
        self.assertEqual(sina["points"][0]["value"], 1001.2)

    @patch("store_skill.etfline.etfline._sina_market_line")
    @patch("store_skill.etfline.etfline._eastmoney_market_line")
    def test_market_lines_fallback_keeps_three_indexes(self, eastmoney, sina):
        def em(code, name, day):
            if code == "000680": raise ValueError("down")
            return {"code": code, "name": name, "points": [{"time": f"{day} 09:31", "value": 1}]}
        eastmoney.side_effect = em
        sina.return_value = {"code": "000680", "name": "科创综指", "points": [{"time": "2026-08-18 09:31", "value": 2}]}
        result = get_market_lines("2026-08-18")
        self.assertTrue(result.ok); self.assertEqual([line["code"] for line in result.data["lines"]], ["000001", "000680", "000688"])
        self.assertEqual(result.data["source"], "mixed"); self.assertTrue(result.meta["warnings"])

    @patch("web.pages.etfline.router.get_sector_lines")
    def test_lines_get_and_post_are_compatible(self, get_lines):
        mocked = Mock(); mocked.to_dict.return_value = {"ok": True}; get_lines.return_value = mocked
        self.assertEqual(lines(["BK0475"], "2026-08-18", "eastmoney"), {"ok": True})
        self.assertEqual(lines_post(LinesRequest(codes=["BK0475"], date="2026-08-18", source="eastmoney")), {"ok": True})
        self.assertEqual(get_lines.call_count, 2)

if __name__ == "__main__": unittest.main()
