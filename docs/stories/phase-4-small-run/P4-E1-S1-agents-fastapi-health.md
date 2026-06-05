# Story P4-E1-S1：创建 apps/agents FastAPI 入口和 /health

状态：待实现  
Sprint：Sprint 1  
优先级：P0  
Epic：P4-E1

## 用户故事

作为第四阶段小范围运行的研发执行者，我希望 `apps/agents` 能作为独立 FastAPI 服务启动，并提供健康检查，以便 `apps/api` 可以通过 HTTP 调用独立 Agent 服务。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`
- `docs/brainstorm/brainstorming-session-2026-06-04-第四阶段小范围运行-LangGraph-Agent迁移.md`
- `apps/agents/README.md`

## Story 定义

**目标：** 创建 `apps/agents/app/main.py`，注册 FastAPI app 和 `/health`。

**建议文件：**

- Create/Modify: `apps/agents/app/main.py`
- Modify: `apps/agents/pyproject.toml`
- Test: `apps/agents/tests/test_health_api.py`

**验收标准：**

- `apps/agents` 可通过 `uvicorn app.main:app --host 0.0.0.0 --port 8010` 启动。
- `GET /health` 返回服务状态、服务名和版本。
- `/docs` 可访问并展示 OpenAPI。
- 不影响 `apps/api` 现有启动。

**非目标：**

- 不实现任何 Agent Run API。
- 不连接数据库。
- 不实现鉴权。

## Codex 提示词

```text
请执行 P4-E1-S1：创建 apps/agents FastAPI 入口和 /health。
要求使用 TDD；只实现本 Story；不得触碰 apps/api 现有 Agent 行为；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- `apps/agents` 不写 core 业务表。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。

