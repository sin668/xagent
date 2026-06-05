# 第四阶段 Agent 观测摘要

生成方式：汇总 `apps/api.agent_task_runs.output_summary_json` 与 `apps/agents.agent_service_runs` 脱敏快照。

| API Task Run | External Run | 关联状态 | Agent | 模式 | API 状态 | Agent 状态 | 耗时(ms) | retry | 节点数 | 风险标记 |
|---|---|---|---|---|---|---|---:|---:|---:|---|
| 22222222-2222-2222-2222-222222222222 | 44444444-4444-4444-4444-444444444444 | linked | lead_extraction_grading | shadow | succeeded | succeeded | 900 | 0 | 3 |  |
| 33333333-3333-3333-3333-333333333333 | 55555555-5555-5555-5555-555555555555 | linked | source_discovery | shadow | retry_pending | failed | 2000 | 2 | 2 | forbidden_source |

## 节点 Trace 摘要

### 44444444-4444-4444-4444-444444444444

- lead_extraction.load_source_content
- lead_extraction.extract_candidate_fields
- lead_grading.apply_hard_rules

### 55555555-5555-5555-5555-555555555555

- load_channel_strategy
- validate_source_evidence
