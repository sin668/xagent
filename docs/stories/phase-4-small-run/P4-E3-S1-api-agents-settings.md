# Story P4-E3-S1：新增 apps/api 调用 apps/agents 的配置

状态：待实现  
Sprint：Sprint 3  
优先级：P0  
Epic：P4-E3

## 用户故事

作为 `apps/api` 的维护者，我希望通过配置声明 `apps/agents` 的服务地址、内部 API Key 和超时，以便 `apps/api` 可以通过 HTTP 调用独立 Agent 服务，而不把 `apps/agents` 作为本地包注入。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`
- `docs/brainstorm/brainstorming-session-2026-06-04-第四阶段小范围运行-LangGraph-Agent迁移.md`

## Story 定义

**目标：** 在 `apps/api` 配置体系中新增 `AGENTS_BASE_URL`、`AGENTS_API_KEY`、`AGENTS_TIMEOUT_SECONDS`，默认指向本地 `apps/agents:8010`。

**建议文件：**

- Modify: `apps/api/app/core/config.py`
- Modify: `apps/api/.env.example`
- Modify: `apps/api/README.md`
- Test: `apps/api/tests/test_agents_settings.py`

**验收标准：**

- `apps/api` 可读取 `AGENTS_BASE_URL`、`AGENTS_API_KEY`、`AGENTS_TIMEOUT_SECONDS`。
- 本地默认地址使用 `http://localhost:8010` 或项目约定的等价地址。
- 未配置 API Key 时，调用端应显式失败或禁用 HTTP Agent runtime，不静默降级。
- 配置变更不影响 `apps/api` 现有 LLM Agent 默认行为。

**非目标：**

- 不实现 HTTP client。
- 不切换任何 Agent 执行入口。
- 不修改 `agent_task_runs` 表结构。

## Codex 提示词

```text
请执行 P4-E3-S1：新增 apps/api 调用 apps/agents 的配置。
要求使用 TDD；apps/api 只能通过 HTTP 配置指向 apps/agents；不得把 apps/agents 作为本地包 import；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- `apps/api` 中现有 LLM Agent 保持不变。
- `apps/agents` 独立服务运行，通过 HTTP API 交互。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。
