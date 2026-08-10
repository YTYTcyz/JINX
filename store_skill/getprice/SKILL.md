---
name: getprice
description: Fetch A-share near-realtime quotes via eastmoney/sina/xueqiu/tushare with CONFIG primary and fallback.
---

# getprice

获取 A 股近实时股价。多数据源可配，失败按 fallback 回退。

## 用法

```python
from store_skill.getprice import get_quote, get_quotes, QuoteConfig

r = get_quote("600519")
print(r.ok, r.data)

# 只用新浪
r = get_quote("600519", config=QuoteConfig(primary="sina", fallback=[]))

# 批量
r = get_quotes(["600519", "000001"])
```

## CONFIG / 环境变量

| 变量 | 含义 |
|------|------|
| `JINX_QUOTE_PRIMARY` | 主源：`eastmoney` / `sina` / `xueqiu` / `tushare` |
| `JINX_QUOTE_FALLBACK` | 逗号分隔回退链，如 `sina,xueqiu` |
| `JINX_QUOTE_TIMEOUT` | 超时秒数 |
| `JINX_SINA_REFERER` | 新浪 Referer |
| `JINX_XUEQIU_COOKIE` | 雪球可选 cookie |
| `JINX_TUSHARE_TOKEN` | 有值才启用 tushare |

默认：`primary=eastmoney`, `fallback=sina,xueqiu`。

## 返回字段

`symbol, market, name, price, change_pct, open, high, low, pre_close, volume, amount, time, source`

## 注意

- 公开源为轮询近实时，非交易所推送；仅供学习研究。
- 新浪请求需带 Referer（代码已处理）。
- tushare 无 token 或未安装包时会自动跳过。
