# etfline

获取行业/概念板块列表与真实资金数据，能力不依赖 Web。

## API

```python
from store_skill.etfline import list_sectors, get_sector_lines, get_market_lines

list_sectors(sector_type="industry", source="auto")
get_sector_lines(["BK0475"], date="2026-08-18", source="eastmoney")
get_market_lines(date="2026-08-18")
```

`source` 支持 `auto/eastmoney/ths/sina`，旧调用仍兼容。返回 `data.source` 是实际来源；`meta` 含 `requested_source/fallbacks/errors/granularity/update_interval`。列表项为 `code/name/price/change_pct/main_net`，资金单位元。

## 来源与真实性

- 东方财富：行业、概念当前快照和真实分钟累计主力净流入，约 1 分钟更新；公共接口可用时可返回当天或近期数据，范围由上游决定。
- 同花顺：直接解析行业/概念资金表真实当前净额（亿元转元）。`THS-...` 是 JINX 按名称生成的稳定命名空间代码，不是同花顺官方代码。
- FastAPI lifespan 后台任务在北京时间工作日 `09:30-11:30`、`13:00-15:00` 每 5 分钟调用同花顺行业和概念列表；浏览器无需保持打开。成功列表由本 Skill 写入 `JINX_ETFLINE_CACHE_DIR`（默认 `~/.cache/jinx/etfline`）的 5 分钟桶；Docker 使用持久卷 `/var/lib/jinx/etfline`。只保存服务运行后实际取得的快照，不回填、不插值、不补造此前历史；至少两个点才形成曲线。
- 新浪：约 5 分钟行情快照，`main_net=None`。接口不含可靠主力净流入，不能用于资金气泡或资金线，也不会用成交额冒充。
- 自动列表依次尝试东财、同花顺、新浪，并整套切换来源和板块代码。各平台板块分类、资金口径和更新时间不同，不得把数字混接为一条线。

日期默认当天。手工资金线选择不限制板块数量；东方财富请求最多 5 路并发，并保持返回顺序与输入代码一致，部分失败写入 `meta.warnings`。这些免费公共数据可能延迟、限流、断连或改版，能力会返回中文错误而不伪造数据；缓存写入为原子替换，写失败不影响实时列表查询。


`get_market_lines(date=None)` 固定获取上证指数 `000001`、科创综指 `000680`（科创板整体代表）、科创50 `000688` 的真实分时收盘点位。优先东方财富指数分时，单指数失败回退新浪；三条不完整时整体返回友好错误，不补造数据。

Web 仅把这三条指数作为右侧小图的非资金参考；资金主图只展示真实资金净流入/净流出，不把指数点位或涨跌幅混入资金线。
