# Story P4-E3-S6：实现 Agent run 查询结果消费

状态：待实现  
Sprint：Sprint 3  
优先级：P1  
Epic：P4-E3

## 用户故事

作为 `apps/api` 的上层业务流程，我希望能通过 `external_agent_run_id` 查询 `apps/agents` 的最终结果，以便异步或重试中的 Agent run 能在完成后被安全消费。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 在 `HttpAgentRuntime` 中实现 `GET /agent-runs/{id}` 查询消费，支持 `running`、`retrying`、`succeeded`、`failed` 状态。

**建议文件：**

- Modify: `apps/api/app/agents/http_runtime.py`
- Modify: `apps/api/app/services/`
- Test: `apps/api/tests/agents/test_agent_run_result_consumption.py`

**验收标准：**

- 可通过 `external_agent_run_id` 查询 run 当前状态和最终输出。
- `running` / `retrying` 不被误判为失败。
- `succeeded` 时返回可被上层 service 使用的结构化输出。
- `failed` 时保留错误类型、错误消息和是否可重试信息。

**非目标：**

- 不实现轮询 worker。
- 不删除 `apps/api` retry worker。
- 不写入 core 业务表。

## Codex 提示词

```text
请执行 P4-E3-S6：实现 Agent run 查询结果消费。
要求使用 TDD；支持 running/retrying/succeeded/failed；不得让 apps/api 成为 Agent run 事实源；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- `apps/api.agent_task_runs` 第四阶段只做兼容摘要。
- `apps/agents` 是 Agent 执行事实源。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。
