# Story P4-E2-S3：实现可重试错误分类和重试策略

状态：待实现  
Sprint：Sprint 2  
优先级：P0  
Epic：P4-E2

## 用户故事

作为 Agent 服务开发者，我希望 `apps/agents` 能根据结构化错误类型决定是否重试，以便后续逐步去掉 `apps/api` 的 Agent retry worker。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 实现 retryable error 分类、retry_count 更新、next_retry_at 计算和最大重试次数限制。

**建议文件：**

- Create: `apps/agents/app/services/retry_policy.py`
- Modify: `apps/agents/app/services/agent_service_runs.py`
- Test: `apps/agents/tests/test_agent_retry_policy.py`

**验收标准：**

- `timeout_error`、`provider_rate_limited`、`transient_network_error` 可重试。
- `schema_validation_error`、`evidence_validation_error`、`risk_blocked`、`contract_mismatch` 不可重试。
- 默认最大重试次数为 2。
- 超过最大重试次数后状态为 failed。
- 重试记录更新 `retry_count` 和 `next_retry_at`。

**非目标：**

- 不实现后台 worker。
- 不调用真实 LLM。

## Codex 提示词

```text
请执行 P4-E2-S3：实现可重试错误分类和重试策略。
要求使用 TDD；重试由 apps/agents 负责；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- schema、证据、风险阻断错误不得重试。
- 不因重试绕过合规硬规则。

