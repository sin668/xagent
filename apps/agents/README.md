# Vehicle Leads Agents

第三阶段独立 Agent 项目，用于局部试点 LangGraph。

## 定位

- 仅承载新增的 Deep Enrichment Agent 和 Lead Cleanup Agent。
- 不迁移第二阶段已运行的 Source Discovery、Lead Extraction、APScheduler、Redis lock 和 `agent_task_runs` 主控链路。
- LangGraph 只负责新增 Agent 内部的多步骤流程表达、分支、状态流转和人工等待点。

## 数据与合规边界

- Agent 项目不得直接写 `customers`、`lead_sources`、`contact_methods` 等 core 表。
- Agent 项目只输出结构化候选结果，例如 `lead_enrichment_field_candidates` 和 `lead_cleanup_suggestions`。
- 所有结构化输出必须交由 `apps/api` Service 层执行 schema 校验、风险硬门禁、人工确认和 PostgreSQL 写入。
- 不自动社交私信。
- 不自动加好友。
- 不登录后批量采集。
- 不反爬规避。
- 不抓取非公开数据。
- 不自动晋级客户。
- 不自动归并客户。
- 不自动恢复 Invalid。
- 不自动触达客户。

## 本 Story 范围

当前只提供项目骨架和占位 graph 契约，不实现具体 LangGraph 流程。
