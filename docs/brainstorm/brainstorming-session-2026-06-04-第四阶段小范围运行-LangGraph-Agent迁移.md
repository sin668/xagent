---
stepsCompleted: [1]
inputDocuments:
  - docs/brainstorm/brainstorming-session-2026-06-02-第二阶段小范围运行-LLM来源发现Agent.md
  - docs/brainstorm/brainstorming-session-2026-06-04-第三阶段小范围运行-客户管理工作台.md
  - apps/agents/README.md
session_topic: "第四阶段小范围运行 - apps/api LLM Agent 保持不变，apps/agents 使用 LangGraph 平行重构"
session_goals: "围绕局部迁移边界、LangGraph 架构、灰度运行、兼容调用、审计观测、合规风控和 BMAD Story 拆分进行头脑风暴"
selected_approach: "BMAD 渐进式头脑风暴"
techniques_used:
  - 渐进式发散与收敛
  - 边界优先
  - 风险反推
ideas_generated: []
context_file: ""
---

# 第四阶段小范围运行 - LangGraph Agent 迁移头脑风暴记录

创建时间：2026-06-04 CST

## Session Overview

**主题：** 进行局部小范围重构，`apps/api` 中现有 LLM Agent 保持不变；同时把这些 LLM Agent 平行迁移到 `apps/agents`，使用 LangGraph 进行重构。

**目标：**

1. 明确第四阶段迁移的 Agent 范围和不迁移范围。
2. 明确 `apps/api` 与 `apps/agents` 的职责边界，避免破坏现有运行链路。
3. 设计 LangGraph 版本 Agent 的图结构、状态、节点、工具、错误分支和人工等待点。
4. 明确小范围运行方式：影子运行、灰度开关、回滚、对照验证。
5. 明确审计、观测、成本、失败案例和合规风控要求。
6. 形成后续 BMAD Epic / Story 拆分依据。

## 已继承的核心边界

- `apps/api` 中现有 LLM Agent 保持不变，不在第四阶段直接替换生产入口。
- `apps/agents` 作为平行的 LangGraph Agent 项目，先用于局部重构、小范围运行和对照验证。
- Agent 不直接写 `customers`、`lead_sources`、`contact_methods` 等 core 表。
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
- High/Forbidden、勿扰、C 级合规复核、证据校验等硬规则不得被 LangGraph 绕过。

## 当前上下文判断

第三阶段 `apps/agents` 已有 LangGraph 雏形：

- `DeepEnrichmentGraphRunner`
- `LeadCleanupGraphRunner`
- `ApiContractBoundary`
- `MockAgentRuntime`
- `public_search`、`evidence_validator`、`duplicate_detector` 等工具占位

但当前 `apps/agents/README.md` 明确第三阶段只承载 Deep Enrichment 和 Lead Cleanup，不迁移 Source Discovery、Lead Extraction、APScheduler、Redis lock 和 `agent_task_runs` 主控链路。

第四阶段的关键不是“一次性重写全部 Agent”，而是决定哪些 Agent 进入局部平行 LangGraph 重构，并建立可灰度、可对照、可回滚的运行方式。

## 维度 1：迁移范围与阶段边界

### 初步专业建议

第四阶段建议采用 **“先平行迁移编排复杂、风险可控的 Agent，再考虑核心生产链路 Agent”**：

1. 第一批：`Deep Enrichment Agent`、`Lead Cleanup Agent`
   - 已有 `apps/agents` 雏形。
   - 输出仍然是候选补全字段和清洗建议，不直接写 core 表。
   - 适合先验证 LangGraph 的状态流、分支、人工等待点和工具封装。

2. 第二批：`Source Discovery Agent`
   - 属于第二阶段核心增长链路，但可做影子运行。
   - LangGraph 版本可以只输出 `lead_source_candidates` 候选，不替换现有 `apps/api` 版本。
   - 适合验证公开搜索、来源归一化、风险分级、去重、失败重试。

3. 第三批：`Lead Extraction / Lead Grading`
   - 影响 `staging_leads`、触达队列和客户晋级前置质量。
   - 不建议第四阶段一开始替换，只建议做离线/影子对照。

不建议第四阶段迁移 APScheduler、Redis lock 和 `agent_task_runs` 主控链路到 `apps/agents`。这些仍应由 `apps/api` 保持主控，`apps/agents` 只作为可调用的 Agent runtime。

### 待确认问题 1

第四阶段第一批迁移范围建议选择哪一种？

A. **保守范围**：只把 Deep Enrichment 和 Lead Cleanup 做成真正 LangGraph 图，完成局部运行闭环。

B. **平衡范围**：Deep Enrichment + Lead Cleanup + Source Discovery 影子运行；不迁移 Lead Extraction/Grading。

C. **激进范围**：Deep Enrichment + Lead Cleanup + Source Discovery + Lead Extraction/Grading 全部做 LangGraph 平行版本。

**我的建议：选择 B。**

理由：

- 只做 A 太保守，第四阶段看不到“第二阶段 LLM Agent 迁移”的价值。
- 直接做 C 风险过高，Lead Extraction/Grading 是进入 `staging_leads` 的关键链路，一旦对齐不好会污染后续工作台和触达流程。
- B 能覆盖两个第三阶段新增 Agent，同时把 Source Discovery 纳入影子运行，验证 LangGraph 对“搜索、去重、风险分级、候选入池”的编排价值。

### 已确认决定 1

选择 **C：Deep Enrichment + Lead Cleanup + Source Discovery + Lead Extraction/Grading 全部做 LangGraph 平行版本**。

补充边界：

- 这是“平行迁移/局部小范围重构”，不是立即替换 `apps/api` 中现有 LLM Agent。
- `apps/api` 中现有 LLM Agent、Service、API、调度、Redis lock、审计和 DB 写入保持不变。
- LangGraph 版本优先用于小样本、影子运行、对照验证和后续灰度切换准备。
- `Lead Extraction/Grading` 虽然纳入第四阶段迁移范围，但默认不直接接管生产写入链路，必须先完成 contract、对照评估、证据一致性和人工验收。

专业判断：

- 选择 C 会提高第四阶段价值，也能把 `apps/agents` 从第三阶段新增 Agent 试点推进为统一 Agent 编排层。
- 主要风险是范围膨胀，所以后续 Story 拆分必须明确“平行图实现”和“生产入口切换”是两件事。
- 建议验收口径改为：第四阶段完成全量 LLM Agent 的 LangGraph 平行版本和小范围验证，但不强制完成生产切换。

## 维度 2：apps/api 与 apps/agents 职责边界

### 初步专业建议

建议第四阶段采用 **“apps/api 负责控制面与数据面，apps/agents 负责 Agent 编排面”**：

- `apps/api`
  - 保持所有现有 API、Service、DB 写入、审计、调度、Redis lock 和权限入口不变。
  - 负责调用 `apps/agents` runtime。
  - 负责最终 schema 校验、硬规则、事务写入、审计和人工状态流转。

- `apps/agents`
  - 负责 LangGraph 图执行。
  - 负责节点编排、状态流转、工具调用、LLM 输出结构化、错误分支和人工等待点表达。
  - 不直接连接生产数据库，不直接写 core 表。
  - 输出 contract JSON，由 `apps/api` 接收和落库。

### 待确认问题 2

`apps/api` 调用 `apps/agents` 的方式，第四阶段建议选择哪一种？

A. **进程内 Python 包调用**：`apps/api` 通过本地包导入 `apps/agents` runtime。

B. **独立 HTTP 服务调用**：`apps/agents` 起独立 FastAPI 服务，`apps/api` 通过 HTTP 调用。

C. **队列/任务调用**：`apps/api` 写任务，`apps/agents` worker 消费队列。

**我的建议：先选 A，预留 B/C。**

理由：

- 小范围运行阶段，A 最简单，部署复杂度最低，也方便复用现有测试和事务边界。
- B 更接近未来独立 Agent 服务，但会引入认证、网络、部署、健康检查、版本兼容等额外复杂度。
- C 适合规模化异步运行，但第四阶段如果过早引入队列，会把问题从 Agent 重构扩展成基础设施重构。

建议验收标准写成：第四阶段必须把 Agent runtime 接口抽象出来，允许未来从本地调用切换到 HTTP/队列，但当前实现优先本地调用。

### 已确认决定 2

调整为 **B：`apps/agents` 作为独立 Agent 服务运行，`apps/api` 通过 API 接口调用 `apps/agents`**。

此前曾建议“进程内 Python 包调用优先，预留 HTTP/队列演进”。经确认，第四阶段目标应改为服务化集成：`apps/api` 不把 `apps/agents` 作为本地包注入，而是通过 HTTP API 与独立运行的 Agent 服务交互。

当前代码核查结果：

- `apps/api` 目前没有直接 import `apps/agents`。
- `LeadEnrichmentService.run_deep_enrichment_agent(...)` 接收外部传入的 `runtime` 参数，然后调用 `runtime.run_deep_enrichment(...)`。
- `LeadCleanupSuggestionService.run_cleanup_agent(...)` 接收外部传入的 `runtime` 参数，然后调用 `runtime.run_lead_cleanup(...)`。
- `apps/api` 测试中使用 fake runtime 验证 service contract。
- `apps/agents` 中存在 `MockAgentRuntime`，提供 `run_deep_enrichment(...)` 和 `run_lead_cleanup(...)`，但当前 API 路由层没有直接实例化或注入它。
- `apps/api/app/api/lead_enrichment.py` 当前只创建 enrichment pending run、查询结果和审核字段候选；没有直接触发 `run_deep_enrichment_agent(...)`。
- `apps/api/app/api/lead_cleanup.py` 当前只提供清洗建议查询、审核、执行；没有直接触发 `run_cleanup_agent(...)`。

当前代码事实仍然是：

```text
apps/api service 定义 runtime 调用协议
  -> 测试或上层调用者注入 runtime
  -> apps/agents 提供 MockAgentRuntime/GraphRunner
  -> apps/api service 负责校验输出、写库、审计和状态流转
```

第四阶段目标架构调整为：

```text
apps/api
  -> AgentRuntimeClient / HttpAgentRuntime
  -> POST apps/agents Agent API
  -> apps/agents 独立运行 LangGraph
  -> 返回结构化 Agent 输出 JSON
  -> apps/api 执行 schema 校验、风险硬门禁、审计、DB 写入和人工状态流转
```

专业建议：

- `apps/api` 仍然不要直接 import 具体 graph runner，应依赖 HTTP client / runtime protocol。
- `apps/agents` 应新增独立 FastAPI 服务入口，例如 `/health`、`/agent-runs/deep-enrichment`、`/agent-runs/lead-cleanup`、`/agent-runs/source-discovery`、`/agent-runs/lead-extraction-grading`。
- `apps/api` 应新增 `HttpAgentRuntime` 或 `AgentRuntimeClient`，实现现有 service 所需的 `run_deep_enrichment(...)`、`run_lead_cleanup(...)` 等方法，内部通过 HTTP 调用 `apps/agents`。
- 需要新增配置项，例如 `AGENTS_BASE_URL`、`AGENTS_API_KEY`、`AGENTS_TIMEOUT_SECONDS`、`AGENT_LANGGRAPH_SHADOW_ENABLED`。
- HTTP 调用必须有超时、错误归一化、重试策略、请求/响应 schema 校验、trace_id / agent_task_run_id 透传。
- `apps/api` 仍作为生产控制面和数据面：所有 DB 写入、审计、合规硬规则、人工确认、调度、Redis lock 不迁移到 `apps/agents`。
- `apps/agents` 作为编排面：运行 LangGraph、工具调用、LLM 结构化输出、节点状态和错误分支，不直接写 `customers`、`lead_sources`、`contact_methods` 等 core 表。
- 由于 `apps/api` 和 `apps/agents` 都使用包名 `app`，服务化调用可以天然规避本地包导入冲突；后续若仍要做共享 schema，应通过独立 contract 包或 OpenAPI/schema 文件，而不是互相 import。

### 待讨论问题 3

`apps/agents` 独立服务的部署形态建议选择哪一种？

A. 与 `apps/api` 同机同环境运行，独立端口，例如 `apps/api:8000`、`apps/agents:8010`。

B. 独立容器运行，通过 Docker Compose / 内网服务名通信。

C. 独立进程 + 队列 worker，同时提供 HTTP 控制 API。

**我的建议：第四阶段先选 A 或 B，不选 C。**

理由：

- A 最适合本地小范围运行，启动和调试简单。
- B 更接近生产部署，能清楚表达服务边界和健康检查。
- C 会把本阶段扩展成队列基础设施重构，容易分散 LangGraph 迁移重点。

建议如果当前第四阶段仍以本地小范围运行为主，先采用 **A：同机独立端口**；如果已经准备进入容器化部署，则采用 **B：独立容器**。

### 已确认决定 3

选择 **A：`apps/api` 与 `apps/agents` 同机同环境运行，使用独立端口**。

建议默认端口：

- `apps/api`: `8000`
- `apps/agents`: `8010`

建议本地运行方式：

```text
apps/api
  uvicorn app.main:app --host 0.0.0.0 --port 8000

apps/agents
  uvicorn app.main:app --host 0.0.0.0 --port 8010
```

专业建议：

- 第四阶段先不要引入 Docker Compose、队列 worker 或独立容器编排，避免把范围从 Agent 重构扩大到部署平台重构。
- `apps/api` 通过 `AGENTS_BASE_URL=http://127.0.0.1:8010` 调用 `apps/agents`。
- `apps/agents` 必须提供 `/health`，`apps/api` 应在启动前或调用前做健康检查。
- 所有 Agent API 响应必须是结构化 JSON，并包含 `schema_version`、`agent_run_id` 或对应 run id、`audit`、`executed_nodes` / trace 信息。
- 同机独立端口仍应视为服务边界，不能因为在同机就共享数据库 session 或直接 import 内部模块。

## 维度 3：HTTP 契约与 Agent API 设计

### 初步专业建议

第四阶段建议为 `apps/agents` 定义一组明确的 Agent Run API，而不是只做一个泛化 `/run`：

```text
GET  /health
POST /agent-runs/deep-enrichment
POST /agent-runs/lead-cleanup
POST /agent-runs/source-discovery
POST /agent-runs/lead-extraction-grading
```

原因：

- 每类 Agent 的输入、输出、风险边界和验收标准不同。
- 独立 endpoint 更容易做 schema、测试、日志、限流和权限控制。
- 泛化 `/run` 容易把 contract 做松，后续定位问题困难。

但 endpoint 内部可以复用统一 envelope：

```json
{
  "request_id": "uuid",
  "agent_task_run_id": "uuid",
  "trigger_source": "manual_api|shadow_run|scheduler",
  "input": {},
  "options": {
    "shadow_mode": true,
    "dry_run": true
  }
}
```

输出统一包含：

```json
{
  "schema_version": "...",
  "status": "succeeded|failed|blocked",
  "output": {},
  "audit": {
    "writes_core_tables": false,
    "executed_nodes": [],
    "source_urls": [],
    "risk_flags": [],
    "llm_provider": "...",
    "llm_model": "..."
  },
  "error": null
}
```

### 待讨论问题 4

`Lead Extraction` 和 `Lead Grading` 在 LangGraph 中应该拆成两个 Agent API，还是合并成一个 Agent API？

A. 拆成两个：`/agent-runs/lead-extraction` 与 `/agent-runs/lead-grading`。

B. 合并为一个：`/agent-runs/lead-extraction-grading`，图中先抽取再分级。

C. 两者都支持：内部拆图，外部提供组合 API。

**我的建议：选择 C，但第四阶段优先实现组合 API。**

理由：

- 业务上抽取和分级通常连续发生，小范围运行时组合 API 更方便做端到端对照。
- 工程上仍应保留内部子图或节点边界，便于单独测试抽取质量和分级质量。
- 后续如果需要只重跑分级，不应被迫重新抽取公开页面。

### 已确认决定 4

选择 **C：内部拆图，外部提供组合 API；第四阶段优先实现组合 API**。

具体口径：

- `apps/agents` 对外优先提供 `POST /agent-runs/lead-extraction-grading`。
- LangGraph 内部保留 extraction 子图/节点和 grading 子图/节点边界。
- 后续可以追加独立 endpoint：
  - `POST /agent-runs/lead-extraction`
  - `POST /agent-runs/lead-grading`
- 小范围运行时，组合 API 用于端到端对照现有 `apps/api` 的抽取 + 分级链路。
- 单独重跑分级、只更新分级建议、只做分级回归测试时，可以复用内部 grading 子图。

专业判断：

- 组合 API 可以降低第四阶段联调复杂度。
- 内部拆图可以避免后续演进被单一大图锁死。
- 对照评估时必须分别记录抽取质量和分级质量，不能只看最终等级是否一致。

## 维度 4：影子运行与切换策略

### 初步专业建议

选择 C 的迁移范围后，第四阶段必须明确“LangGraph 平行版本不默认接管生产写入”。

建议运行模式分三档：

1. **dry_run**
   - `apps/api` 传入样本输入。
   - `apps/agents` 运行 LangGraph。
   - 只返回结果，不写任何业务表。

2. **shadow_run**
   - `apps/api` 同时保留现有 Agent 结果。
   - 调用 `apps/agents` 得到 LangGraph 结果。
   - 写入对照审计或 `agent_task_runs.output_summary_json`，不影响原有业务流转。

3. **active_run**
   - 仍由 `apps/api` 调用 `apps/agents`。
   - `apps/api` 使用 LangGraph 输出进入原有 schema 校验和写库流程。
   - 只有在连续对照通过后才允许逐 Agent 开启。

### 待讨论问题 5

第四阶段是否允许任何 LangGraph Agent 进入 `active_run`？

A. 不允许，全部只做 dry_run / shadow_run。

B. 只允许 Deep Enrichment 和 Lead Cleanup active_run；Source Discovery、Lead Extraction/Grading 只做 shadow_run。

C. 全部允许 active_run，但默认关闭，由配置逐个打开。

**我的建议：选择 B。**

理由：

- Deep Enrichment 和 Lead Cleanup 当前本来就输出候选字段/建议，不直接写 core 表，active 风险较低。
- Source Discovery 会影响候选来源池，Lead Extraction/Grading 会影响 `staging_leads`，建议先 shadow 对照。
- B 能体现第四阶段真实运行价值，同时控制核心链路污染风险。

### 已确认决定 5

选择 **B：只允许 Deep Enrichment 和 Lead Cleanup 进入 active_run；Source Discovery、Lead Extraction/Grading 第四阶段先做 shadow_run**。

运行策略：

| Agent | 第四阶段默认模式 | 是否可 active_run | 说明 |
|---|---|---:|---|
| Deep Enrichment | `active_run` 可开启 | 是 | 输出字段候选，仍由 `apps/api` 写入和人工审核 |
| Lead Cleanup | `active_run` 可开启 | 是 | 输出清洗建议，仍由 `apps/api` 写入和人工审核/执行 |
| Source Discovery | `shadow_run` | 否 | 不直接污染来源候选池，先与现有结果做对照 |
| Lead Extraction/Grading | `shadow_run` | 否 | 不直接写 `staging_leads`，先做抽取质量和分级质量对照 |

建议配置：

```text
AGENT_LANGGRAPH_DEEP_ENRICHMENT_MODE=active
AGENT_LANGGRAPH_LEAD_CLEANUP_MODE=active
AGENT_LANGGRAPH_SOURCE_DISCOVERY_MODE=shadow
AGENT_LANGGRAPH_LEAD_EXTRACTION_GRADING_MODE=shadow
```

专业判断：

- 该策略允许第四阶段真实验证 LangGraph 服务化调用，不停留在纯 mock。
- 同时避免一开始就让 LangGraph 结果影响来源池和 staging 线索质量。
- 后续是否把 Source Discovery 或 Lead Extraction/Grading 切到 active，必须依赖对照指标和人工 go/no-go。

## 维度 5：LangGraph 图结构与节点边界

### 初步专业建议

第四阶段不应只把现有函数搬进 `apps/agents`，而要利用 LangGraph 表达以下能力：

- 节点级可观测：每个节点有输入摘要、输出摘要、耗时、失败原因。
- 条件分支：风险阻断、缺证据、LLM 输出不合规、需要人工审核。
- 状态可恢复：失败后可知道停在哪个节点，后续可重试。
- 人工等待点：字段候选、清洗建议、来源审核、分级异常都能停在人工复核。
- 工具边界：公开搜索、页面读取、证据校验、去重、LLM 结构化输出都作为 tool/node。

建议四类图的第一版节点如下：

### Deep Enrichment Graph

```text
load_lead
  -> validate_trigger_boundary
  -> build_search_keywords
  -> search_public_sources
  -> read_public_pages
  -> extract_field_candidates
  -> validate_evidence
  -> score_confidence
  -> output_field_candidates
  -> wait_human_review
```

### Lead Cleanup Graph

```text
load_cleanup_scope
  -> detect_duplicates
  -> classify_invalid_reason
  -> find_restore_candidates
  -> validate_no_auto_execution
  -> output_cleanup_suggestions
  -> wait_human_review
```

### Source Discovery Graph

```text
load_channel_strategy
  -> build_discovery_queries
  -> search_public_sources
  -> normalize_source_candidates
  -> classify_channel_risk
  -> dedupe_candidates
  -> validate_source_evidence
  -> output_shadow_candidates
```

### Lead Extraction / Grading Graph

```text
load_source_candidate
  -> validate_source_allowed_for_shadow
  -> read_public_page
  -> extract_lead_json
  -> validate_extraction_schema
  -> validate_evidence_and_contacts
  -> grade_lead
  -> apply_hard_rules
  -> output_shadow_staging_lead
  -> compare_with_api_result
```

### 待讨论问题 6

第四阶段 LangGraph 节点日志要记录到哪里？

A. 只记录在 `apps/agents` 响应的 `audit.executed_nodes` 中，由 `apps/api` 存入 `agent_task_runs.output_summary_json`。

B. `apps/agents` 自己落本地日志文件或内存日志，`apps/api` 只保存最终摘要。

C. `apps/api` 新增/复用表保存节点级 trace，例如扩展 `agent_task_runs.output_summary_json` 或后续新增 `agent_node_runs`。

**我的建议：第四阶段选 A，预留 C。**

理由：

- A 不需要新增迁移，适合第四阶段局部小范围运行。
- 节点数量、耗时、失败节点、风险 flags 可以先放在 `agent_task_runs.output_summary_json`。
- C 更完整，但会增加数据模型和迁移范围；等 LangGraph 稳定后再考虑 `agent_node_runs`。

### 已确认决定 6

选择 **A：LangGraph 节点日志先放在 `apps/agents` 响应的 `audit.executed_nodes` / trace 摘要中，由 `apps/api` 存入 `agent_task_runs.output_summary_json`**，预留后续新增节点级 trace 表。

第四阶段节点审计最小字段建议：

```json
{
  "executed_nodes": [
    {
      "node": "read_public_page",
      "status": "succeeded",
      "duration_ms": 123,
      "input_summary": "...",
      "output_summary": "...",
      "error": null
    }
  ],
  "failed_node": null,
  "risk_flags": [],
  "source_urls": [],
  "writes_core_tables": false
}
```

专业判断：

- 第四阶段先不新增 `agent_node_runs`，避免把迁移范围扩大到新数据模型。
- 但 `audit.executed_nodes` 结构必须稳定，否则后续无法平滑迁移到节点级表。
- 对失败 case，至少必须记录 `failed_node`、`error_type`、`retryable`、`input_ref`。

## 维度 6：对照指标与 Go/No-Go

### 初步专业建议

既然 Source Discovery 和 Lead Extraction/Grading 先 shadow，就必须定义对照指标，否则 shadow 只是在“跑一遍”。

建议第四阶段最小指标：

| Agent | 关键对照指标 | Go/No-Go 建议 |
|---|---|---|
| Source Discovery | URL 有效率、重复率、风险分级一致率、证据完整率 | 连续小样本 50 条中，证据完整率 >= 90%，Forbidden 误放行为为 0 |
| Lead Extraction | schema 通过率、证据命中率、联系方式反编造通过率、字段完整度 | schema 通过率 >= 95%，联系方式反编造失败不得高于现有链路 |
| Lead Grading | 等级一致率、硬规则一致率、C/Invalid/Watch 分流准确性 | 硬规则一致率 100%，等级差异必须可解释 |
| Deep Enrichment | 字段候选有效率、人工接受率、无证据候选率 | 无证据候选率为 0，人工接受率达到小范围基线 |
| Lead Cleanup | 重复建议准确率、错误合并建议数、人工拒绝率 | 不得出现自动执行，错误合并建议必须可人工拦截 |

### 待讨论问题 7

第四阶段小范围样本量建议定多少？

A. 每类 Agent 10 条以内，只验证链路可跑。

B. 每类 Agent 20-50 条，验证链路、质量和人工审核体验。

C. 每类 Agent 100+ 条，直接追求统计稳定性。

**我的建议：选择 B。**

理由：

- A 只能验证技术连通，无法发现质量问题。
- C 对第四阶段来说成本和人工审核压力偏高。
- B 足够暴露 schema、证据、重复、风险分级和人工审核体验问题，适合小范围运行。

### 已确认决定 7

选择 **B：每类 Agent 20-50 条小范围样本**。

建议样本拆分：

| Agent | 样本量 | 样本构成建议 |
|---|---:|---|
| Source Discovery | 30-50 条 | Low/Medium 官网与目录、High 公开社媒入口、重复 URL、无效 URL、Forbidden 边界 |
| Lead Extraction/Grading | 30-50 条 | A/B/C/Watch/Invalid、联系方式完整/缺失、证据充分/不足、High/Forbidden、疑似编造边界 |
| Deep Enrichment | 20-30 条 | 缺城市、缺联系方式、缺经营信号、缺意向车型、已有勿扰匹配、Forbidden 来源 |
| Lead Cleanup | 20-30 条 | 强重复、弱重复、联系方式冲突、来源证据冲突、Watch 可恢复、Invalid 待确认 |

专业判断：

- 样本必须覆盖风险边界，而不是只挑“容易成功”的 seed 数据。
- 每类 Agent 都应包含成功、失败、阻断和人工复核样本。
- 第四阶段验收不追求规模，而追求 contract 稳定、风控一致和人工可解释。

## 维度 7：服务安全、认证与调用边界

### 初步专业建议

即使 `apps/api` 与 `apps/agents` 同机运行，仍应把 `apps/agents` 当作内部服务保护，不应裸奔暴露 Agent Run API。

建议第四阶段最小安全策略：

- `apps/agents` 仅监听内网或本机地址，默认 `127.0.0.1:8010` 或内网网卡。
- `apps/api` 调用 `apps/agents` 时携带内部 API Key，例如 `X-Agents-Api-Key`。
- `apps/agents` 校验 API Key，不通过则返回 401。
- 请求必须带 `request_id`、`agent_task_run_id`、`trigger_source`。
- 响应不得包含原始密钥、完整 prompt 中的敏感配置、非公开数据。
- `apps/agents` 不直接接收任意 URL 批量抓取请求，必须由 `apps/api` 传入已通过风险策略的输入。

### 待讨论问题 8

第四阶段 `apps/agents` 是否需要鉴权？

A. 不需要，只监听本机端口。

B. 需要简单内部 API Key，`apps/api` 通过 header 调用。

C. 需要完整 JWT / RBAC。

**我的建议：选择 B。**

理由：

- A 在开发阶段方便，但容易形成坏默认。
- C 对同机小范围运行过重，权限主体仍在 `apps/api`。
- B 成本低，能明确服务边界，后续也容易迁移到容器或内网服务。

### 已确认决定 8

选择 **B：`apps/agents` 需要简单内部 API Key 鉴权，`apps/api` 通过 header 调用**。

建议约定：

```text
Header: X-Agents-Api-Key: <AGENTS_API_KEY>
apps/api env: AGENTS_API_KEY
apps/agents env: AGENTS_API_KEY
```

专业判断：

- 第四阶段虽然是同机独立端口，但仍然应把 `apps/agents` 当作内部服务保护。
- 鉴权逻辑不需要绑定用户级 RBAC；用户权限仍由 `apps/api` 控制。
- `apps/agents` 只校验“调用方是否为可信内部服务”。

## 维度 8：失败处理、重试与回滚

### 初步专业建议

第四阶段不要让 `apps/agents` 自己做复杂持久化重试。保持 `apps/api` 是任务主控：

- `apps/api` 创建或复用 `agent_task_runs`。
- `apps/api` 调用 `apps/agents`。
- `apps/agents` 返回成功、失败或阻断。
- `apps/api` 根据错误类型判断是否可重试，并写入 `agent_task_runs`、`failed_cases` 或对应业务结果表。

建议错误分类：

| error_type | 是否可重试 | 说明 |
|---|---:|---|
| `timeout_error` | 是 | HTTP 超时、LLM 超时 |
| `provider_rate_limited` | 是 | LLM 限流 |
| `transient_network_error` | 是 | 网络短暂失败 |
| `schema_validation_error` | 否 | 输出 schema 不合格 |
| `evidence_validation_error` | 否 | 证据缺失或联系方式反编造失败 |
| `risk_blocked` | 否 | High/Forbidden/勿扰/策略阻断 |
| `contract_mismatch` | 否 | apps/api 与 apps/agents contract 不一致 |

### 待讨论问题 9

Agent 失败重试由谁负责？

A. `apps/agents` 自己内部重试并隐藏失败细节。

B. `apps/api` 负责主控重试，`apps/agents` 只返回结构化错误。

C. 双方都重试。

**我的建议：选择 B。**

理由：

- 现有 `apps/api` 已有 `agent_task_runs`、retry worker、调度和审计基础。
- 如果 `apps/agents` 自己持久化重试，会产生两个任务状态源，排障复杂。
- `apps/agents` 可以做单次请求内部的轻量 LLM retry，但最终错误必须结构化返回给 `apps/api`。

### 已确认决定 9

选择 **A：Agent 失败重试由 `apps/agents` 自己负责，`apps/api` 已有的 `agent_task_runs`、retry worker 只是临时保留，后续希望去掉**。

该决定意味着第四阶段的长期目标从“`apps/api` 作为 Agent 主控”调整为：

```text
apps/api
  -> 业务入口、权限、人工操作、业务表写入
  -> 发起 Agent 请求 / 查询 Agent 结果

apps/agents
  -> Agent 任务主控
  -> LangGraph 执行
  -> 节点级状态
  -> Agent 失败重试
  -> Agent 运行审计
  -> 返回结构化结果给 apps/api
```

过渡期建议：

- 第四阶段仍要保持 `apps/api` 现有 `agent_task_runs` 不破坏，因为 `apps/api` 当前业务代码和测试依赖它。
- 但新增 LangGraph Agent 的重试状态应优先在 `apps/agents` 内表达，避免继续扩大 `apps/api` 的 Agent 主控职责。
- `apps/api` 可以临时保存一份摘要或外部 run id，例如 `agent_task_runs.output_summary_json.external_agent_run_id`，用于兼容现有页面/指标。
- 后续阶段再迁移或废弃 `apps/api` 的 retry worker、scheduler 中与 Agent 执行强相关的部分。

专业判断：

- 选择 A 更符合“`apps/agents` 独立服务”的长期方向。
- 主要风险是第四阶段可能出现两个运行状态源：`apps/api.agent_task_runs` 与 `apps/agents` 自己的 run 状态。
- 因此必须定义清楚：第四阶段 `apps/agents` 是 Agent 执行事实源；`apps/api.agent_task_runs` 只是兼容摘要，不作为 LangGraph 节点级状态源。
- 如果第四阶段要让 `apps/agents` 真正负责重试，`apps/agents` 需要自己的运行状态存储。小范围运行可先使用内存/文件/轻量表，但进入更稳定阶段前应设计持久化。

## 维度 9：BMAD Story 拆分方向

### 初步专业建议

第四阶段如果范围选 C，建议拆成多个小 Story，而不是一个“大迁移 Story”：

1. **P4-E1 Agent 服务化基础**
   - `apps/agents` FastAPI 入口、健康检查、内部 API Key、统一 envelope。

2. **P4-E2 API 到 Agents HTTP Runtime Client**
   - `apps/api` 新增 `HttpAgentRuntime`、配置项、超时、错误归一化、contract tests。

3. **P4-E3 Deep Enrichment / Lead Cleanup active 接入**
   - 两个低风险 Agent 通过 HTTP active_run，保持 `apps/api` 写库与人工审核。

4. **P4-E4 Source Discovery LangGraph shadow**
   - 独立图、影子运行、候选来源对照指标。

5. **P4-E5 Lead Extraction/Grading LangGraph shadow**
   - 组合 API、内部拆图、抽取/分级对照指标。

6. **P4-E6 观测、失败案例与 Go/No-Go 报告**
   - 节点 trace 摘要、失败分类、样本报告、是否允许下一阶段 active 切换。

### 待讨论问题 10

第四阶段 Story 拆分要偏哪种节奏？

A. 技术基础优先：先做服务化与 runtime client，再逐个 Agent 接入。

B. 业务闭环优先：先让 Deep Enrichment / Lead Cleanup 跑通 HTTP active，再补 Source Discovery 和 Extraction/Grading。

C. 对照验证优先：先做 Source Discovery 和 Extraction/Grading shadow，低风险 Agent 后置。

**我的建议：选择 A。**

理由：

- 你的目标已经明确为 `apps/agents` 独立服务，服务化和 HTTP runtime 是所有 Agent 的共同地基。
- 没有统一 contract 和错误模型，后续每个 Agent 都会重复造一套调用方式。
- A 最符合 BMAD 小步迭代：先地基，再低风险 active，再核心链路 shadow。

### 已确认决定 10

选择 **A：技术基础优先，先做服务化与 runtime client，再逐个 Agent 接入**。

第四阶段 Story 拆分顺序建议更新为：

1. `apps/agents` 独立 FastAPI 服务基础：健康检查、内部 API Key、统一 request/response envelope。
2. `apps/agents` Agent run 状态与重试基础：先支持小范围运行，明确它是 Agent 执行事实源。
3. `apps/api` HTTP Agent client：调用 `apps/agents`，保存兼容摘要，不再扩大 `apps/api` Agent 主控职责。
4. Deep Enrichment / Lead Cleanup HTTP active 接入。
5. Source Discovery LangGraph shadow。
6. Lead Extraction/Grading LangGraph shadow。
7. 对照指标、失败案例、Go/No-Go 报告和是否迁移更多主控职责的决策。

专业判断：

- 与此前“`apps/api` 主控重试”的建议相比，当前 Story 拆分需要提前加入 `apps/agents` 自身 run 状态与重试能力。
- 但仍不建议第四阶段一次性删除 `apps/api` 的 `agent_task_runs` 和 retry worker；删除应作为后续阶段单独 Story，避免影响现有链路。

## 维度 10：apps/agents 自身运行状态存储

### 初步专业建议

既然已确认 Agent 重试由 `apps/agents` 自己负责，`apps/agents` 必须有自己的 run 状态表达。否则独立服务一旦重启，就无法恢复失败任务，也无法支撑后续去掉 `apps/api` retry worker。

可选方案：

A. **内存状态**：第四阶段最简单，但服务重启即丢失。

B. **本地文件 / SQLite**：适合本地小范围运行，能持久化 run 状态，但与 PostgreSQL 主库割裂。

C. **独立 PostgreSQL 表，由 `apps/agents` 自己管理**：最接近未来事实源，但需要新迁移和边界设计。

D. **复用现有 PostgreSQL，但通过 `apps/agents` 自己的表，不写 core 表**：同一数据库连接，但 schema/table 归属独立。

**我的建议：第四阶段选择 D。**

理由：

- A/B 对“后续去掉 `apps/api` retry worker”的目标支撑不够。
- C 如果指完全独立数据库，会增加部署复杂度。
- D 最符合当前小范围运行：同一 PostgreSQL 实例，新增 `agent_service_runs` / `agent_service_node_runs` 等 `apps/agents` 专属表，`apps/agents` 只管理 Agent 运行状态，不写 core 业务表。

### 待讨论问题 11

`apps/agents` 自身运行状态存储选择哪种？

A. 第四阶段先用内存状态。

B. 第四阶段先用本地文件 / SQLite。

C. `apps/agents` 使用独立数据库。

D. 使用同一 PostgreSQL 实例，但新增 `apps/agents` 专属运行表，不写 core 业务表。

**我的建议：选择 D。**

### 已确认决定 11

选择 **D：使用同一 PostgreSQL 实例，但新增 `apps/agents` 专属运行表，不写 core 业务表**。

建议表方向：

```text
agent_service_runs
  -> apps/agents 的 Agent run 事实源
  -> 保存 agent_type、status、mode、request_id、trigger_source、retry_count、started_at、finished_at、error_type、error_message、output_summary_json

agent_service_node_runs
  -> 可选，第四阶段可先不建或作为后续增强
  -> 保存每个 LangGraph node 的状态、耗时、输入摘要、输出摘要和错误
```

边界约定：

- `apps/agents` 可以写自己的运行表。
- `apps/agents` 不写 `customers`、`lead_sources`、`contact_methods`、`staging_leads` 等业务表。
- `apps/api` 仍负责业务表写入、人工确认、合规硬规则和对外 API。
- 同一 PostgreSQL 实例只是部署便利，不代表两个服务共享业务写权限。

专业判断：

- 这个选择最符合“`apps/agents` 后续接管 Agent 重试”的目标。
- 也避免第四阶段引入独立数据库带来的部署复杂度。
- 后续如果 `apps/agents` 独立部署成容器或服务，仍可继续使用同一数据库连接串或迁移到独立 schema。

## 维度 11：apps/api 的 agent_task_runs 过渡策略

### 初步专业建议

当前 `apps/api` 已有 `agent_task_runs`，不能在第四阶段直接删除。建议把它定位为“兼容摘要表”，而不是 LangGraph 执行事实源。

过渡方式：

```text
apps/api.agent_task_runs
  -> 保存业务入口、触发来源、外部 agent_service_run_id、最终摘要

apps/agents.agent_service_runs
  -> 保存 Agent 执行事实、状态、重试、节点 trace
```

### 待讨论问题 12

第四阶段是否要立刻改造 `apps/api.agent_task_runs`？

A. 不改，只在 output_summary_json 里保存 external_agent_run_id。

B. 小改，增加 `external_agent_run_id` / `runtime_source` 字段。

C. 大改，直接迁移到 `apps/agents` 状态表。

**我的建议：选择 A。**

理由：

- A 最小改动，符合“apps/api LLM Agent 保持不变”的边界。
- B 需要迁移，收益有限。
- C 风险过大，会影响现有 API、测试和指标。

### 已确认决定 12

选择 **A：第四阶段不改造 `apps/api.agent_task_runs` 表结构，只在 `output_summary_json` 中保存 `external_agent_run_id`**。

建议摘要结构：

```json
{
  "runtime_source": "apps_agents_http",
  "external_agent_run_id": "uuid",
  "agents_base_url": "http://127.0.0.1:8010",
  "agent_mode": "active|shadow|dry_run",
  "schema_version": "...",
  "status": "succeeded|failed|blocked",
  "writes_core_tables": false
}
```

专业判断：

- 这能保持 `apps/api` 现有模型、迁移、测试和指标尽量不变。
- `apps/api.agent_task_runs` 在第四阶段定位为兼容摘要，不再作为 LangGraph 执行事实源。
- 真正的 Agent 执行状态、节点状态和重试状态归 `apps/agents.agent_service_runs` 管理。

## 阶段性收敛结论

截至本轮，第四阶段核心架构决策如下：

1. 迁移范围选择 C：Deep Enrichment、Lead Cleanup、Source Discovery、Lead Extraction/Grading 全部做 LangGraph 平行版本。
2. `apps/agents` 独立服务运行，`apps/api` 通过 HTTP API 调用，不做本地包注入。
3. 本地小范围运行采用同机同环境、独立端口：`apps/api:8000`，`apps/agents:8010`。
4. `Lead Extraction/Grading` 外部优先提供组合 API，内部保留抽取和分级子图边界。
5. Deep Enrichment 和 Lead Cleanup 可进入 active_run；Source Discovery 和 Lead Extraction/Grading 先 shadow_run。
6. LangGraph 节点日志第四阶段先通过响应 audit 摘要写入 `agent_task_runs.output_summary_json`，预留节点级表。
7. 每类 Agent 小范围样本量采用 20-50 条。
8. `apps/agents` 使用内部 API Key 鉴权。
9. Agent 失败重试由 `apps/agents` 负责，`apps/api` 的 `agent_task_runs` / retry worker 是临时兼容层，后续希望去掉。
10. `apps/agents` 使用同一 PostgreSQL 实例管理自己的专属运行表，不写 core 业务表。
11. 第四阶段不改造 `apps/api.agent_task_runs` 表结构，只在 `output_summary_json` 保存 `external_agent_run_id` 等兼容摘要。

## 下一步待讨论

后续还需要继续收敛：

- `apps/agents` 的 FastAPI endpoint 具体 request/response schema。
- `agent_service_runs` 最小字段和是否需要 `agent_service_node_runs` 在第四阶段落表。
- 四类 LangGraph 的具体 state schema。
- `apps/api` 调用 `apps/agents` 的超时、错误分类和回调/轮询方式。
- 第四阶段 BMAD Epic / Story / 验收标准正式拆分。
