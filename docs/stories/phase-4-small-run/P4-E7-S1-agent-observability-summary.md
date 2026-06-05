# Story P4-E7-S1：汇总 agent_service_runs 与 apps/api 兼容摘要

状态：待实现  
Sprint：Sprint 7  
优先级：P1  
Epic：P4-E7

## 用户故事

作为第四阶段运行观察者，我希望能汇总 `agent_service_runs` 与 `apps/api.agent_task_runs.output_summary_json` 中的兼容摘要，以便跨服务追踪一次 Agent 调用的状态和结果。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 建立第四阶段 Agent 观测摘要，关联 `external_agent_run_id`、run 状态、错误类型、retry_count 和节点 trace 摘要。

**建议文件：**

- Create/Modify: `apps/api/app/services/agent_observability.py`
- Create/Modify: `apps/agents/app/services/observability.py`
- Create/Modify: `docs/reports/phase-4/agent-observability-summary.md`
- Test: `apps/api/tests/test_agent_observability_summary.py`

**验收标准：**

- 能从 `apps/api` 兼容摘要定位到 `apps/agents.agent_service_runs`。
- 摘要包含状态、耗时、错误类型、retry_count、executed_nodes。
- 不暴露 API Key 或敏感输入全文。
- 能区分 active_run 和 shadow_run。

**非目标：**

- 不建设完整监控平台。
- 不删除现有 `apps/api` retry worker。
- 不改变业务状态。

## Codex 提示词

```text
请执行 P4-E7-S1：汇总 agent_service_runs 与 apps/api 兼容摘要。
要求使用 TDD；摘要不得泄露 API Key 或敏感输入全文；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- 观测只用于排障和阶段评估，不自动驱动业务写入。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。
