# 第四阶段小范围运行 Story 文件

来源：

- `docs/brainstorm/brainstorming-session-2026-06-04-第四阶段小范围运行-LangGraph-Agent迁移.md`
- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`
- `docs/architecture/2026-06-03-LLM-Agent服务编排选型分析.md`
- `apps/agents/README.md`

执行原则：

- 每次只执行一个 Story，不要执行下一个 Story。
- 不做锁操作。
- 不做 git 操作。
- 代码实现 Story 必须使用 `superpowers:test-driven-development`。
- 调试异常必须使用 `superpowers:systematic-debugging`。
- 完成前必须使用 `superpowers:verification-before-completion`。
- 每个 Story 完成后必须执行两轮独立多维度评审，并记录结论、发现项和修正结果。
- 必须执行必要的前后端或服务间真实联调，不允许只验证 seed 静态页面。
- 所有过程、结果、注解和文档使用中文。

通用风控边界：

- `apps/api` 中现有 LLM Agent 保持不变，不在第四阶段直接替换生产入口。
- `apps/agents` 独立服务运行，`apps/api` 通过 HTTP API 调用，不做本地包注入。
- `apps/agents` 不直接写 `customers`、`lead_sources`、`contact_methods`、`staging_leads` 等业务 core 表。
- `apps/agents` 只写自己的 Agent 运行状态表，例如 `agent_service_runs`。
- 所有业务表写入、合规硬规则、人工确认、客户晋级、字段采纳、清洗执行仍由 `apps/api` 负责。
- 不自动社交私信。
- 不自动加好友。
- 不登录后批量采集。
- 不反爬规避。
- 不抓取非公开数据。
- 不自动晋级客户。
- 不自动归并客户。
- 不自动恢复 Invalid。
- 不自动触达客户。
- High/Forbidden、勿扰、C 级合规复核、证据校验等硬规则不得被 LangGraph 绕过。

## Epic 总览

| Epic ID | Epic | Story 数 | 目标 |
|---|---|---:|---|
| P4-E1 | Agent 独立服务基础 | 4 | 让 `apps/agents` 作为独立 FastAPI 服务运行，具备健康检查、鉴权、统一 envelope 和启动文档。 |
| P4-E2 | Agent 运行状态与重试基础 | 4 | 建立 `apps/agents` 自己的 Agent run 事实源、状态流转、错误分类、重试和节点 trace 摘要。 |
| P4-E3 | apps/api HTTP Agent Client | 6 | 让 `apps/api` 通过 HTTP 调用 `apps/agents`，保存兼容摘要，并可查询最终 Agent 结果。 |
| P4-E4 | Deep Enrichment / Lead Cleanup active 接入 | 5 | 让两个低风险候选输出类 Agent 通过 HTTP active_run 跑通。 |
| P4-E5 | Source Discovery LangGraph shadow | 4 | 实现 Source Discovery 的 LangGraph 平行版本并做 shadow 对照。 |
| P4-E6 | Lead Extraction/Grading LangGraph shadow | 5 | 实现抽取 + 分级组合图并做 shadow 对照。 |
| P4-E7 | 观测、失败案例与 Go/No-Go 报告 | 4 | 汇总第四阶段小范围运行指标、失败案例和下一阶段 Go/No-Go 决策。 |

## Story 清单

### P4-E1：Agent 独立服务基础

- `P4-E1-S1` [创建 `apps/agents` FastAPI 入口和 `/health`](P4-E1-S1-agents-fastapi-health.md)（Sprint 1，P0）
- `P4-E1-S2` [实现内部 API Key 鉴权](P4-E1-S2-agents-internal-api-key-auth.md)（Sprint 1，P0）
- `P4-E1-S3` [定义统一 Agent Run request / response envelope](P4-E1-S3-agent-run-envelope.md)（Sprint 1，P0）
- `P4-E1-S4` [补充本地启动文档和端口配置](P4-E1-S4-local-runbook-ports.md)（Sprint 1，P1）

### P4-E2：Agent 运行状态与重试基础

- `P4-E2-S1` [新增 `agent_service_runs` 模型与迁移](P4-E2-S1-agent-service-runs-model.md)（Sprint 2，P0）
- `P4-E2-S2` [实现 Agent run 创建、状态流转和失败记录](P4-E2-S2-agent-run-state-service.md)（Sprint 2，P0）
- `P4-E2-S3` [实现可重试错误分类和重试策略](P4-E2-S3-agent-retry-policy.md)（Sprint 2，P0）
- `P4-E2-S4` [将节点 trace 摘要写入 `audit_json.executed_nodes`](P4-E2-S4-agent-node-trace-summary.md)（Sprint 2，P1）

### P4-E3：apps/api HTTP Agent Client

- `P4-E3-S1` [新增 `AGENTS_BASE_URL`、`AGENTS_API_KEY`、`AGENTS_TIMEOUT_SECONDS` 配置](P4-E3-S1-api-agents-settings.md)（Sprint 3，P0）
- `P4-E3-S2` [实现 `HttpAgentRuntime` HTTP 调用客户端](P4-E3-S2-http-agent-runtime-client.md)（Sprint 3，P0）
- `P4-E3-S3` [兼容现有 runtime 方法：深挖和清洗](P4-E3-S3-runtime-method-compatibility.md)（Sprint 3，P0）
- `P4-E3-S4` [在 `agent_task_runs.output_summary_json` 保存 `external_agent_run_id`](P4-E3-S4-agent-task-run-compatible-summary.md)（Sprint 3，P0）
- `P4-E3-S5` [HTTP Agent client contract tests](P4-E3-S5-http-agent-client-contract-tests.md)（Sprint 3，P0）
- `P4-E3-S6` [实现 Agent run 查询结果消费](P4-E3-S6-agent-run-result-consumption.md)（Sprint 3，P1）

### P4-E4：Deep Enrichment / Lead Cleanup active 接入

- `P4-E4-S1` [实现 Deep Enrichment LangGraph HTTP API](P4-E4-S1-deep-enrichment-http-api.md)（Sprint 4，P0）
- `P4-E4-S2` [实现 Lead Cleanup LangGraph HTTP API](P4-E4-S2-lead-cleanup-http-api.md)（Sprint 4，P0）
- `P4-E4-S3` [`apps/api` 接入 Deep Enrichment HTTP active_run](P4-E4-S3-api-deep-enrichment-active-run.md)（Sprint 4，P0）
- `P4-E4-S4` [`apps/api` 接入 Lead Cleanup HTTP active_run](P4-E4-S4-api-lead-cleanup-active-run.md)（Sprint 4，P0）
- `P4-E4-S5` [字段候选和清洗建议人工审核链路联调](P4-E4-S5-active-agents-human-review-integration.md)（Sprint 4，P1）

### P4-E5：Source Discovery LangGraph shadow

- `P4-E5-S1` [实现 Source Discovery Graph](P4-E5-S1-source-discovery-graph.md)（Sprint 5，P0）
- `P4-E5-S2` [实现来源归一化、风险分级、去重、证据校验节点](P4-E5-S2-source-discovery-validation-nodes.md)（Sprint 5，P0）
- `P4-E5-S3` [实现 shadow 输出与现有来源发现结果对照](P4-E5-S3-source-discovery-shadow-comparison.md)（Sprint 5，P1）
- `P4-E5-S4` [输出 Source Discovery 30-50 条样本对照报告](P4-E5-S4-source-discovery-sample-report.md)（Sprint 5，P1）

### P4-E6：Lead Extraction/Grading LangGraph shadow

- `P4-E6-S1` [实现 Lead Extraction 子图](P4-E6-S1-lead-extraction-subgraph.md)（Sprint 6，P0）
- `P4-E6-S2` [实现 Lead Grading 子图](P4-E6-S2-lead-grading-subgraph.md)（Sprint 6，P0）
- `P4-E6-S3` [实现组合 API `/agent-runs/lead-extraction-grading`](P4-E6-S3-lead-extraction-grading-combined-api.md)（Sprint 6，P0）
- `P4-E6-S4` [实现 schema、证据、联系方式反编造和硬规则校验](P4-E6-S4-extraction-grading-hard-rules.md)（Sprint 6，P0）
- `P4-E6-S5` [输出 Lead Extraction/Grading 30-50 条样本对照报告](P4-E6-S5-extraction-grading-sample-report.md)（Sprint 6，P1）

### P4-E7：观测、失败案例与 Go/No-Go 报告

- `P4-E7-S1` [汇总 `agent_service_runs` 与 `apps/api` 兼容摘要](P4-E7-S1-agent-observability-summary.md)（Sprint 7，P1）
- `P4-E7-S2` [统计第四阶段样本指标](P4-E7-S2-phase4-sample-metrics.md)（Sprint 7，P1）
- `P4-E7-S3` [整理失败案例和不可重试错误](P4-E7-S3-failed-cases-non-retryable-errors.md)（Sprint 7，P1）
- `P4-E7-S4` [输出第四阶段 Go/No-Go 报告](P4-E7-S4-phase4-go-no-go-report.md)（Sprint 7，P1）

## 建议执行顺序

1. 先执行 P4-E1，建立 `apps/agents` 独立服务基础。
2. 再执行 P4-E2，让 `apps/agents` 拥有自己的 run 事实源和重试基础。
3. 再执行 P4-E3，让 `apps/api` 通过 HTTP 调用 `apps/agents`，同时保持现有表结构。
4. 再执行 P4-E4，完成 Deep Enrichment 和 Lead Cleanup 的 HTTP active_run。
5. 再执行 P4-E5 和 P4-E6，分别完成 Source Discovery 与 Lead Extraction/Grading 的 shadow 对照。
6. 最后执行 P4-E7，汇总指标、失败案例和下一阶段 Go/No-Go 决策。

## 本次拆分复核记录

### 第一轮独立复核：覆盖性检查

复核维度：

- README 中 Story 链接数量。
- `docs/stories/phase-4-small-run` 目录下实际 Story 文件数量。
- P4-E1 到 P4-E7 的 Epic 数量和每个 Epic 的 Story 数。
- 与产品技术设计文档第 12 节 BMAD Epic / Story 拆分是否一致。

结论：

- 通过。README 中共有 32 个 Story 链接，目录下共有 32 个 Story 文件。
- 通过。Epic 数量为 7 个，Story 分布为 4、4、6、5、4、5、4，与方案文档一致。
- 通过。已覆盖服务化基础、Agent run 事实源、HTTP client、低风险 active、核心链路 shadow、观测与 Go/No-Go。

发现项：

- 未发现新增实质阻塞问题。

修正结果：

- 无需修正。

### 第二轮独立复核：Story 质量与风控检查

复核维度：

- 每个 Story 是否包含状态、Sprint、优先级、Epic。
- 每个 Story 是否包含用户故事、上下文来源、目标、建议文件、验收标准、非目标。
- 每个 Story 是否包含 Codex 提示词、通用执行要求和通用风控边界。
- 是否明确保留 `apps/api` 现有 LLM Agent，不把 `apps/agents` 作为本地包注入。
- 是否明确 active_run 与 shadow_run 边界、人工审核边界、core 业务表写入边界。

结论：

- 通过。32 个 Story 均具备必要结构字段。
- 通过。P4-E3 明确 `apps/api` 通过 HTTP API 调用 `apps/agents`，不得 import `apps/agents`。
- 通过。P4-E4 仅允许 Deep Enrichment 和 Lead Cleanup active_run，且业务写入和人工审核仍由 `apps/api` 负责。
- 通过。P4-E5、P4-E6 明确 Source Discovery 与 Lead Extraction/Grading 仅 shadow_run，不写业务 core 表。
- 通过。P4-E7 明确第四阶段只输出评估和 Go/No-Go 建议，不自动删除 `apps/api` retry worker。

发现项：

- 未发现新增实质阻塞问题。

修正结果：

- 无需修正。
