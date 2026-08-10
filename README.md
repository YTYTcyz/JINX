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

A 股近实时股价，多源可配（东财 / 新浪 / 雪球 / 可选 tushare）。

```python
from store_skill.getprice import get_quote, get_quotes, QuoteConfig

print(get_quote("600519"))
print(get_quote("600519", config=QuoteConfig(primary="sina", fallback=[])))
print(get_quotes(["600519", "000001"]))
```

环境变量：

- `JINX_QUOTE_PRIMARY`：主源（默认 `eastmoney`）
- `JINX_QUOTE_FALLBACK`：回退链（默认 `sina,xueqiu`）
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

先安装依赖，然后运行根目录脚本：

```bash
pip install -r requirements.txt
./start.sh
```

打开 <http://localhost:3788>。开发时可启用自动重载：

```bash
./start.sh --reload
```

新增页面时，在 `web/pages/<页面名>/` 放置路由与模板，并在
`web/app.py` 注册路由。

## Docker

Docker 会从干净的 Python 3.12 环境安装 `requirements.txt`：

```bash
docker compose -f docker/docker-compose.yml up --build
```

打开 <http://localhost:3788>。停止服务：

```bash
docker compose -f docker/docker-compose.yml down
```
