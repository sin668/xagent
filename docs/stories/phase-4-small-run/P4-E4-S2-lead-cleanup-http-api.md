# Story P4-E4-S2：实现 Lead Cleanup LangGraph HTTP API

状态：已实现  
Sprint：Sprint 4  
优先级：P0  
Epic：P4-E4

## 用户故事

作为 Agent 服务开发者，我希望 `apps/agents` 提供 Lead Cleanup 的 LangGraph HTTP API，以便 `apps/api` 可以通过 active_run 获取重复、冲突和清洗建议。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`
- `apps/agents/README.md`

## Story 定义

**目标：** 在 `apps/agents` 中实现 Lead Cleanup graph 和 `POST /agent-runs/lead-cleanup`。

**建议文件：**

- Create/Modify: `apps/agents/app/api/agent_runs.py`
- Create/Modify: `apps/agents/app/graphs/lead_cleanup.py`
- Create/Modify: `apps/agents/app/schemas/lead_cleanup.py`
- Test: `apps/agents/tests/test_lead_cleanup_api.py`

**验收标准：**

- API 使用统一 Agent Run envelope。
- 输出仅包含清洗建议、重复原因、冲突字段、证据和置信度。
- 不自动归并客户、不自动恢复 Invalid、不自动执行清洗动作。
- run 状态写入 `agent_service_runs`。
- 失败时记录错误类型和错误消息。

**非目标：**

- 不接入 `apps/api` active_run。
- 不实现人工审核写入。
- 不修改客户、来源或联系方式表。

## Codex 提示词

```text
请执行 P4-E4-S2：实现 Lead Cleanup LangGraph HTTP API。
要求使用 TDD；只输出清洗建议；不得自动归并、自动恢复 Invalid 或写 core 表；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- Lead Cleanup 只输出建议，不自动执行。
- 人工确认和业务写入仍由 `apps/api` 负责。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。

## 实施记录

### 实现内容

- 在 `apps/agents` 新增 `POST /agent-runs/lead-cleanup`。
- API 使用统一 `AgentRunRequest` / `AgentRunResponse` envelope，并通过 `X-Agents-Api-Key` 鉴权。
- Lead Cleanup runner 使用 LangGraph `StateGraph` 编译为 `CompiledStateGraph` 后执行。
- API 创建并更新 `agent_service_runs`：
  - 创建时为 `pending`。
  - 执行前标记 `running`。
  - 成功后标记 `succeeded`，写入 `output_json`、`output_summary_json`、`audit_json`。
  - 自动执行、删除线索、自动恢复 Invalid 等风险动作请求会标记 `failed`，记录 `error_type=risk_blocked` 和错误消息。
- 成功输出仅返回 Lead Cleanup 建议结构：
  - `suggestions`
  - `blocked_items`
  - `audit`
  - `cleanup_run_id`
- 清洗建议保持 `review_status=pending`，只供后续人工审核链路消费。
- API 和 graph audit 均保持 `writes_core_tables=false`、`auto_execute_cleanup=false`、`auto_restore_invalid=false`。

### TDD 记录

- RED 1：新增 `tests/test_lead_cleanup_api.py`，初次运行因缺少 `/agent-runs/lead-cleanup` 路由返回 404。
- GREEN 1：在 `apps/agents/app/api/agent_runs.py` 中新增 Lead Cleanup HTTP API，并复用 `agent_service_runs` 状态写入模式。
- RED 2：新增 `test_lead_cleanup_graph_runner_uses_compiled_langgraph`，初次运行因 runner 缺少 `compiled_graph` 失败。
- GREEN 2：将 `LeadCleanupGraphRunner` 改为使用 LangGraph `StateGraph` 编译图执行，保持原有节点顺序和输出契约。

### 验证结果

- Story/API/Graph 聚焦测试：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_lead_cleanup_api.py tests/test_lead_cleanup_graph.py -q`
  - 结果：9 passed
- `apps/agents` 全量测试：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest -q`
  - 结果：59 passed
- `apps/api` HTTP Agent client 聚焦回归：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/contracts/test_http_agent_client_contract.py tests/agents/test_http_agent_runtime.py tests/agents/test_http_runtime_compatibility.py tests/agents/test_agent_run_result_consumption.py tests/test_agents_settings.py -q`
  - 结果：29 passed
- `apps/agents` 路由和 LangGraph 编译图检查：
  - 确认 `/agent-runs/lead-cleanup` 已挂载。
  - 确认 `/agent-runs/deep-enrichment` 仍存在。
  - 确认 `/health` 仍存在。
  - 确认 `LeadCleanupGraphRunner().compiled_graph` 类型为 `CompiledStateGraph`。

### 服务联调说明

- 本 Story 使用 FastAPI `TestClient` 对 `apps/agents` 真实 HTTP 路由进行请求，覆盖鉴权、统一 envelope、状态入库、成功输出和失败记录。
- 测试通过依赖覆盖使用 SQLite 内存库，不调用真实 LLM，不连接真实外部服务。
- 本 Story 未接入 `apps/api` active_run，未实现人工审核写入，未修改客户、来源或联系方式表，符合非目标。

## 文件清单

- 修改：`apps/agents/app/api/agent_runs.py`
- 修改：`apps/agents/app/graphs/lead_cleanup.py`
- 新增：`apps/agents/tests/test_lead_cleanup_api.py`
- 修改：`apps/agents/tests/test_lead_cleanup_graph.py`
- 修改：`docs/stories/phase-4-small-run/P4-E4-S2-lead-cleanup-http-api.md`

## 两轮独立评审记录

### 第一轮独立评审：验收标准与风控边界复核

评审维度：

- 是否提供 `POST /agent-runs/lead-cleanup`。
- 是否使用统一 Agent Run envelope。
- 是否实际使用 LangGraph 编译图。
- 是否写入 `agent_service_runs` 并记录成功/失败状态。
- 是否只输出清洗建议、重复原因、证据和置信度。
- 是否避免自动归并客户、自动恢复 Invalid、自动执行清洗动作。
- 是否失败时记录错误类型和错误消息。
- 是否避免接入 `apps/api` active_run、人工审核写入和 core 表修改。

结论：

- 通过。未发现新增实质阻塞问题。

发现项：

- 未发现新增实质阻塞问题。

修正结果：

- 无需进一步修正。

### 第二轮独立评审：回归、路由与架构边界复核

评审维度：

- 是否破坏 Deep Enrichment HTTP API。
- 是否破坏 `apps/agents` 已有 health、鉴权、envelope、状态服务、重试策略和 trace 测试。
- 是否破坏 `apps/api` HTTP Agent client 既有契约。
- 是否保持 `/health` 公开、Agent Run API 受 API Key 保护。
- 是否保持 `apps/api` 和 `apps/agents` HTTP 服务边界，不做本地包注入。

结论：

- 通过。未发现新增实质阻塞问题。

发现项：

- 未发现新增实质阻塞问题。

修正结果：

- 无需进一步修正。
