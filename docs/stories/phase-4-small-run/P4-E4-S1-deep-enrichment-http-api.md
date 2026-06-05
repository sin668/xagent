# Story P4-E4-S1：实现 Deep Enrichment LangGraph HTTP API

状态：已实现  
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

## 实施记录

### 实现内容

- 在 `apps/agents` 新增 `POST /agent-runs/deep-enrichment`。
- API 使用统一 `AgentRunRequest` / `AgentRunResponse` envelope，并通过 `X-Agents-Api-Key` 鉴权。
- Deep Enrichment runner 使用 LangGraph `StateGraph` 编译为 `CompiledStateGraph` 后执行。
- API 创建并更新 `agent_service_runs`：
  - 创建时为 `pending`。
  - 执行前标记 `running`。
  - 成功后标记 `succeeded`，写入 `output_json`、`output_summary_json`、`audit_json`。
  - 风险阻断或 schema 类异常时标记 `failed`，记录 `error_type` 和 `error_message`。
- 成功输出仅返回 Deep Enrichment 候选结构：
  - `field_candidates`
  - `missing_fields`
  - `recommended_next_action`
  - `audit`
  - `agent_run_id`
  - `staging_lead_id`
- API 和 graph audit 均保持 `writes_core_tables=false`。
- 新增 `apps/agents` 同步 DB session 依赖，支持 `AGENTS_DATABASE_URL`，未配置时回退 `DATABASE_URL`，再回退本地 `sqlite:///./agents.db`。
- 更新 `apps/agents/README.md`，补充 Agent 运行状态数据库配置说明。

### TDD 记录

- RED 1：新增 `tests/test_deep_enrichment_api.py`，初次运行因缺少 `app.db.session` 失败。
- GREEN 1：补充 DB session、Agent Run router，并在 `app.main` 挂载 `/agent-runs/deep-enrichment`。
- RED 2：第一轮评审发现 runner 仍是手写顺序调用，不足以证明 “LangGraph HTTP API”；新增 `test_deep_enrichment_graph_runner_uses_compiled_langgraph`，先确认失败。
- GREEN 2：将 `DeepEnrichmentGraphRunner` 改为使用 LangGraph `StateGraph` 编译图执行，保持原有节点顺序和输出契约。
- RED 3：第一轮评审发现 DB URL 硬编码；新增 `tests/test_agents_settings.py`，先确认 settings 缺少 `database_url`。
- GREEN 3：补充 `AgentSettings.database_url` 和 `get_db_session()` 配置读取。

### 验证结果

- Story/API/Graph/Settings 聚焦测试：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_agents_settings.py tests/test_deep_enrichment_api.py tests/test_deep_enrichment_graph.py -q`
  - 结果：9 passed
- `apps/agents` 全量测试：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest -q`
  - 结果：55 passed
- `apps/api` HTTP Agent client 聚焦回归：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/contracts/test_http_agent_client_contract.py tests/agents/test_http_agent_runtime.py tests/agents/test_http_runtime_compatibility.py tests/agents/test_agent_run_result_consumption.py tests/test_agents_settings.py -q`
  - 结果：29 passed
- `apps/agents` 路由和 LangGraph 编译图检查：
  - 确认 `/agent-runs/deep-enrichment` 已挂载。
  - 确认 `/health` 仍存在。
  - 确认 `DeepEnrichmentGraphRunner().compiled_graph` 类型为 `CompiledStateGraph`。

### 服务联调说明

- 本 Story 使用 FastAPI `TestClient` 对 `apps/agents` 真实 HTTP 路由进行请求，覆盖鉴权、统一 envelope、状态入库、成功输出和失败记录。
- 测试通过依赖覆盖使用 SQLite 内存库，不调用真实 LLM，不连接真实外部服务。
- 本 Story 未接入 `apps/api` active_run，未实现人工审核写入，未自动采纳字段候选，符合非目标。

## 文件清单

- 修改：`apps/agents/README.md`
- 新增：`apps/agents/app/api/__init__.py`
- 新增：`apps/agents/app/api/agent_runs.py`
- 新增：`apps/agents/app/db/session.py`
- 修改：`apps/agents/app/graphs/deep_enrichment.py`
- 修改：`apps/agents/app/main.py`
- 修改：`apps/agents/app/settings.py`
- 新增：`apps/agents/tests/test_agents_settings.py`
- 新增：`apps/agents/tests/test_deep_enrichment_api.py`
- 修改：`apps/agents/tests/test_deep_enrichment_graph.py`
- 修改：`docs/stories/phase-4-small-run/P4-E4-S1-deep-enrichment-http-api.md`

## 两轮独立评审记录

### 第一轮独立评审：验收标准与技术形态复核

评审维度：

- 是否提供 `POST /agent-runs/deep-enrichment`。
- 是否使用统一 Agent Run envelope。
- 是否实际使用 LangGraph，而不是仅保留普通 Python 顺序 runner。
- 是否写入 `agent_service_runs` 并记录成功/失败状态。
- 是否避免写入 `customers`、`contact_methods`、`staging_leads` 等 core 表。
- 是否失败时记录错误类型和错误消息。
- 是否避免接入 `apps/api` active_run、人工审核写入和自动采纳字段候选。

结论：

- 初版基本满足 HTTP API 和状态入库，但发现两个需要修正的问题。

发现项：

- Deep Enrichment runner 初版仍是手写顺序调用，不能充分证明 Story 要求的 LangGraph API 形态。
- DB session 初版硬编码 `sqlite:///./agents.db`，不符合独立服务后续环境配置和部署要求。

修正结果：

- 新增 LangGraph 形态测试，并将 runner 改为 `StateGraph(...).compile()` 后执行，验证类型为 `CompiledStateGraph`。
- 新增 settings 测试，并让 `AGENTS_DATABASE_URL` 优先、`DATABASE_URL` 回退、本地 SQLite 默认。
- 相关测试修正后 9 passed，`apps/agents` 全量 55 passed。

### 第二轮独立评审：回归、风控与联调复核

评审维度：

- 是否破坏 `apps/agents` 已有 health、鉴权、envelope、状态服务、重试策略和 trace 测试。
- 是否破坏 `apps/api` HTTP Agent client 既有契约。
- 是否保持 `/health` 公开、Agent Run API 受 API Key 保护。
- 是否保持 `apps/api` 和 `apps/agents` HTTP 服务边界，不做本地包注入。
- 是否保持 Deep Enrichment 只输出候选、不自动写 core 表、不自动触达、不自动采纳。

结论：

- 通过。未发现新增实质阻塞问题。

发现项：

- 未发现新增实质阻塞问题。

修正结果：

- 无需进一步修正。
