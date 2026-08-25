# 数据接口参考

## Python API

```python
from store_skill.getprice import get_quote, get_quotes
from store_skill.getkline import get_kline
from store_skill.etfline import list_sectors, get_sector_lines, get_market_lines
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

### 板块资金线

`list_sectors(sector_type="industry", source="auto")` 返回 `sector_type/source/items`。`source` 是实际来源，`items` 含 `code/name/price/change_pct/main_net`。东财和同花顺 `main_net` 为真实当前主力净流入（元）；新浪仅行情，值为 `None`。

`get_sector_lines(codes, date=None, source="auto")` 返回 `date/source/metric/unit/lines`。东财公共接口可用时提供约 1 分钟真实累计值；同花顺上游只有当前资金快照，由服务端在北京时间交易时段每 5 分钟实际采集并写入持久缓存，浏览器无需开启，只能从服务运行后积累且不补造此前轨迹；新浪约 5 分钟行情快照，无可靠主力净流入和资金线。`meta` 含请求来源、回退、错误、粒度与更新间隔。自动回退会整套切换来源和代码；各平台分类、资金口径和更新时间不同，不可混接。代码数量不限，东财抓取使用有上限并发并保序。

`get_market_lines(date=None)` 返回固定三条 `code/name/points(time,value)` 指数点位线：`000001` 上证指数、`000680` 科创综指、`000688` 科创50；`meta` 记录东财到新浪的回退与警告。

所有接口返回 `SkillResult`。仅在 `result.ok` 为 `True` 时使用
`result.data`；失败时读取 `result.error`。

以上来源均为免费公共接口，可能延迟、限流、断连或改版；缺失时必须报告，不得推算或伪造。
