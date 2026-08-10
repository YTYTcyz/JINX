from __future__ import annotations

from typing import Any

from store_skill.getprice.config import SourceConfig
from store_skill.getprice.normalize import SymbolInfo
from store_skill.getprice.sources.base import finalize_quote


class TushareSource:
    name = "tushare"

    def fetch_one(
        self,
        info: SymbolInfo,
        *,
        timeout: float,
        source_config: SourceConfig,
    ) -> dict[str, Any]:
        del timeout
        token = (source_config.token or "").strip()
        if not token:
            raise ValueError("tushare: token missing (set JINX_TUSHARE_TOKEN)")

        try:
            import tushare as ts
        except ImportError as exc:
            raise ValueError("tushare: package not installed (pip install tushare)") from exc

        pro = ts.pro_api(token)
        # realtime_quote is available on newer tushare; fall back to daily last close
        try:
            df = pro.realtime_quote(ts_code=info.ts_code)
        except Exception:
            df = None

        if df is not None and not getattr(df, "empty", True):
            row = df.iloc[0]
            return finalize_quote(
                {
                    "name": row.get("name"),
                    "price": row.get("price") or row.get("close"),
                    "change_pct": row.get("pct_chg"),
                    "open": row.get("open"),
                    "high": row.get("high"),
                    "low": row.get("low"),
                    "pre_close": row.get("pre_close"),
                    "volume": row.get("volume") or row.get("vol"),
                    "amount": row.get("amount"),
                    "time": row.get("time") or row.get("trade_time") or row.get("date"),
                },
                info,
                self.name,
            )

        # fallback: latest daily bar (not true realtime)
        daily = pro.daily(ts_code=info.ts_code, limit=1)
        if daily is None or getattr(daily, "empty", True):
            raise ValueError(f"tushare: no data for {info.ts_code}")
        row = daily.iloc[0]
        return finalize_quote(
            {
                "name": None,
                "price": row.get("close"),
                "change_pct": row.get("pct_chg"),
                "open": row.get("open"),
                "high": row.get("high"),
                "low": row.get("low"),
                "pre_close": row.get("pre_close"),
                "volume": row.get("vol"),
                "amount": row.get("amount"),
                "time": str(row.get("trade_date")),
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
        return [
            self.fetch_one(info, timeout=timeout, source_config=source_config)
            for info in infos
        ]
