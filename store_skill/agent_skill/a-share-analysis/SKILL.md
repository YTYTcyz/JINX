---
name: a-share-analysis
description: 获取并分析 A 股、ETF 的实时价格和 K 线数据。用户询问股票价格、涨跌、分时、K 线、MA5、行情走势，或开发相关行情功能时使用。
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
- 公共数据源可能延迟或限流，异常时如实说明。

## 修改项目代码时

- 遵守根目录 [VIBE_REQUIREMENTS.md](../../../VIBE_REQUIREMENTS.md)。
- 数据能力放在 `store_skill/`，Web 中不写抓取逻辑。
- 新增或修改能力时更新测试、能力说明和本 Agent Skill。
