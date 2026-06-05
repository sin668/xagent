# Story P4-E5-S1：实现 Source Discovery Graph

状态：已实现  
Sprint：Sprint 5  
优先级：P0  
Epic：P4-E5

## 用户故事

作为 Agent 服务开发者，我希望在 `apps/agents` 中实现 Source Discovery 的 LangGraph 平行版本，以便在不影响现有生产链路的情况下进行 shadow 对照。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`
- `docs/brainstorm/brainstorming-session-2026-06-04-第四阶段小范围运行-LangGraph-Agent迁移.md`

## Story 定义

**目标：** 创建 Source Discovery LangGraph graph，支持 shadow_run 输入和结构化候选来源输出。

**建议文件：**

- Create: `apps/agents/app/graphs/source_discovery.py`
- Create: `apps/agents/app/schemas/source_discovery.py`
- Modify: `apps/agents/app/api/agent_runs.py`
- Test: `apps/agents/tests/test_source_discovery_graph.py`

**验收标准：**

- graph 能接收来源发现输入并输出候选 URL、来源类型、初步风险和证据摘要。
- API 或 graph mode 明确标记为 `shadow_run`。
- shadow_run 不写 `lead_source_candidates` 或任何 core 业务表。
- run 状态写入 `agent_service_runs`。

**非目标：**

- 不替换现有 Source Discovery 生产入口。
- 不抓取非公开数据。
- 不实现完整对照报告。

## Codex 提示词

```text
请执行 P4-E5-S1：实现 Source Discovery Graph。
要求使用 TDD；仅做 shadow_run；不得写 lead_source_candidates 或 core 业务表；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- Source Discovery 第四阶段只 shadow_run。
- Forbidden、High 风险、非公开数据不得被误放。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。

## 实施记录

### 实现内容

- 新增 `apps/agents/app/schemas/source_discovery.py`：
  - 定义 `SourceCandidateOutput`。
  - 定义 `SourceDiscoveryAgentOutput`。
  - 输出 schema 使用 `phase4.agent.source_discovery.v1`。
- 新增 `apps/agents/app/graphs/source_discovery.py`：
  - 使用 LangGraph `StateGraph` 编译 Source Discovery graph。
  - 节点顺序为：
    - `load_channel_strategy`
    - `build_discovery_queries`
    - `search_public_sources`
    - `normalize_source_candidates`
    - `classify_channel_risk`
    - `dedupe_candidates`
    - `validate_source_evidence`
    - `output_shadow_candidates`
  - 输入支持 `market`、`channel_strategy`、`seed_urls`、`search_results`、`requested_actions`。
  - 输出候选包含 URL、归一化 URL、来源类型、初步风险、证据摘要、发现 query 和审核状态。
  - `public_social` 初步风险为 `high`，输出为 `needs_manual_review`。
  - 登录墙、验证码、私有来源和缺少 URL/证据摘要的来源进入 `blocked_items`。
  - `agent_mode != shadow` 时直接失败，确保第四阶段只允许 shadow_run。
- 修改 `apps/agents/app/api/agent_runs.py`：
  - 新增 `POST /agent-runs/source-discovery`。
  - 复用统一 Agent Run envelope。
  - run 创建、running、succeeded/failed 状态写入 `agent_service_runs`。
  - 成功时保存 output、output_summary 和 audit。
  - active mode 或私有采集动作会返回 failed envelope，`error_type=risk_blocked`。
- 修改 `apps/agents/app/adapters/api_contract.py`：
  - 允许 `shadow_source_candidates` 作为第四阶段 shadow 输出表。
  - 明确禁止 `lead_source_candidates`，避免 shadow 输出污染真实来源候选池。
- 修改 `apps/agents/tests/test_api_contract.py`：
  - 更新边界合同测试，覆盖 shadow 输出白名单和真实来源池禁写。

### TDD 记录

- RED 1：新增 `tests/test_source_discovery_graph.py`，初次运行因缺少 `app.graphs.source_discovery` 导入失败。
- RED 2：新增 `tests/test_source_discovery_api.py`，固定 `/agent-runs/source-discovery` 的统一 envelope、shadow mode、run 状态和禁 active 合同。
- GREEN 1：新增 Source Discovery schema、LangGraph runner 和 API endpoint。
- GREEN 2：扩展 `ApiContractBoundary`，允许 `shadow_source_candidates`，同时禁止 `lead_source_candidates`。
- 回归修正：`tests/test_api_contract.py` 旧合同仍只允许两个 staging 输出表，已更新为“staging + shadow 输出白名单”合同。

### 验证结果

- Source Discovery 聚焦测试：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_source_discovery_graph.py tests/test_source_discovery_api.py -q`
  - 结果：7 passed
- Source Discovery + API contract 聚焦回归：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_source_discovery_graph.py tests/test_source_discovery_api.py tests/test_api_contract.py -q`
  - 结果：11 passed
- `apps/agents` 全量测试：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest -q`
  - 结果：66 passed

### 服务联调说明

- 已通过 `apps/agents` FastAPI TestClient 验证 `/agent-runs/source-discovery` 的鉴权、统一 envelope、shadow 输出、失败 envelope 和 `agent_service_runs` 状态写入。
- 已尝试启动真实 `apps/agents` 服务：
  - 命令使用 `uvicorn app.main:app --host 127.0.0.1 --port 18113`。
  - 当前沙箱返回 `ERROR: [Errno 1] error while attempting to bind on address ('127.0.0.1', 18113): operation not permitted`。
  - 因环境禁止 bind 本地端口，本 Story 未能完成真实 socket 级联调；已记录为验证限制。
- 未调用真实搜索引擎、真实 LLM 或生产数据库。

## 文件清单

- 新增：`apps/agents/app/graphs/source_discovery.py`
- 新增：`apps/agents/app/schemas/source_discovery.py`
- 修改：`apps/agents/app/api/agent_runs.py`
- 修改：`apps/agents/app/adapters/api_contract.py`
- 新增：`apps/agents/tests/test_source_discovery_graph.py`
- 新增：`apps/agents/tests/test_source_discovery_api.py`
- 修改：`apps/agents/tests/test_api_contract.py`
- 修改：`docs/stories/phase-4-small-run/P4-E5-S1-source-discovery-graph.md`

## 两轮独立评审记录

### 第一轮独立评审：验收标准与 shadow 边界复核

评审维度：

- graph 是否能接收来源发现输入并输出候选 URL、来源类型、初步风险和证据摘要。
- Source Discovery 是否明确只允许 shadow_run。
- shadow_run 是否不写 `lead_source_candidates` 或 core 业务表。
- Forbidden、登录墙、验证码、私有来源是否不会进入可抽取候选。
- High 风险来源是否只进入待人工审核候选。
- run 状态是否写入 `agent_service_runs`。

结论：

- 初版实现满足 Story 主要验收标准，但发现一个需要修正的合同测试问题。

发现项：

- `ApiContractBoundary` 扩展了 `shadow_source_candidates` 后，旧测试 `test_api_contract_boundary_allows_only_staging_outputs` 仍使用第三/第四阶段早期合同，只允许 Deep Enrichment 与 Lead Cleanup 两个输出表。

修正结果：

- 更新合同测试为 `test_api_contract_boundary_allows_only_staging_and_shadow_outputs`。
- 明确 `shadow_source_candidates` 允许，`lead_source_candidates` 禁止。
- Source Discovery + API contract 聚焦回归 11 passed。

### 第二轮独立评审：回归、服务边界与可运维性复核

评审维度：

- 是否破坏 Deep Enrichment / Lead Cleanup API 和 graph。
- 是否破坏统一 Agent Run envelope。
- 是否保持 `apps/agents` 不写业务 core 表。
- 是否符合 P4-E5-S1 非目标，不替换现有 Source Discovery 生产入口，不输出完整对照报告。
- 是否满足服务间真实联调要求。

结论：

- 代码、合同测试和 `apps/agents` 全量测试通过；真实 socket 级服务联调因当前环境禁止端口绑定未完成。

发现项：

- `uvicorn` 绑定 `127.0.0.1:18113` 失败，错误为 `operation not permitted`。该问题来自当前执行环境限制，不是应用代码测试失败。

修正结果：

- 已记录验证限制。
- 已用 FastAPI TestClient、graph tests、API contract tests 和 `apps/agents` 全量测试作为替代验证证据。
- 第二轮未发现新增实质阻塞问题，当前 Story 可收口。
