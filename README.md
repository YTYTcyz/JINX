# JINX

学习/实验用项目。能力以 skill 形式放在 `store_skill/` 下，可被脚本或 Web 直接 import。
完整能力目录见 [`store_skill/README.md`](store_skill/README.md)。

Agent Skill 的维护源位于
`store_skill/agent_skill/a-share-analysis/`；`.cursor/skills/` 是
Cursor 自动发现入口。项目维护规范见 [`VIBE_REQUIREMENTS.md`](VIBE_REQUIREMENTS.md)。

## 安装

```bash
cd JINX
pip install -e .
# 可选 tushare
# pip install -e ".[tushare]"
```

## Skill: getprice

A 股、港股、美股近实时股价，多源自动回退（东财 / 新浪 / Yahoo / Yahoo 备用 / 雪球 / 可选 tushare）。

```python
from store_skill.getprice import get_quote, get_quotes, QuoteConfig

print(get_quote("600519"))
print(get_quote("600519", config=QuoteConfig(primary="sina", fallback=[])))
print(get_quote("HK:00700"))
print(get_quote("US:AAPL"))
print(get_quotes(["600519", "HK:00700", "US:AAPL"]))
```

环境变量：

- `JINX_QUOTE_PRIMARY`：主源（默认 `eastmoney`）
- `JINX_QUOTE_FALLBACK`：回退链（默认 `sina,yahoo,yahoo_alt,xueqiu`）
- `JINX_XUEQIU_COOKIE` / `JINX_TUSHARE_TOKEN`：可选

## 样例测试

```bash
python -m store_skill.test.test_getprice
JINX_QUOTE_PRIMARY=sina python -m store_skill.test.test_getprice
```

详情见 [`store_skill/getprice/SKILL.md`](store_skill/getprice/SKILL.md)。

## Skill: getkline

获取分时、五日、日 K、周 K、月 K 和 MA5：

```python
from store_skill.getkline import get_kline

print(get_kline("600519", period="daily"))
```

手动测试：

```bash
python -m store_skill.test.test_getkline
```

## Skill: etfline

获取东财、同花顺、新浪行业/概念板块数据；东财提供分钟资金线，同花顺提供本服务真实 5 分钟快照采样，新浪仅提供行情：

```python
from store_skill.etfline import list_sectors, get_sector_lines, get_market_lines

print(list_sectors("concept", source="auto"))
print(get_sector_lines(["BK0475"], source="eastmoney"))
print(get_market_lines())
```

Web 页面：<http://localhost:3788/etfline>，右侧包含版块选择；左侧主图只展示真实资金净流入/净流出。上证、科创综指和科创50的点位走势仅作为右侧小图参考，不参与资金主图。免费公共接口可能延迟、限流或改版；东方财富分钟数据可用日期由上游决定，新浪不提供可靠主力净流入。不同来源不会混接为一条资金线。

Web 服务启动后会在北京时间 A 股交易时段每 5 分钟采集同花顺行业与概念的真实当前快照，不依赖页面保持打开。样本只从服务运行后开始积累，不回填、不补造历史。Docker 将缓存持久化到命名卷 `etfline-cache`（容器内 `JINX_ETFLINE_CACHE_DIR=/var/lib/jinx/etfline`）。

## Agent Skill

人或 Agent 都可以通过统一脚本获取数据：

```bash
python store_skill/agent_skill/a-share-analysis/scripts/stock_data.py 600519 --period daily
python store_skill/agent_skill/a-share-analysis/scripts/stock_data.py 600519 --quote-only
```

## 项目结构

```text
store_skill/   独立、可复用的 Python 能力
web/pages/     每个页面一个文件夹
docker/        可移植的纯净 Docker 环境
start.sh       本机 Web 启动入口
```

## 启动 Web

在项目根目录运行：

```bash
bash start.sh
```

脚本会构建并在后台启动 Docker 服务，然后输出访问地址
<http://localhost:3788>。

新增页面时，在 `web/pages/<页面名>/` 放置路由与模板，并在
`web/app.py` 注册路由。

## Docker

`start.sh` 内部执行：

```bash
docker compose -f docker/docker-compose.yml up --build -d
```

打开 <http://localhost:3788>。停止服务：

```bash
docker compose -f docker/docker-compose.yml down
```
