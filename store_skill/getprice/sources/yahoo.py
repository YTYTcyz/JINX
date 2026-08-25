from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

import requests

from store_skill.getprice.config import SourceConfig
from store_skill.getprice.normalize import SymbolInfo
from store_skill.getprice.sources.base import finalize_quote


def format_yahoo_time(value: Any, timezone_name: str | None = None) -> str | None:
    """Format Yahoo epoch seconds using the exchange timezone when available."""
    if value in (None, "", 0):
        return None
    try:
        timestamp = float(value)
    except (TypeError, ValueError):
        return str(value)
    tz = timezone.utc
    if timezone_name:
        try:
            tz = ZoneInfo(timezone_name)
        except Exception:
            pass
    return datetime.fromtimestamp(timestamp, tz=tz).isoformat(sep=" ", timespec="seconds")


class YahooSource:
    name = "yahoo"
    host = "query1.finance.yahoo.com"

    def __init__(self, name: str | None = None, host: str | None = None) -> None:
        if name:
            self.name = name
        if host:
            self.host = host

    @property
    def url_template(self) -> str:
        return f"https://{self.host}/v8/finance/chart/{{symbol}}"

    def fetch_one(
        self,
        info: SymbolInfo,
        *,
        timeout: float,
        source_config: SourceConfig,
    ) -> dict[str, Any]:
        del source_config
        if info.market not in {"HK", "US"} or not info.yahoo_code:
            raise ValueError(f"{self.name}: unsupported market {info.market}")
        response = requests.get(
            self.url_template.format(symbol=info.yahoo_code),
            params={"range": "1d", "interval": "1m"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=timeout,
        )
        response.raise_for_status()
        result = response.json().get("chart", {}).get("result") or []
        if not result:
            raise ValueError(f"{self.name}: no data for {info.symbol}")
        item = result[0]
        meta = item.get("meta") or {}
        price = meta.get("regularMarketPrice")
        previous = meta.get("previousClose") or meta.get("chartPreviousClose")
        if price is None:
            quotes = item.get("indicators", {}).get("quote") or [{}]
            closes = quotes[0].get("close") or []
            price = next((value for value in reversed(closes) if value is not None), None)
        change_pct = None
        if price is not None and previous not in (None, 0):
            change_pct = (price - previous) / previous * 100
        return finalize_quote(
            {
                "name": meta.get("longName") or meta.get("shortName"),
                "price": price,
                "pre_close": previous,
                "change_pct": change_pct,
                "time": format_yahoo_time(meta.get("regularMarketTime"), meta.get("exchangeTimezoneName")),
            },
            info,
            self.name,
        )

    def fetch_many(
        self,
        infos: list[SymbolInfo],
        *,
        timeout: float,
        source_config: SourceConfig,
    ) -> list[dict[str, Any]]:
        rows = []
        for info in infos:
            try:
                rows.append(self.fetch_one(info, timeout=timeout, source_config=source_config))
            except Exception:
                continue
        if not rows:
            raise ValueError(f"{self.name}: no parseable quotes")
        return rows


class YahooAltSource(YahooSource):
    name = "yahoo_alt"
    host = "query2.finance.yahoo.com"
