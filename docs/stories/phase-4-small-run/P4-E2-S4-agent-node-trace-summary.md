# Story P4-E2-S4：将节点 trace 摘要写入 audit_json.executed_nodes

状态：待实现  
Sprint：Sprint 2  
优先级：P1  
Epic：P4-E2

## 用户故事

作为运维和研发排障人员，我希望每次 LangGraph 运行都记录节点级摘要，以便定位失败节点、耗时和风险 flags。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 设计并实现 `audit_json.executed_nodes` 的稳定结构。

**建议文件：**

- Create/Modify: `apps/agents/app/schemas/trace.py`
- Modify: `apps/agents/app/services/agent_service_runs.py`
- Test: `apps/agents/tests/test_agent_node_trace_summary.py`

**验收标准：**

- 节点摘要包含 node、status、duration_ms、input_summary、output_summary、error。
- run 摘要包含 failed_node、risk_flags、source_urls、writes_core_tables。
- 失败 case 至少记录 failed_node、error_type、retryable。
- 第四阶段不强制新增 `agent_service_node_runs` 表。

**非目标：**

- 不实现外部 trace 平台。
- 不实现 LangSmith 集成。

## Codex 提示词

```text
请执行 P4-E2-S4：将节点 trace 摘要写入 audit_json.executed_nodes。
要求使用 TDD；保持结构稳定，便于后续迁移到 agent_service_node_runs；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- trace 不得包含 API Key 或敏感密钥。
- trace 不得记录非公开数据全文。

