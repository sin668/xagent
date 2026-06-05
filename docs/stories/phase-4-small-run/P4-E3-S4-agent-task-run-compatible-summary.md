# Story P4-E3-S4：在 agent_task_runs.output_summary_json 保存 external_agent_run_id

状态：待实现  
Sprint：Sprint 3  
优先级：P0  
Epic：P4-E3

## 用户故事

作为运营和排障人员，我希望 `apps/api.agent_task_runs` 能保存 `apps/agents` 返回的外部 run id，以便第四阶段在不改表结构的前提下追踪一次 HTTP Agent 调用。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`
- `docs/brainstorm/brainstorming-session-2026-06-04-第四阶段小范围运行-LangGraph-Agent迁移.md`

## Story 定义

**目标：** 在 `agent_task_runs.output_summary_json` 中保存 `external_agent_run_id`、`external_agent_status`、`agents_base_url` 等兼容摘要。

**建议文件：**

- Modify: `apps/api/app/services/`
- Modify: `apps/api/app/agents/`
- Test: `apps/api/tests/agents/test_agent_task_run_external_summary.py`

**验收标准：**

- 不修改 `agent_task_runs` 表结构。
- HTTP Agent 调用成功创建外部 run 后，`output_summary_json.external_agent_run_id` 可追踪。
- 失败时记录可排障摘要，但不吞掉原始错误语义。
- 摘要字段不包含 API Key 或敏感输入全文。

**非目标：**

- 不删除 `apps/api` retry worker。
- 不迁移历史 `agent_task_runs`。
- 不让 `apps/api` 成为 `apps/agents` 的运行状态事实源。

## Codex 提示词

```text
请执行 P4-E3-S4：在 agent_task_runs.output_summary_json 保存 external_agent_run_id。
要求使用 TDD；不得修改 agent_task_runs 表结构；不得记录 API Key；完成后执行两轮独立评审。
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
