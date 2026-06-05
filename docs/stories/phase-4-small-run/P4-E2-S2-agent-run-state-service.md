# Story P4-E2-S2：实现 Agent run 创建、状态流转和失败记录

状态：待实现  
Sprint：Sprint 2  
优先级：P0  
Epic：P4-E2

## 用户故事

作为 Agent 服务开发者，我希望 `apps/agents` 能创建 run、更新状态并记录失败，以便它成为 LangGraph Agent 执行事实源。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 实现 `agent_service_runs` 的创建、状态流转、失败记录和查询服务。

**建议文件：**

- Create: `apps/agents/app/services/agent_service_runs.py`
- Modify: `apps/agents/app/schemas/agent_service_run.py`
- Test: `apps/agents/tests/test_agent_run_state_service.py`

**验收标准：**

- 支持创建 pending run。
- 支持状态流转到 running、retrying、succeeded、failed、blocked、cancelled。
- 失败记录包含 `error_type` 和 `error_message`。
- 状态流转更新 `started_at`、`finished_at`、`updated_at`。
- 非法状态流转被拒绝或显式处理。

**非目标：**

- 不实现具体 Agent API。
- 不实现重试调度。

## Codex 提示词

```text
请执行 P4-E2-S2：实现 Agent run 创建、状态流转和失败记录。
要求使用 TDD；apps/agents 是 Agent 执行事实源；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- 不写 core 业务表。
- 不隐藏失败原因。

