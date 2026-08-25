# JINX 开发与维护规范

本文件约束人工开发和 AI 辅助开发。目标是保持项目简单、可测试、可迁移。

## 1. 代码原则

- 代码必须简洁、易读，优先直白实现，避免无必要的抽象和层级。
- 函数只承担一个清晰职责；名称应表达用途。
- 配置、密钥和 Token 使用环境变量，不写入代码或 Git。
- 用户可见的错误必须使用中文，并给出可执行的处理建议。

## 2. Store Skill

- 可复用的数据和业务能力放在 `store_skill/<能力名>/`。
- 每个能力通过 `__init__.py` 暴露少量稳定的公共函数。
- Skill 不依赖 FastAPI、HTML 或 Web 状态，确保脚本和 Agent 都能调用。
- 每个能力必须有 `SKILL.md`，写清用途、输入、输出、限制和示例。

新增或修改 `store_skill/` 能力后，必须同时：

1. 在 `store_skill/test/` 新增或更新对应测试/样例。
2. 更新 `store_skill/README.md` 的能力列表。
3. API、字段或工作流变化时，更新
   `store_skill/agent_skill/a-share-analysis/`。
4. 运行对应测试，并确认失败信息清晰。

## 3. Agent Skill

- Agent Skill 的维护源放在 `store_skill/agent_skill/`。
- `.cursor/skills/` 只作为 Cursor 自动发现入口，指向维护源。
- Agent 不得编造缺失数据；调用失败时必须如实报告。
- Agent Skill 中引用的命令必须实际运行验证。

## 4. Web

- Web 保持薄层：接收参数、调用 Store Skill、展示结果。
- 每个页面放在 `web/pages/<页面名>/`，包含自己的路由和模板。
- 抓取、计算和数据源回退逻辑不得写进页面代码。
- 新页面需要在 `web/app.py` 注册路由。

## 5. 依赖与 Docker

- Python 依赖同时维护 `requirements.txt` 和 `pyproject.toml`。
- Web、依赖或部署文件变化后，重新构建并验证 Docker。
- 服务固定监听 `0.0.0.0:3788`。

## 6. 完成前检查

```bash
python -m compileall -q store_skill web
python -m store_skill.test.test_getprice
python -m store_skill.test.test_getkline
python -m store_skill.test.test_etfline
python -m store_skill.test.test_etfline_sampler
docker compose -f docker/docker-compose.yml up --build -d
```

只运行与本次修改相关且必要的测试；不得以删除测试或隐藏错误通过验证。
