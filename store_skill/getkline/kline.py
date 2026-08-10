from __future__ import annotations

from datetime import datetime, timedelta
from math import isnan
from typing import Any

import akshare as ak

from store_skill.getkline.types import SkillResult
from store_skill.getprice.normalize import normalize_symbol


PERIODS = ("intraday", "five_day", "daily", "weekly", "monthly")
_HISTORY_DAYS = {"daily": 240, "weekly": 730, "monthly": 1825}
_HISTORY_LIMIT = {"daily": 120, "weekly": 104, "monthly": 60}


def _is_etf(symbol: str) -> bool:
    return symbol.startswith(("15", "51", "56", "58"))


def _number(value: Any) -> float | None:
    try:
        number = float(value)
        return None if isnan(number) else number
    except (TypeError, ValueError):
        return None


def _items(df, time_column: str) -> list[dict[str, Any]]:
    rows = []
    for _, row in df.iterrows():
        rows.append(
            {
                "time": str(row[time_column]),
                "open": _number(row.get("开盘")),
                "close": _number(row.get("收盘")),
                "high": _number(row.get("最高")),
                "low": _number(row.get("最低")),
                "volume": _number(row.get("成交量")),
                "amount": _number(row.get("成交额")),
                "average": _number(row.get("均价")),
            }
        )
    return rows


def _sina_items(df) -> list[dict[str, Any]]:
    rows = []
    for _, row in df.iterrows():
        volume = _number(row.get("volume"))
        amount = _number(row.get("amount"))
        rows.append(
            {
                "time": str(row.get("day", row.get("date"))),
                "open": _number(row.get("open")),
                "close": _number(row.get("close")),
                "high": _number(row.get("high")),
                "low": _number(row.get("low")),
                "volume": volume,
                "amount": amount,
                "average": round(amount / volume, 3) if amount and volume else None,
            }
        )
    return rows


def _add_ma5(items: list[dict[str, Any]]) -> None:
    closes: list[float] = []
    for item in items:
        close = item["close"]
        if close is None:
            item["ma5"] = None
            continue
        closes.append(close)
        item["ma5"] = round(sum(closes[-5:]) / 5, 3) if len(closes) >= 5 else None


def _eastmoney_intraday(
    symbol: str, five_days: bool, is_etf: bool
) -> list[dict[str, Any]]:
    now = datetime.now()
    start = now - timedelta(days=14)
    fetch = ak.fund_etf_hist_min_em if is_etf else ak.stock_zh_a_hist_min_em
    df = fetch(
        symbol=symbol,
        start_date=start.strftime("%Y-%m-%d 09:30:00"),
        end_date=(now + timedelta(days=1)).strftime("%Y-%m-%d 15:00:00"),
        period="5" if five_days else "1",
        adjust="",
    )
    if df is None or df.empty:
        return []

    dates = df["时间"].astype(str).str[:10]
    trading_dates = list(dict.fromkeys(dates))
    keep = trading_dates[-5:] if five_days else trading_dates[-1:]
    return _items(df[dates.isin(keep)], "时间")


def _eastmoney_history(
    symbol: str, period: str, is_etf: bool
) -> list[dict[str, Any]]:
    now = datetime.now()
    start = now - timedelta(days=_HISTORY_DAYS[period])
    fetch = ak.fund_etf_hist_em if is_etf else ak.stock_zh_a_hist
    kwargs = {
        "symbol": symbol,
        "period": period,
        "start_date": start.strftime("%Y%m%d"),
        "end_date": (now + timedelta(days=1)).strftime("%Y%m%d"),
        "adjust": "",
    }
    if not is_etf:
        kwargs["timeout"] = 10
    df = fetch(
        **kwargs,
    )
    if df is None or df.empty:
        return []
    return _items(df.tail(_HISTORY_LIMIT[period]), "日期")


def _sina_intraday(symbol: str, five_days: bool) -> list[dict[str, Any]]:
    df = ak.stock_zh_a_minute(
        symbol=symbol,
        period="5" if five_days else "1",
        adjust="",
    )
    if df is None or df.empty:
        return []
    dates = df["day"].astype(str).str[:10]
    trading_dates = list(dict.fromkeys(dates))
    keep = trading_dates[-5:] if five_days else trading_dates[-1:]
    return _sina_items(df[dates.isin(keep)])


def _sina_history(
    symbol: str, period: str, is_etf: bool
) -> list[dict[str, Any]]:
    now = datetime.now()
    start = now - timedelta(days=_HISTORY_DAYS[period])
    if is_etf:
        df = ak.fund_etf_hist_sina(symbol=symbol)
        if df is not None and not df.empty:
            dates = df["date"].astype("datetime64[ns]")
            df = df[dates >= start].copy()
    else:
        df = ak.stock_zh_a_daily(
            symbol=symbol,
            start_date=start.strftime("%Y%m%d"),
            end_date=(now + timedelta(days=1)).strftime("%Y%m%d"),
            adjust="",
        )
    if df is None or df.empty:
        return []

    if period in {"weekly", "monthly"}:
        dates = df["date"].astype("datetime64[ns]")
        groups = dates.dt.to_period("W-FRI" if period == "weekly" else "M")
        df = (
            df.assign(date=dates)
            .groupby(groups, as_index=False)
            .agg(
                date=("date", "last"),
                open=("open", "first"),
                close=("close", "last"),
                high=("high", "max"),
                low=("low", "min"),
                volume=("volume", "sum"),
                amount=("amount", "sum"),
            )
        )
    return _sina_items(df.tail(_HISTORY_LIMIT[period]))


def get_kline(symbol: str, period: str = "intraday") -> SkillResult:
    """Return normalized OHLCV data for an A-share symbol."""
    period = period.strip().lower()
    if period not in PERIODS:
        return SkillResult(ok=False, error=f"unsupported period: {period}")

    try:
        info = normalize_symbol(symbol)
    except ValueError as exc:
        return SkillResult(ok=False, error=str(exc))

    errors = []
    is_etf = _is_etf(info.symbol)
    sources = (
        (
            "eastmoney",
            lambda: _eastmoney_intraday(
                info.symbol, period == "five_day", is_etf
            )
            if period in {"intraday", "five_day"}
            else _eastmoney_history(info.symbol, period, is_etf),
        ),
        (
            "sina",
            lambda: _sina_intraday(info.sina_code, period == "five_day")
            if period in {"intraday", "five_day"}
            else _sina_history(info.sina_code, period, is_etf),
        ),
    )

    tried = []
    for source, fetch in sources:
        tried.append(source)
        try:
            items = fetch()
            if not items:
                raise ValueError("empty response")
            _add_ma5(items)
            return SkillResult(
                ok=True,
                data={
                    "symbol": info.symbol,
                    "market": info.market,
                    "period": period,
                    "chart_type": "line"
                    if period in {"intraday", "five_day"}
                    else "candlestick",
                    "items": items,
                    "source": source,
                },
                meta={"tried": tried, "used": source},
            )
        except Exception as exc:  # public sources fail independently
            errors.append(f"{source}: {exc}")

    return SkillResult(ok=False, error=" | ".join(errors))
