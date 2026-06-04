# 第二阶段小范围运行 Story 文件

来源：

- `docs/product/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行方案与产品技术设计.md`
- `_bmad-output/brainstorming/brainstorming-session-2026-06-02-第二阶段小范围运行-LLM来源发现Agent.md`
- `docs/superpowers/plans/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行Codex推进计划.md`

执行原则：

- 每次只执行一个 Story。
- 不做锁操作。
- 不做 git 操作。
- 必须使用计划中指定的 superpowers 技能。
- 每个 Story 完成后必须执行两轮独立评审。
- 必须执行必要的前后端真实联调，不允许只验证 seed 静态页面。

通用风控边界：

- 不自动社交私信。
- 不自动加好友。
- 不登录后批量采集。
- 不反爬规避。
- High/Forbidden 风险边界不得被自动化链路绕过。
- 所有 AI 输出必须保存来源证据和审计。

Story 清单：

- `P2-E1-S1` [创建 `llm_prompt_templates` 数据表、模型和 schema](P2-E1-S1-llm-prompt-templates-data-model.md)（Sprint 1，P0）
- `P2-E1-S2` [创建 `agent_task_runs` 数据表、模型和状态机 schema](P2-E1-S2-agent-task-runs-state-machine.md)（Sprint 1，P0）
- `P2-E1-S3` [创建 `lead_source_candidates` 数据表、模型和默认风险准入规则](P2-E1-S3-lead-source-candidates-data-model.md)（Sprint 1，P0）
- `P2-E1-S4` [模型导入、migration 验证和数据层契约测试](P2-E1-S4-phase2-data-foundation-contract.md)（Sprint 1，P0）
- `P2-E2-S1` [扩展 LLM 配置和 Provider 健康检查](P2-E2-S1-llm-settings-health-api.md)（Sprint 1，P0）
- `P2-E2-S2` [实现统一 `LLMClient` 和 mock 测试](P2-E2-S2-llm-client-mock-tests.md)（Sprint 1，P0）
- `P2-E2-S3` [实现技术失败 fallback，schema/合规失败不 fallback](P2-E2-S3-llm-fallback-rules.md)（Sprint 1，P0）
- `P2-E2-S4` [Source Discovery prompt/schema 入库与默认版本管理](P2-E2-S4-source-discovery-prompt-seed.md)（Sprint 1，P0）
- `P2-E2-S5` [Prompt template 查询 API 和后台治理接口基础](P2-E2-S5-prompt-template-query-api.md)（Sprint 1，P0）
- `P2-E3-S1` [实现 Source Discovery 输出 schema 校验服务](P2-E3-S1-source-discovery-schema-validation.md)（Sprint 2，P0）
- `P2-E3-S2` [实现来源候选 upsert、去重和默认审核状态服务](P2-E3-S2-lead-source-candidate-upsert.md)（Sprint 2，P0）
- `P2-E3-S3` [实现 Source Discovery Agent 核心运行服务](P2-E3-S3-source-discovery-agent-service.md)（Sprint 2，P0）
- `P2-E3-S4` [实现 Source Discovery 手动启动 API 和任务审计](P2-E3-S4-source-discovery-run-api.md)（Sprint 2，P0）
- `P2-E3-S5` [实现来源候选列表、详情、筛选 API](P2-E3-S5-lead-source-candidate-query-api.md)（Sprint 2，P0）
- `P2-E3-S6` [实现来源审核动作 API 与风险闸门](P2-E3-S6-lead-source-candidate-review-api.md)（Sprint 2，P0）
- `P2-E4-S1` [移动端来源候选 service 和 API adapter](P2-E4-S1-mobile-source-candidates-service.md)（Sprint 3，P1）
- `P2-E4-S2` [移动端来源候选队列页面](P2-E4-S2-mobile-source-candidates-page.md)（Sprint 3，P1）
- `P2-E4-S3` [移动端来源详情与审核动作页面](P2-E4-S3-mobile-source-detail-review-page.md)（Sprint 3，P1）
- `P2-E4-S4` [移动端 Agent 手动调用页面和任务状态展示](P2-E4-S4-mobile-agent-run-page.md)（Sprint 3，P1）
- `P2-E4-S5` [移动端前后端联调与 H5 可用性验证](P2-E4-S5-mobile-h5-integration-verification.md)（Sprint 3，P1）
- `P2-E5-S1` [APScheduler 开关、任务注册和 Redis lock](P2-E5-S1-agent-scheduler-redis-lock.md)（Sprint 4，P1）
- `P2-E5-S2` [失败重试、超时恢复和任务状态机收敛](P2-E5-S2-agent-retry-timeout-recovery.md)（Sprint 4，P1）
- `P2-E5-S3` [`LEAD_EXTRACTION` 从来源候选池消费 approved 来源](P2-E5-S3-lead-extraction-source-selection.md)（Sprint 4，P1）
- `P2-E5-S4` [抽取结果写入 staging/core/audit 并更新来源抽取状态](P2-E5-S4-lead-extraction-source-result-writeback.md)（Sprint 4，P1）
- `P2-E6-S1` [第二阶段 dashboard API](P2-E6-S1-phase2-dashboard-api.md)（Sprint 5，P2）
- `P2-E6-S2` [管理后台第二阶段运行看板](P2-E6-S2-admin-phase2-dashboard.md)（Sprint 5，P2）
- `P2-E6-S3` [管理后台 LLM/Prompt 治理页面](P2-E6-S3-admin-llm-prompt-governance.md)（Sprint 5，P2）
- `P2-E6-S4` [真实 PostgreSQL + Redis + LLM + 移动端 H5 端到端验收](P2-E6-S4-phase2-e2e-verification.md)（Sprint 5，P2）
- `P2-E6-S5` [部署与运行手册、最终验收结果归档](P2-E6-S5-phase2-deploy-runbook-final-archive.md)（Sprint 5，P2）
