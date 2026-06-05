# Story P4-E1-S3：定义统一 Agent Run request / response envelope

状态：待实现  
Sprint：Sprint 1  
优先级：P0  
Epic：P4-E1

## 用户故事

作为 API 与 Agent 服务集成开发者，我希望所有 Agent Run API 使用统一 request / response envelope，以便 `apps/api` 可以稳定调用、校验和记录兼容摘要。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 定义 `phase4.agent.run.v1` 的请求和响应 schema。

**建议文件：**

- Create: `apps/agents/app/schemas/agent_run.py`
- Modify: `apps/agents/app/schemas/__init__.py`
- Test: `apps/agents/tests/test_agent_run_envelope.py`

**验收标准：**

- Request 包含 `request_id`、`agent_task_run_id`、`trigger_source`、`agent_mode`、`input`、`options`。
- Response 包含 `schema_version`、`agent_service_run_id`、`request_id`、`status`、`agent_type`、`agent_mode`、`output`、`audit`、`error`。
- status 支持 `succeeded`、`failed`、`blocked`、`running`、`retrying`。
- schema 可被 OpenAPI 正确展示。

**非目标：**

- 不实现具体 Agent endpoint。
- 不实现数据库状态存储。

## Codex 提示词

```text
请执行 P4-E1-S3：定义统一 Agent Run request / response envelope。
要求使用 Pydantic schema 和 TDD；不得实现具体 Agent 业务逻辑；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- envelope 必须保留 `writes_core_tables=false` 的审计表达能力。
- 任何 Agent 输出都不得绕过 `apps/api` 业务校验。

