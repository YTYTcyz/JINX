---
name: a-share-analysis
description: 获取并分析 A 股、ETF 的实时价格、K 线及行业/概念板块资金线数据。用户询问股票价格、涨跌、分时、K 线、MA5、行情走势，或开发相关行情功能时使用。
---

# A 股行情分析

使用项目现有 Python 能力获取真实数据，不自行编造行情。

## 获取数据

在项目根目录执行：

```bash
python store_skill/agent_skill/a-share-analysis/scripts/stock_data.py 600519 --period daily
```

支持 `intraday`、`five_day`、`daily`、`weekly`、`monthly`。

仅查询实时价格：

```bash
python store_skill/agent_skill/a-share-analysis/scripts/stock_data.py 600519 --quote-only
```

脚本输出 JSON。数据字段见 [reference.md](reference.md)。

## 板块资金线

可调用 `list_sectors(sector_type, source)`、不限数量的 `get_sector_lines(codes, date, source)` 与固定三指数的 `get_market_lines(date)`。`auto` 列表按东财、同花顺、新浪整套回退，并须把实际 `data.source` 传给资金线。东财公共接口可用时返回约 1 分钟真实累计资金线；同花顺上游只有当前资金快照，由 FastAPI 服务端在交易时段每 5 分钟采样并持久化，不依赖页面开启，也不能还原服务运行前轨迹；新浪约 5 分钟行情且 `main_net=None`，不得用于资金分析。不同来源的分类、代码、资金口径和更新时间不可混用；任何来源均不得补造缺失历史。大盘接口返回上证指数、科创综指（科创板整体代表）、科创50真实分时收盘点位，东财失败时回退新浪。

## 工作流程

1. 提取六位证券代码；代码不明确时先询问。
2. 执行脚本获取价格和用户指定周期的数据。
3. 检查 `ok`；失败时说明中文原因，不分析缺失数据。
4. 将“数据事实”和“分析判断”分开表达。
5. 未指定周期时默认使用 `daily`。

## 回答规范

- 先报告代码、名称、现价、涨跌幅、数据时间和来源。
- K 线分析只描述数据支持的趋势、振幅和 MA5 关系。
- 明确区分盘中数据与收盘数据。
- 不承诺收益，不提供确定性买卖结论。
- 免费公共数据源可能延迟、限流、断连或改版，异常时如实说明。

## 修改项目代码时

- 遵守根目录 [VIBE_REQUIREMENTS.md](../../../VIBE_REQUIREMENTS.md)。
- 数据能力放在 `store_skill/`，Web 中不写抓取逻辑。
- 新增或修改能力时更新测试、能力说明和本 Agent Skill。
