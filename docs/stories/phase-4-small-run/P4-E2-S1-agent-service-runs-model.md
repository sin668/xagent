# Story P4-E2-S1：新增 agent_service_runs 模型与迁移

状态：待实现  
Sprint：Sprint 2  
优先级：P0  
Epic：P4-E2

## 用户故事

作为 Agent 服务开发者，我希望 `apps/agents` 拥有自己的 `agent_service_runs` 运行状态表，以便 Agent 执行事实源从 `apps/api.agent_task_runs` 逐步迁移出来。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 在 `apps/agents` 中创建 `agent_service_runs` 数据模型、迁移和 schema。

**建议文件：**

- Create: `apps/agents/app/models/agent_service_run.py`
- Create/Modify: `apps/agents/app/db/`
- Create/Modify: `apps/agents/alembic/versions/`
- Create: `apps/agents/app/schemas/agent_service_run.py`
- Test: `apps/agents/tests/test_agent_service_runs_model.py`

**验收标准：**

- `agent_service_runs` 包含 agent_type、agent_mode、status、request_id、trigger_source、input_json、output_json、audit_json、retry_count、max_retries、error_type、error_message、时间字段。
- 模型和 schema 字段一致。
- 迁移可生成 PostgreSQL DDL。
- 不创建或修改 core 业务表。

**非目标：**

- 不创建 `agent_service_node_runs`。
- 不实现重试 worker。

## Codex 提示词

```text
请执行 P4-E2-S1：新增 agent_service_runs 模型与迁移。
要求使用 TDD；表只归 apps/agents 管理；不得写 customers、lead_sources、contact_methods、staging_leads；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- `apps/agents` 只写 Agent 运行表。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。

