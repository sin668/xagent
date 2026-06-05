# Story P4-E4-S1：实现 Deep Enrichment LangGraph HTTP API

状态：待实现  
Sprint：Sprint 4  
优先级：P0  
Epic：P4-E4

## 用户故事

作为 Agent 服务开发者，我希望 `apps/agents` 提供 Deep Enrichment 的 LangGraph HTTP API，以便 `apps/api` 可以通过 active_run 获取字段候选结果。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`
- `apps/agents/README.md`

## Story 定义

**目标：** 在 `apps/agents` 中实现 Deep Enrichment graph 和 `POST /agent-runs/deep-enrichment`。

**建议文件：**

- Create/Modify: `apps/agents/app/api/agent_runs.py`
- Create/Modify: `apps/agents/app/graphs/deep_enrichment.py`
- Create/Modify: `apps/agents/app/schemas/deep_enrichment.py`
- Test: `apps/agents/tests/test_deep_enrichment_api.py`

**验收标准：**

- API 使用统一 Agent Run envelope。
- 输出仅包含字段候选、证据、置信度、风险摘要。
- 不直接写 `customers`、`contact_methods` 或其他 core 表。
- run 状态写入 `agent_service_runs`。
- 失败时记录错误类型和错误消息。

**非目标：**

- 不接入 `apps/api` active_run。
- 不实现人工审核写入。
- 不自动采纳字段候选。

## Codex 提示词

```text
请执行 P4-E4-S1：实现 Deep Enrichment LangGraph HTTP API。
要求使用 TDD；只输出字段候选；不得写 core 业务表；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- Deep Enrichment 只输出候选，不自动写入客户主数据。
- 无证据候选不得进入可采纳结果。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。
