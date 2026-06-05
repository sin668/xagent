# 第四阶段小范围运行 LangGraph Agent 迁移 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans` 按 Story 逐个实现本计划。代码实现 Story 必须使用 `superpowers:test-driven-development`；异常排查必须使用 `superpowers:systematic-debugging`；完成前必须使用 `superpowers:verification-before-completion`。Steps use checkbox (`- [ ]`) syntax for tracking.

创建日期：2026-06-05  
阶段：第四阶段小范围运行  
计划状态：待执行  
适用目录：`docs/stories/phase-4-small-run/`  
计划负责人：BMAD 输出边界，Superpowers 推进实施，Codex 按 Story 执行

**Goal:** 在不改变 `apps/api` 现有 LLM Agent 生产行为的前提下，将四类 LLM Agent 平行迁移到独立 `apps/agents` 服务，并用 LangGraph 重构执行编排、运行状态、重试和小样本对照验证。

**Architecture:** `apps/agents` 作为独立 FastAPI 服务运行在 `8010`，通过内部 API Key 接收 `apps/api` 的 HTTP 调用，并使用同一 PostgreSQL 实例中的专属运行表 `agent_service_runs` 作为 Agent 执行事实源。`apps/api` 保持业务入口、权限、人工审核、业务表写入和合规硬规则职责，只通过 HTTP client 调用 `apps/agents`，并在 `agent_task_runs.output_summary_json` 中保存兼容摘要。Deep Enrichment 与 Lead Cleanup 可受控 active_run；Source Discovery 与 Lead Extraction/Grading 只做 shadow_run 和对照报告。

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, SQLAlchemy 2, Alembic, PostgreSQL, Redis, APScheduler, Pydantic 2, LangGraph, DeepSeek/OpenAI-compatible LLM client, Vue 3/Vite admin, uni-app Vue mobile, Node v22.22.0.

---

## 0. 真相源和输入包

执行时按以下顺序读取。若发生冲突，先暂停并回写修正文档，不得直接扩大实现范围。

1. 当前用户确认的第四阶段决策。
2. 仓库 `AGENTS.md` / 本会话提供的开发阶段铁律。
3. `docs/brainstorm/brainstorming-session-2026-06-04-第四阶段小范围运行-LangGraph-Agent迁移.md`
4. `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`
5. `docs/stories/phase-4-small-run/README.md`
6. 当前要执行的 `docs/stories/phase-4-small-run/{Story 文件}`
7. `docs/architecture/2026-06-03-LLM-Agent服务编排选型分析.md`
8. `docs/AI协同开发执行标准.md`
9. 当前代码、测试和本地运行结果。

原型与界面约束：

- 第四阶段主要是服务化、Agent runtime、状态和对照验证，不新建大页面。
- 涉及人工审核体验时，必须复用第三阶段已形成的字段候选、清洗建议、客户工作台和审核链路。
- 如 Story 执行中出现新增页面、导航、角色入口或关键交互变更，必须先回到 `PRD -> UX -> 角色/页面矩阵 -> 关键原型确认 -> Epic/Story`，不得让 Codex 直接凭实现需要扩展 UI。

## 1. 冻结决策

本计划必须遵守以下已确认决策：

- `apps/api` 中现有 LLM Agent 保持不变，不在第四阶段直接替换生产入口。
- `apps/agents` 独立服务运行，`apps/api` 通过 HTTP API 调用，不做本地包注入。
- 本地小范围运行采用同机同环境、独立端口：`apps/api:8000`，`apps/agents:8010`。
- `apps/agents` 使用内部 API Key：`X-Agents-Api-Key`。
- `apps/agents` 是 LangGraph Agent 执行事实源。
- `apps/agents` 使用同一 PostgreSQL 实例中的专属运行表，不写 core 业务表。
- `apps/api.agent_task_runs` 第四阶段不改表结构，只在 `output_summary_json` 保存 `external_agent_run_id` 等兼容摘要。
- Agent 失败重试由 `apps/agents` 自己负责；`apps/api` 已有 `agent_task_runs`、retry worker 和 scheduler 只是临时保留。
- Deep Enrichment 和 Lead Cleanup 可进入受控 active_run。
- Source Discovery 和 Lead Extraction/Grading 只做 shadow_run。
- Lead Extraction/Grading 对外优先提供组合 API：`POST /agent-runs/lead-extraction-grading`，内部保留子图边界。

## 2. 强制标准、规范和流程

### 2.1 协同开发标准

- BMAD 负责边界、PRD、架构、Epic/Story 和验收口径。
- Superpowers 负责计划、TDD、系统化调试和完成前验证。
- Codex 负责单 Story 实现、测试、联调、修复和回写结果。
- 一次只执行一个 Story，不允许批量实现多个 Story。
- 稳定结论必须落盘到 Story、报告或实施产物中。
- 不允许静默扩需求。

### 2.2 Superpowers 使用规范

每个代码实现 Story 的最小技能链：

1. `superpowers:test-driven-development`
2. `superpowers:systematic-debugging`，仅在测试失败、联调异常、LLM/DB/HTTP 行为不符合预期时启用。
3. `superpowers:verification-before-completion`

执行整份计划时二选一：

- 推荐：`superpowers:subagent-driven-development`，每个 Story 独立上下文执行，主会话做验收和复核。
- 可选：`superpowers:executing-plans`，当前会话按计划逐 Story 推进。

### 2.3 两轮独立评审铁律

每个 Story 完成后必须执行两轮独立多维度评审，并记录到当前 Story 文件或 `_bmad-output/implementation-artifacts/phase-4/`。

第一轮建议维度：

- 需求覆盖：是否只实现当前 Story。
- 架构边界：是否保持 `apps/api` 与 `apps/agents` HTTP 服务边界。
- 数据边界：是否未写 core 业务表。
- 测试覆盖：单元、契约、集成或联调是否符合 Story。
- 安全合规：API Key、敏感输入、风险硬规则是否满足。

第二轮建议维度：

- 回归风险：是否影响现有 `apps/api` LLM Agent、retry worker、scheduler。
- 可观测性：run id、状态、错误、trace 摘要是否可追踪。
- 人工审核：active_run 输出是否仍由 `apps/api` 校验和人工确认。
- 可运维性：本地启动、端口、超时、失败重试是否清晰。
- 文档回写：Story 状态、执行记录、残留风险是否落盘。

只有连续两轮评审都没有新增实质阻塞问题，Story 才能标记完成。

### 2.4 测试与联调门禁

后端常用命令：

```bash
cd apps/api
python -m pytest
```

```bash
cd apps/agents
python -m pytest
```

前端常用命令：

```bash
cd apps/admin
npm test
npm run check:syntax
npm run build
```

```bash
cd apps/mobile
npm test
npm run check:syntax
npm run build:h5
```

服务间联调最低要求：

- `apps/api` 启动在 `8000`。
- `apps/agents` 启动在 `8010`。
- `apps/api` 通过 `AGENTS_BASE_URL` 和 `AGENTS_API_KEY` 调用 `apps/agents`。
- active_run Story 必须验证 `apps/api -> apps/agents -> apps/api 业务校验/审核` 的真实链路。
- shadow_run Story 必须验证 shadow 输出不写业务表，只进入对照摘要或报告。

## 3. 文件结构与职责边界

计划执行中优先使用以下现有结构；除非 Story 明确要求，不做大规模重构。

### 3.1 `apps/agents`

- `apps/agents/app/main.py`：FastAPI 入口、路由注册、健康检查。
- `apps/agents/app/api/agent_runs.py`：Agent Run HTTP API。
- `apps/agents/app/schemas/`：统一 envelope 和各 Agent 输入输出 schema。
- `apps/agents/app/graphs/`：LangGraph 图和子图。
- `apps/agents/app/runtime/`：run 创建、状态流转、重试、错误分类、trace 摘要。
- `apps/agents/app/models/`：`agent_service_runs` 等专属运行表模型。
- `apps/agents/app/db/`：数据库连接和 session。
- `apps/agents/app/tools/`：公开页面读取、证据校验、重复检测等可测试工具。
- `apps/agents/tests/`：单元测试、API 测试、契约测试和 graph 测试。

`apps/agents` 禁止职责：

- 不写 `customers`、`lead_sources`、`contact_methods`、`staging_leads`。
- 不自动触达、自动晋级、自动归并、自动恢复 Invalid。
- 不暴露公网服务。
- 不接收任意 URL 批量抓取请求绕过 `apps/api` 风险策略。

### 3.2 `apps/api`

- `apps/api/app/core/config.py` 或现有配置模块：`AGENTS_BASE_URL`、`AGENTS_API_KEY`、`AGENTS_TIMEOUT_SECONDS`。
- `apps/api/app/services/`：现有业务服务、人工审核、业务写入、合规硬规则。
- `apps/api/app/services/agent_task_runs.py`：兼容摘要保存。
- `apps/api/app/agents/http_runtime.py` 或同等位置：HTTP Agent runtime client。
- `apps/api/tests/`：配置、HTTP client、兼容摘要、服务间契约和 active_run 集成测试。

`apps/api` 禁止职责：

- 不 import `apps/agents`。
- 不接管 LangGraph 节点执行。
- 不主控 `apps/agents` 内部重试。
- 不直接修正 `apps/agents` 输出，只能校验、拒绝或进入既有业务流程。

### 3.3 前端与原型

- `apps/admin`：Vue 3/Vite 管理后台，第四阶段仅在观测看板或报告入口需要时小改。
- `apps/mobile`：uni-app Vue 移动端，第四阶段仅在人工审核联调需要时复用第三阶段页面。
- 第四阶段不新增大规模页面型需求；如必须新增，先冻结 UX 和原型。

## 4. API、状态与数据契约

### 4.1 `apps/agents` HTTP API

第四阶段目标接口：

```text
GET  /health
POST /agent-runs/deep-enrichment
POST /agent-runs/lead-cleanup
POST /agent-runs/source-discovery
POST /agent-runs/lead-extraction-grading
GET  /agent-runs/{agent_service_run_id}
```

统一请求 envelope：

```json
{
  "request_id": "uuid",
  "agent_task_run_id": "uuid-or-null",
  "trigger_source": "manual_api|shadow_run|scheduler|test",
  "agent_mode": "active|shadow|dry_run",
  "input": {},
  "options": {
    "max_retries": 2,
    "timeout_seconds": 120,
    "dry_run": false,
    "shadow_mode": false
  }
}
```

统一响应 envelope：

```json
{
  "schema_version": "phase4.agent.run.v1",
  "agent_service_run_id": "uuid",
  "request_id": "uuid",
  "status": "pending|running|retrying|succeeded|failed|blocked|cancelled",
  "agent_type": "deep_enrichment|lead_cleanup|source_discovery|lead_extraction_grading",
  "agent_mode": "active|shadow|dry_run",
  "output": {},
  "audit": {
    "writes_core_tables": false,
    "executed_nodes": [],
    "failed_node": null,
    "risk_flags": [],
    "source_urls": [],
    "llm_provider": "deepseek",
    "llm_model": "deepseek-chat"
  },
  "error": null
}
```

### 4.2 `agent_service_runs` 最小字段

`agent_service_runs` 必须至少覆盖：

- `id`
- `request_id`
- `agent_type`
- `agent_mode`
- `status`
- `trigger_source`
- `input_json`
- `output_json`
- `output_summary_json`
- `audit_json`
- `retry_count`
- `max_retries`
- `next_retry_at`
- `error_type`
- `error_message`
- `started_at`
- `finished_at`
- `created_at`
- `updated_at`

第四阶段先不强制创建 `agent_service_node_runs`，节点 trace 先写入 `audit_json.executed_nodes`。

### 4.3 错误分类

| error_type | 可重试 | 说明 |
|---|---:|---|
| `timeout_error` | 是 | HTTP 超时、LLM 超时 |
| `provider_rate_limited` | 是 | LLM 限流 |
| `transient_network_error` | 是 | 短暂网络失败 |
| `schema_validation_error` | 否 | 输出 schema 不合格 |
| `evidence_validation_error` | 否 | 证据缺失或联系方式反编造失败 |
| `risk_blocked` | 否 | High/Forbidden/勿扰/策略阻断 |
| `contract_mismatch` | 否 | `apps/api` 与 `apps/agents` contract 不一致 |

## 5. Story 执行顺序

严格按下列顺序推进：

```text
P4-E1-S1 -> P4-E1-S2 -> P4-E1-S3 -> P4-E1-S4
P4-E2-S1 -> P4-E2-S2 -> P4-E2-S3 -> P4-E2-S4
P4-E3-S1 -> P4-E3-S2 -> P4-E3-S3 -> P4-E3-S4 -> P4-E3-S5 -> P4-E3-S6
P4-E4-S1 -> P4-E4-S2 -> P4-E4-S3 -> P4-E4-S4 -> P4-E4-S5
P4-E5-S1 -> P4-E5-S2 -> P4-E5-S3 -> P4-E5-S4
P4-E6-S1 -> P4-E6-S2 -> P4-E6-S3 -> P4-E6-S4 -> P4-E6-S5
P4-E7-S1 -> P4-E7-S2 -> P4-E7-S3 -> P4-E7-S4
```

推进理由：

1. P4-E1 先建立服务入口、鉴权和统一 envelope。
2. P4-E2 再建立 `apps/agents` 自己的运行事实源和重试能力。
3. P4-E3 再让 `apps/api` 通过 HTTP 调用 `apps/agents`。
4. P4-E4 先接两个低风险 active_run Agent，验证人工审核闭环。
5. P4-E5/P4-E6 做核心链路 shadow，不污染现有业务表。
6. P4-E7 汇总观测、样本指标、失败案例和下一阶段 Go/No-Go。

## 6. Story 索引和 Codex 提示词

使用方式：

- 每次只复制一个 Story 的提示词给 Codex。
- Codex 执行前必须读取本计划、当前 Story 文件和真相源。
- Codex 完成后必须回写 Story 状态、验证命令、两轮评审结论和残留风险。

### 6.1 通用提示词模板

```text
请进入第四阶段小范围运行 LangGraph Agent 迁移实施。

必须先读取：
1. docs/superpowers/plans/2026-06-05-海外车辆采购AI获客系统-第四阶段小范围运行LangGraph-Agent迁移推进计划.md
2. docs/stories/phase-4-small-run/README.md
3. 当前 Story 文件：{STORY_PATH}
4. docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md
5. docs/brainstorm/brainstorming-session-2026-06-04-第四阶段小范围运行-LangGraph-Agent迁移.md

只执行当前 Story：{STORY_ID}。
使用 superpowers:test-driven-development 推进实现。
如果遇到失败或异常，使用 superpowers:systematic-debugging。
完成前使用 superpowers:verification-before-completion。

强制边界：
- apps/api 现有 LLM Agent 保持不变。
- apps/api 只能通过 HTTP API 调用 apps/agents，不得 import apps/agents。
- apps/agents 独立服务运行，默认端口 8010。
- apps/agents 不写 core 业务表，只写自己的 Agent 运行表。
- Deep Enrichment 和 Lead Cleanup 可 active_run，但业务写入和人工审核仍由 apps/api 负责。
- Source Discovery 和 Lead Extraction/Grading 只 shadow_run，不写 lead_source_candidates 或 staging_leads。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。

完成要求：
- 运行当前 Story 要求的测试和必要联调。
- 执行两轮独立多维度评审，并记录结论、发现项、修正结果。
- 回写当前 Story 的执行记录、验证命令和残留风险。
- 不做 git 操作，不做锁操作。
```

### 6.2 P4-E1：Agent 独立服务基础

- [ ] `P4-E1-S1`：创建 `apps/agents` FastAPI 入口和 `/health`  
  Story: `docs/stories/phase-4-small-run/P4-E1-S1-agents-fastapi-health.md`  
  Codex 替换：`{STORY_ID}=P4-E1-S1`，`{STORY_PATH}=docs/stories/phase-4-small-run/P4-E1-S1-agents-fastapi-health.md`

- [ ] `P4-E1-S2`：实现内部 API Key 鉴权  
  Story: `docs/stories/phase-4-small-run/P4-E1-S2-agents-internal-api-key-auth.md`  
  Codex 替换：`{STORY_ID}=P4-E1-S2`，`{STORY_PATH}=docs/stories/phase-4-small-run/P4-E1-S2-agents-internal-api-key-auth.md`

- [ ] `P4-E1-S3`：定义统一 Agent Run request / response envelope  
  Story: `docs/stories/phase-4-small-run/P4-E1-S3-agent-run-envelope.md`  
  Codex 替换：`{STORY_ID}=P4-E1-S3`，`{STORY_PATH}=docs/stories/phase-4-small-run/P4-E1-S3-agent-run-envelope.md`

- [ ] `P4-E1-S4`：补充本地启动文档和端口配置  
  Story: `docs/stories/phase-4-small-run/P4-E1-S4-local-runbook-ports.md`  
  Codex 替换：`{STORY_ID}=P4-E1-S4`，`{STORY_PATH}=docs/stories/phase-4-small-run/P4-E1-S4-local-runbook-ports.md`

### 6.3 P4-E2：Agent 运行状态与重试基础

- [ ] `P4-E2-S1`：新增 `agent_service_runs` 模型与迁移  
  Story: `docs/stories/phase-4-small-run/P4-E2-S1-agent-service-runs-model.md`

- [ ] `P4-E2-S2`：实现 Agent run 创建、状态流转和失败记录  
  Story: `docs/stories/phase-4-small-run/P4-E2-S2-agent-run-state-service.md`

- [ ] `P4-E2-S3`：实现可重试错误分类和重试策略  
  Story: `docs/stories/phase-4-small-run/P4-E2-S3-agent-retry-policy.md`

- [ ] `P4-E2-S4`：将节点 trace 摘要写入 `audit_json.executed_nodes`  
  Story: `docs/stories/phase-4-small-run/P4-E2-S4-agent-node-trace-summary.md`

### 6.4 P4-E3：apps/api HTTP Agent Client

- [ ] `P4-E3-S1`：新增 `AGENTS_BASE_URL`、`AGENTS_API_KEY`、`AGENTS_TIMEOUT_SECONDS` 配置  
  Story: `docs/stories/phase-4-small-run/P4-E3-S1-api-agents-settings.md`

- [ ] `P4-E3-S2`：实现 `HttpAgentRuntime` HTTP 调用客户端  
  Story: `docs/stories/phase-4-small-run/P4-E3-S2-http-agent-runtime-client.md`

- [ ] `P4-E3-S3`：兼容现有 runtime 方法：深挖和清洗  
  Story: `docs/stories/phase-4-small-run/P4-E3-S3-runtime-method-compatibility.md`

- [ ] `P4-E3-S4`：在 `agent_task_runs.output_summary_json` 保存 `external_agent_run_id`  
  Story: `docs/stories/phase-4-small-run/P4-E3-S4-agent-task-run-compatible-summary.md`

- [ ] `P4-E3-S5`：HTTP Agent client contract tests  
  Story: `docs/stories/phase-4-small-run/P4-E3-S5-http-agent-client-contract-tests.md`

- [ ] `P4-E3-S6`：实现 Agent run 查询结果消费  
  Story: `docs/stories/phase-4-small-run/P4-E3-S6-agent-run-result-consumption.md`

### 6.5 P4-E4：Deep Enrichment / Lead Cleanup active 接入

- [ ] `P4-E4-S1`：实现 Deep Enrichment LangGraph HTTP API  
  Story: `docs/stories/phase-4-small-run/P4-E4-S1-deep-enrichment-http-api.md`

- [ ] `P4-E4-S2`：实现 Lead Cleanup LangGraph HTTP API  
  Story: `docs/stories/phase-4-small-run/P4-E4-S2-lead-cleanup-http-api.md`

- [ ] `P4-E4-S3`：`apps/api` 接入 Deep Enrichment HTTP active_run  
  Story: `docs/stories/phase-4-small-run/P4-E4-S3-api-deep-enrichment-active-run.md`

- [ ] `P4-E4-S4`：`apps/api` 接入 Lead Cleanup HTTP active_run  
  Story: `docs/stories/phase-4-small-run/P4-E4-S4-api-lead-cleanup-active-run.md`

- [ ] `P4-E4-S5`：字段候选和清洗建议人工审核链路联调  
  Story: `docs/stories/phase-4-small-run/P4-E4-S5-active-agents-human-review-integration.md`

### 6.6 P4-E5：Source Discovery LangGraph shadow

- [ ] `P4-E5-S1`：实现 Source Discovery Graph  
  Story: `docs/stories/phase-4-small-run/P4-E5-S1-source-discovery-graph.md`

- [ ] `P4-E5-S2`：实现来源归一化、风险分级、去重、证据校验节点  
  Story: `docs/stories/phase-4-small-run/P4-E5-S2-source-discovery-validation-nodes.md`

- [ ] `P4-E5-S3`：实现 shadow 输出与现有来源发现结果对照  
  Story: `docs/stories/phase-4-small-run/P4-E5-S3-source-discovery-shadow-comparison.md`

- [ ] `P4-E5-S4`：输出 Source Discovery 30-50 条样本对照报告  
  Story: `docs/stories/phase-4-small-run/P4-E5-S4-source-discovery-sample-report.md`

### 6.7 P4-E6：Lead Extraction/Grading LangGraph shadow

- [ ] `P4-E6-S1`：实现 Lead Extraction 子图  
  Story: `docs/stories/phase-4-small-run/P4-E6-S1-lead-extraction-subgraph.md`

- [ ] `P4-E6-S2`：实现 Lead Grading 子图  
  Story: `docs/stories/phase-4-small-run/P4-E6-S2-lead-grading-subgraph.md`

- [ ] `P4-E6-S3`：实现组合 API `/agent-runs/lead-extraction-grading`  
  Story: `docs/stories/phase-4-small-run/P4-E6-S3-lead-extraction-grading-combined-api.md`

- [ ] `P4-E6-S4`：实现 schema、证据、联系方式反编造和硬规则校验  
  Story: `docs/stories/phase-4-small-run/P4-E6-S4-extraction-grading-hard-rules.md`

- [ ] `P4-E6-S5`：输出 Lead Extraction/Grading 30-50 条样本对照报告  
  Story: `docs/stories/phase-4-small-run/P4-E6-S5-extraction-grading-sample-report.md`

### 6.8 P4-E7：观测、失败案例与 Go/No-Go 报告

- [ ] `P4-E7-S1`：汇总 `agent_service_runs` 与 `apps/api` 兼容摘要  
  Story: `docs/stories/phase-4-small-run/P4-E7-S1-agent-observability-summary.md`

- [ ] `P4-E7-S2`：统计第四阶段样本指标  
  Story: `docs/stories/phase-4-small-run/P4-E7-S2-phase4-sample-metrics.md`

- [ ] `P4-E7-S3`：整理失败案例和不可重试错误  
  Story: `docs/stories/phase-4-small-run/P4-E7-S3-failed-cases-non-retryable-errors.md`

- [ ] `P4-E7-S4`：输出第四阶段 Go/No-Go 报告  
  Story: `docs/stories/phase-4-small-run/P4-E7-S4-phase4-go-no-go-report.md`

## 7. 每个 Story 的执行检查清单

复制提示词给 Codex 后，用下面清单验收：

- [ ] Codex 已声明使用对应 Superpowers 技能。
- [ ] Codex 已读取本计划、README、当前 Story、产品技术设计和头脑风暴记录。
- [ ] Codex 明确只执行当前 Story。
- [ ] Codex 先写失败测试，再实现，再跑通过测试。
- [ ] 涉及服务间调用时，已验证 `apps/api` 与 `apps/agents` 真实 HTTP 交互。
- [ ] 涉及 active_run 时，已验证输出仍进入 `apps/api` 校验、人工审核和业务写入流程。
- [ ] 涉及 shadow_run 时，已验证不写业务 core 表。
- [ ] 已运行当前 Story 要求的最小测试命令。
- [ ] 已执行两轮独立多维度评审。
- [ ] 已记录结论、发现项、修正结果和残留风险。
- [ ] Story 状态和执行记录已回写。

## 8. 阶段验收口径

第四阶段完成必须同时满足：

- `apps/agents` 可独立启动，默认端口 `8010`。
- `/health` 可用。
- Agent Run API 必须鉴权，无 API Key 返回 401。
- 统一 envelope 可被 OpenAPI 和 contract tests 固化。
- `agent_service_runs` 是 Agent 执行事实源。
- `apps/api` 不 import `apps/agents`。
- `apps/api.agent_task_runs` 表结构不变。
- `agent_task_runs.output_summary_json` 可追踪 `external_agent_run_id`。
- Deep Enrichment active_run 只输出字段候选，业务写入仍由 `apps/api` 完成。
- Lead Cleanup active_run 只输出清洗建议，不自动执行。
- Source Discovery shadow_run 不写 `lead_source_candidates`。
- Lead Extraction/Grading shadow_run 不写 `staging_leads`。
- High/Forbidden、勿扰、C 级合规复核、证据校验等硬规则未被绕过。
- 输出 Source Discovery 和 Lead Extraction/Grading 的 30-50 条样本对照报告。
- 输出第四阶段失败案例、样本指标和 Go/No-Go 报告。
- 明确下一阶段是否开始废弃 `apps/api` retry worker。

## 9. 风险与阻断条件

发现以下问题时必须暂停当前 Story，不能继续推进下一 Story：

- `apps/api` 通过本地包 import `apps/agents`。
- `apps/agents` 写入 core 业务表。
- Source Discovery shadow 输出污染 `lead_source_candidates`。
- Lead Extraction/Grading shadow 输出写入 `staging_leads`。
- active_run 绕过 `apps/api` schema 校验、合规硬规则或人工审核。
- API Key、LLM 输入输出、客户联系方式等敏感数据被写入不该公开的日志或报告。
- 两轮评审中第二轮仍发现新增实质阻塞问题。
- 测试或联调失败但 Story 被标记完成。

## 10. 第一条 Codex 提示词

下一步从 `P4-E1-S1` 开始。建议提交给 Codex 的完整提示词：

```text
请进入第四阶段小范围运行 LangGraph Agent 迁移实施。

必须先读取：
1. docs/superpowers/plans/2026-06-05-海外车辆采购AI获客系统-第四阶段小范围运行LangGraph-Agent迁移推进计划.md
2. docs/stories/phase-4-small-run/README.md
3. 当前 Story 文件：docs/stories/phase-4-small-run/P4-E1-S1-agents-fastapi-health.md
4. docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md
5. docs/brainstorm/brainstorming-session-2026-06-04-第四阶段小范围运行-LangGraph-Agent迁移.md

只执行当前 Story：P4-E1-S1。
使用 superpowers:test-driven-development 推进实现。
如果遇到失败或异常，使用 superpowers:systematic-debugging。
完成前使用 superpowers:verification-before-completion。

强制边界：
- apps/api 现有 LLM Agent 保持不变。
- apps/api 只能通过 HTTP API 调用 apps/agents，不得 import apps/agents。
- apps/agents 独立服务运行，默认端口 8010。
- apps/agents 不写 core 业务表，只写自己的 Agent 运行表。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。

完成要求：
- 先写 apps/agents /health 的失败测试。
- 实现最小 FastAPI 入口和 /health。
- 验证 uvicorn app.main:app --host 0.0.0.0 --port 8010 可启动。
- 验证 GET /health 返回服务状态、服务名和版本。
- 验证 /docs 可访问并展示 OpenAPI。
- 不影响 apps/api 现有启动。
- 执行两轮独立多维度评审，并记录结论、发现项、修正结果。
- 回写当前 Story 的执行记录、验证命令和残留风险。
- 不做 git 操作，不做锁操作。
```

## 11. 自检记录

### 第一轮复核：需求覆盖与计划完整性

结论：

- 通过。本计划覆盖头脑风暴、产品技术设计和 `docs/stories/phase-4-small-run` 中的 7 个 Epic、32 个 Story。
- 通过。本计划明确保留 `apps/api` 现有 LLM Agent，`apps/agents` 独立服务运行，双方通过 HTTP API 交互。
- 通过。本计划明确 Deep Enrichment / Lead Cleanup active_run 与 Source Discovery / Lead Extraction/Grading shadow_run 的边界。

发现项：

- 未发现新增实质阻塞问题。

修正结果：

- 无需修正。

### 第二轮复核：标准规范、技术栈与推进流程

结论：

- 通过。本计划对齐 `docs/AI协同开发执行标准.md` 的 BMAD、Codex、Superpowers 分工。
- 通过。本计划对齐当前技术栈：FastAPI、SQLAlchemy、Alembic、PostgreSQL、Redis、APScheduler、LangGraph、Pydantic、Vue/Vite、uni-app。
- 通过。本计划明确每个 Story 必须使用 Superpowers 技能推进、执行 TDD、完成前验证和两轮独立评审。
- 通过。本计划未要求新增未冻结页面，涉及人工审核时要求复用现有原型和第三阶段审核链路。

发现项：

- 未发现新增实质阻塞问题。

修正结果：

- 无需修正。
