from __future__ import annotations

from typing import Any

from store_skill.getprice.config import SourceConfig
from store_skill.getprice.normalize import SymbolInfo
from store_skill.getprice.sources.base import finalize_quote


def _series_to_map(df) -> dict[str, Any]:
    if "item" in df.columns and "value" in df.columns:
        return {str(r["item"]): r["value"] for _, r in df.iterrows()}
    if df.shape[1] >= 2:
        return {str(row.iloc[0]): row.iloc[1] for _, row in df.iterrows()}
    raise ValueError("xueqiu: unexpected dataframe shape")


class XueqiuSource:
    name = "xueqiu"

    def fetch_one(
        self,
        info: SymbolInfo,
        *,
        timeout: float,
        source_config: SourceConfig,
    ) -> dict[str, Any]:
        del timeout
        import akshare as ak

        kwargs: dict[str, Any] = {"symbol": info.xq_code}
        cookie = (source_config.cookie or "").strip()
        if cookie:
            # newer akshare versions accept token/cookie differently; try common kw
            try:
                df = ak.stock_individual_spot_xq(symbol=info.xq_code, token=cookie)
            except TypeError:
                df = ak.stock_individual_spot_xq(**kwargs)
        else:
            df = ak.stock_individual_spot_xq(**kwargs)

        if df is None or getattr(df, "empty", True):
            raise ValueError(f"xueqiu: empty quote for {info.symbol}")

        mapping = _series_to_map(df)
        return finalize_quote(
            {
                "name": mapping.get("名称") or mapping.get("name"),
                "price": mapping.get("现价") or mapping.get("最新") or mapping.get("当前价"),
                "change_pct": mapping.get("涨跌幅"),
                "open": mapping.get("今开") or mapping.get("开盘"),
                "high": mapping.get("最高"),
                "low": mapping.get("最低"),
                "pre_close": mapping.get("昨收"),
                "volume": mapping.get("成交量"),
                "amount": mapping.get("成交额"),
                "time": mapping.get("时间") or mapping.get("更新时间"),
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
