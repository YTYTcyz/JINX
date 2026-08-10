from __future__ import annotations

from typing import Any

import requests

from store_skill.getprice.config import SourceConfig
from store_skill.getprice.normalize import SymbolInfo
from store_skill.getprice.sources.base import finalize_quote


class SinaSource:
    name = "sina"
    URL = "https://hq.sinajs.cn/list={codes}"

    def fetch_one(
        self,
        info: SymbolInfo,
        *,
        timeout: float,
        source_config: SourceConfig,
    ) -> dict[str, Any]:
        rows = self.fetch_many([info], timeout=timeout, source_config=source_config)
        if not rows:
            raise ValueError(f"sina: empty quote for {info.symbol}")
        return rows[0]

    def fetch_many(
        self,
        infos: list[SymbolInfo],
        *,
        timeout: float,
        source_config: SourceConfig,
    ) -> list[dict[str, Any]]:
        if not infos:
            return []
        codes = ",".join(i.sina_code for i in infos)
        headers = {
            "Referer": source_config.referer or "https://finance.sina.com.cn/",
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
        }
        resp = requests.get(self.URL.format(codes=codes), headers=headers, timeout=timeout)
        resp.raise_for_status()
        resp.encoding = "gbk"
        text = resp.text.strip()
        if not text or "Kinsoku" in text:
            raise ValueError("sina: blocked or empty response (check Referer)")

        by_sina = {i.sina_code: i for i in infos}
        quotes: list[dict[str, Any]] = []
        for line in text.splitlines():
            line = line.strip()
            if not line or "=" not in line:
                continue
            left, right = line.split("=", 1)
            code = left.split("_")[-1].strip().lower()
            payload = right.strip().strip(";").strip('"')
            if not payload:
                continue
            parts = payload.split(",")
            if len(parts) < 32:
                continue
            info = by_sina.get(code)
            if info is None:
                # try without market mismatch
                continue
            quotes.append(
                finalize_quote(
                    {
                        "name": parts[0] or None,
                        "open": parts[1],
                        "pre_close": parts[2],
                        "price": parts[3],
                        "high": parts[4],
                        "low": parts[5],
                        "volume": parts[8],
                        "amount": parts[9],
                        "time": f"{parts[30]} {parts[31]}".strip(),
                    },
                    info,
                    self.name,
                )
            )
        if not quotes:
            raise ValueError("sina: no parseable quotes")
        return quotes
