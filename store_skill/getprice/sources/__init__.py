from __future__ import annotations

from store_skill.getprice.sources.eastmoney import EastmoneySource
from store_skill.getprice.sources.sina import SinaSource
from store_skill.getprice.sources.tushare import TushareSource
from store_skill.getprice.sources.xueqiu import XueqiuSource

SOURCE_REGISTRY = {
    EastmoneySource.name: EastmoneySource(),
    SinaSource.name: SinaSource(),
    XueqiuSource.name: XueqiuSource(),
    TushareSource.name: TushareSource(),
}

__all__ = ["SOURCE_REGISTRY", "EastmoneySource", "SinaSource", "XueqiuSource", "TushareSource"]
