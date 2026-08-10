---
name: getkline
description: 获取 A 股分时、五日、日 K、周 K、月 K 以及 MA5 数据。
---

# getkline

```python
from store_skill.getkline import get_kline

result = get_kline("600519", period="daily")
```

`period` 支持：

- `intraday`：最近交易日 1 分钟数据
- `five_day`：最近五个交易日 5 分钟数据
- `daily`：日 K，最多 120 条
- `weekly`：周 K，最多 104 条
- `monthly`：月 K，最多 60 条

每条数据包含 `time/open/close/high/low/volume/amount/average/ma5`。
数据来自东方财富公开接口（经 AKShare），属于近实时公开数据，不是交易所行情授权源。
