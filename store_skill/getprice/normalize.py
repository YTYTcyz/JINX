from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class SymbolInfo:
    symbol: str  # 600519
    market: str  # SH / SZ / BJ
    sina_code: str  # sh600519
    em_code: str  # 600519
    xq_code: str  # SH600519
    ts_code: str  # 600519.SH


_PREFIX_RE = re.compile(r"^(sh|sz|bj)(\d{6})$", re.IGNORECASE)
_SUFFIX_RE = re.compile(r"^(\d{6})\.(sh|sz|bj)$", re.IGNORECASE)
_DIGITS_RE = re.compile(r"^(\d{6})$")


def _market_from_code(code: str) -> str:
    if code.startswith(("5", "6", "9")):
        return "SH"
    if code.startswith(("4", "8")):
        return "BJ"
    return "SZ"


def normalize_symbol(raw: str) -> SymbolInfo:
    text = (raw or "").strip().upper().replace(" ", "")
    if not text:
        raise ValueError("empty stock symbol")

    market: str | None = None
    code: str | None = None

    m = _PREFIX_RE.match(text)
    if m:
        market = m.group(1).upper()
        code = m.group(2)
    else:
        m = _SUFFIX_RE.match(text)
        if m:
            code = m.group(1)
            market = m.group(2).upper()
        else:
            m = _DIGITS_RE.match(text)
            if m:
                code = m.group(1)
                market = _market_from_code(code)

    if not code or not market:
        raise ValueError(f"unsupported stock symbol: {raw!r}")

    lower_mkt = market.lower()
    return SymbolInfo(
        symbol=code,
        market=market,
        sina_code=f"{lower_mkt}{code}",
        em_code=code,
        xq_code=f"{market}{code}",
        ts_code=f"{code}.{market}",
    )
