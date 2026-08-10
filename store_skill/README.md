# Store Skill 能力说明

`store_skill/` 存放可独立调用的 Python 能力。Web 只负责接收请求和展示结果。

## 当前能力

### getprice

获取 A 股近实时价格，支持东财、新浪、雪球和可选 Tushare，并可配置主源及回退顺序。

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
