from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class SymbolInfo:
    symbol: str
    market: str  # SH / SZ / BJ / HK / US
    sina_code: str | None = None
    em_code: str | None = None
    xq_code: str | None = None
    ts_code: str | None = None
    yahoo_code: str | None = None


_PREFIX_RE = re.compile(r"^(sh|sz|bj)(\d{6})$", re.IGNORECASE)
_SUFFIX_RE = re.compile(r"^(\d{6})\.(sh|sz|bj)$", re.IGNORECASE)
_HK_PREFIX_RE = re.compile(r"^HK:(\d{5})$")
_HK_SUFFIX_RE = re.compile(r"^(\d{5})\.HK$")
_US_PREFIX_RE = re.compile(r"^US:([A-Z][A-Z0-9.\-]*)$")
_US_SUFFIX_RE = re.compile(r"^([A-Z][A-Z0-9.\-]*)\.US$")
_DIGITS_RE = re.compile(r"^(\d{6})$")


def _yahoo_hk_code(code: str) -> str:
    """Map canonical five-digit HK codes to Yahoo's four-digit ticker form."""
    return f"{code.lstrip('0') or '0':0>4}.HK"


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
    market = code = None
    m = _PREFIX_RE.match(text)
    if m:
        market, code = m.group(1).upper(), m.group(2)
    else:
        m = _SUFFIX_RE.match(text)
        if m:
            code, market = m.group(1), m.group(2).upper()
        else:
            m = _HK_PREFIX_RE.match(text) or _HK_SUFFIX_RE.match(text)
            if m:
                code, market = (m.group(1), "HK") if text.startswith("HK:") else (m.group(1), "HK")
            else:
                m = _US_PREFIX_RE.match(text) or _US_SUFFIX_RE.match(text)
                if m:
                    code, market = m.group(1), "US"
                else:
                    m = _DIGITS_RE.match(text)
                    if m:
                        code, market = m.group(1), _market_from_code(m.group(1))
    if not code or not market:
        raise ValueError(f"unsupported stock symbol: {raw!r}")
    if market == "HK":
        return SymbolInfo(code, market, yahoo_code=_yahoo_hk_code(code))
    if market == "US":
        return SymbolInfo(code, market, yahoo_code=code)
    lower = market.lower()
    return SymbolInfo(code, market, f"{lower}{code}", code, f"{market}{code}", f"{code}.{market}", code)
