# Store Skill 能力说明

`store_skill/` 存放可独立调用的 Python 能力。Web 只负责接收请求和展示结果。

## 当前能力

### getprice

获取 A 股、港股、美股近实时价格，支持东财、新浪、Yahoo、雪球和可选 Tushare，并可配置主源及回退顺序。

```python
from store_skill.getprice import get_quote, get_quotes

get_quote("600519")
get_quotes(["600519", "000001"])
```

详细说明：[getprice/SKILL.md](getprice/SKILL.md)

### getkline

获取分时、五日、日 K、周 K、月 K 和 MA5。

```python
from store_skill.getkline import get_kline

get_kline("600519", period="daily")
```

详细说明：[getkline/SKILL.md](getkline/SKILL.md)

### etfline

获取东财/同花顺/新浪行业与概念板块；东财为约 1 分钟资金线，同花顺为本服务交易时段后台积累的真实 5 分钟快照，新浪仅约 5 分钟行情且无可靠主力净流入；另提供上证指数、科创综指、科创50真实分时点位（东财优先、新浪回退）。

```python
from store_skill.etfline import list_sectors, get_sector_lines, get_market_lines

list_sectors("industry", source="auto")
get_sector_lines(["BK0475"])
get_market_lines()
```

详细说明：[etfline/SKILL.md](etfline/SKILL.md)

免费公共数据可能延迟、限流或改版。FastAPI 后台采样不依赖浏览器，Docker 缓存使用持久卷；同花顺只能从服务启动后积累实际快照，不还原历史。不同平台分类、口径和代码不可混接。

## Agent Skill

Agent Skill 的维护源位于：

```text
store_skill/agent_skill/a-share-analysis/
```

`.cursor/skills/a-share-analysis/` 是 Cursor 自动发现入口。修改 Agent
能力时只维护 `store_skill/agent_skill/` 中的源文件。

## 新增能力约定

每个能力使用独立文件夹：

```text
store_skill/<能力名>/
  __init__.py   对外导出函数
  SKILL.md      输入、输出、限制和示例
  ...           具体实现
```

新增后请同步更新：

1. 本文件的“当前能力”列表。
2. `store_skill/test/` 中的测试。
3. 对应能力的 `SKILL.md`。
4. 相关 Agent Skill。
