from __future__ import annotations

from typing import Any

from store_skill.getprice.config import SourceConfig
from store_skill.getprice.normalize import SymbolInfo
from store_skill.getprice.sources.base import finalize_quote


def _map_from_bid_ask(df, info: SymbolInfo, source: str) -> dict[str, Any]:
    # akshare stock_bid_ask_em returns two columns: item / value
    mapping = {str(row.iloc[0]): row.iloc[1] for _, row in df.iterrows()}
    return finalize_quote(
        {
            "name": mapping.get("名称") or mapping.get("name"),
            "price": mapping.get("最新") or mapping.get("最新价"),
            "change_pct": mapping.get("涨跌幅"),
            "open": mapping.get("今开"),
            "high": mapping.get("最高"),
            "low": mapping.get("最低"),
            "pre_close": mapping.get("昨收"),
            "volume": mapping.get("总手") or mapping.get("成交量"),
            "amount": mapping.get("金额") or mapping.get("成交额"),
            "time": mapping.get("更新时间") or mapping.get("时间"),
        },
        info,
        source,
    )


class EastmoneySource:
    name = "eastmoney"

    def fetch_one(
        self,
        info: SymbolInfo,
        *,
        timeout: float,
        source_config: SourceConfig,
    ) -> dict[str, Any]:
        del timeout, source_config  # akshare uses its own session defaults
        import akshare as ak

        df = ak.stock_bid_ask_em(symbol=info.em_code)
        if df is None or getattr(df, "empty", True):
            raise ValueError(f"eastmoney: empty bid/ask for {info.symbol}")
        return _map_from_bid_ask(df, info, self.name)

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
