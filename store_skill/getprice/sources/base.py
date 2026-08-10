from __future__ import annotations

from typing import Any, Protocol

from store_skill.getprice.config import SourceConfig
from store_skill.getprice.normalize import SymbolInfo


def empty_quote(info: SymbolInfo, source: str) -> dict[str, Any]:
    return {
        "symbol": info.symbol,
        "market": info.market,
        "name": None,
        "price": None,
        "change_pct": None,
        "open": None,
        "high": None,
        "low": None,
        "pre_close": None,
        "volume": None,
        "amount": None,
        "time": None,
        "source": source,
    }


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if text in {"", "-", "--", "None", "nan", "NaN"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def finalize_quote(payload: dict[str, Any], info: SymbolInfo, source: str) -> dict[str, Any]:
    quote = empty_quote(info, source)
    quote.update(payload)
    quote["symbol"] = info.symbol
    quote["market"] = info.market
    quote["source"] = source

    for key in ("price", "change_pct", "open", "high", "low", "pre_close", "volume", "amount"):
        quote[key] = _to_float(quote.get(key))

    price = quote["price"]
    pre_close = quote["pre_close"]
    if quote["change_pct"] is None and price is not None and pre_close not in (None, 0):
        quote["change_pct"] = round((price - pre_close) / pre_close * 100, 4)

    if quote["price"] is None:
        raise ValueError(f"{source}: missing price for {info.symbol}")
    return quote


class QuoteSource(Protocol):
    name: str

    def fetch_one(
        self,
        info: SymbolInfo,
        *,
        timeout: float,
        source_config: SourceConfig,
    ) -> dict[str, Any]: ...

    def fetch_many(
        self,
        infos: list[SymbolInfo],
        *,
        timeout: float,
        source_config: SourceConfig,
    ) -> list[dict[str, Any]]: ...
