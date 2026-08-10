# 数据接口参考

## Python API

```python
from store_skill.getprice import get_quote, get_quotes
from store_skill.getkline import get_kline
```

### 实时价格

```python
get_quote("600519")
get_quotes(["600519", "000001"])
```

返回字段：

```text
symbol, market, name, price, change_pct, open, high, low,
pre_close, volume, amount, time, source
```

### K 线

```python
get_kline("600519", period="daily")
```

返回字段：

```text
symbol, market, period, chart_type, source, items
```

`items` 包含：

```text
time, open, close, high, low, volume, amount, average, ma5
```

所有接口返回 `SkillResult`。仅在 `result.ok` 为 `True` 时使用
`result.data`；失败时读取 `result.error`。
