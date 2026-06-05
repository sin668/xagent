# Story P4-E4-S3：apps/api 接入 Deep Enrichment HTTP active_run

状态：已实现  
Sprint：Sprint 4  
优先级：P0  
Epic：P4-E4

## 用户故事

作为业务操作人员，我希望 Deep Enrichment 可以通过 `apps/api` 调用 `apps/agents` active_run，并仍由 `apps/api` 控制字段候选采纳，以便小范围验证独立 Agent 服务。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 在 `apps/api` 中为 Deep Enrichment 接入 HTTP active_run，保留现有业务写入和人工审核边界。

**建议文件：**

- Modify: `apps/api/app/services/`
- Modify: `apps/api/app/agents/`
- Test: `apps/api/tests/test_deep_enrichment_http_active_run.py`

**验收标准：**

- `apps/api` 通过 HTTP 调用 `apps/agents` Deep Enrichment。
- `agent_task_runs.output_summary_json` 保存 `external_agent_run_id`。
- 字段候选仍由 `apps/api` schema 校验、风险门禁和人工确认后写入。
- 可通过配置或小范围开关控制是否使用 HTTP active_run。

**非目标：**

- 不删除现有本地 Deep Enrichment 逻辑。
- 不自动采纳字段候选。
- 不改 core 表结构。

## Codex 提示词

```text
请执行 P4-E4-S3：apps/api 接入 Deep Enrichment HTTP active_run。
要求使用 TDD；保留现有本地 Agent 行为；字段候选必须由 apps/api 审核后写入；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 必须执行 `apps/api` 与 `apps/agents` 服务间真实联调。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- `apps/api` 中现有 LLM Agent 保持不变。
- Deep Enrichment 只输出候选，不自动写入客户主数据。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。

## 实施记录

### 实现内容

- 在 `apps/api` 增加 Deep Enrichment HTTP active_run 开关：
  - `AGENT_DEEP_ENRICHMENT_HTTP_ACTIVE_ENABLED`
  - `VEHICLE_LEADS_AGENT_DEEP_ENRICHMENT_HTTP_ACTIVE_ENABLED`
- 默认关闭；未配置 `AGENTS_API_KEY` 时不会启用 HTTP active_run。
- 新增 `select_deep_enrichment_runtime(settings)`：
  - 开关关闭时返回 `None`。
  - 开关开启且 `AGENTS_API_KEY` 有效时返回 `HttpAgentRuntime`。
- `HttpAgentRuntime` 新增 `run_deep_enrichment_response()`，用于保留完整 phase4 envelope。
- 保留原有 `run_deep_enrichment()`，继续返回 phase3 output，兼容既有 service 调用。
- `LeadEnrichmentService.run_deep_enrichment_agent(...)` 支持 HTTP active_run：
  - HTTP runtime 返回 phase4 envelope 时，从 `output` 中取 phase3 Deep Enrichment 结果。
  - 字段候选仍由 `apps/api` 创建 `lead_enrichment_field_candidates`，且 `review_status=pending`。
  - 成功时 `agent_task_runs.output_summary_json` 保存 `external_agent_run_id`、`external_agent_status`、`external_agent_type`、`agents_base_url` 和脱敏审计摘要。
  - 失败时保留 `external_agent_run_id`、`external_agent_error` 和外部失败节点摘要。
- `create_lead_enrichment_run` 在创建 pending run 后，按配置选择是否立即触发 HTTP active_run。
- 未删除现有本地 Deep Enrichment runtime 行为；开关关闭时仍保持原流程。

### TDD 记录

- RED 1：新增 `tests/test_deep_enrichment_http_active_run.py`，初次运行因缺少 `select_deep_enrichment_runtime` 导入失败。
- GREEN 1：新增配置开关、runtime 选择器、`HttpAgentRuntime.run_deep_enrichment_response()`，并让 service 保存 HTTP active_run 的 external summary。
- RED 2：补充 HTTP active_run 失败态测试，发现失败时 `external_agent_run_id` 丢失。
- GREEN 2：调整失败分支，使用 `AgentTaskRunService.fail_with_external_agent_summary(...)` 保存外部失败摘要。
- 补充入口层断言，确认 `create_lead_enrichment_run` 调用 runtime 选择器和 `run_deep_enrichment_agent(...)`。

### 验证结果

- P4-E4-S3 聚焦测试：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_deep_enrichment_http_active_run.py -q`
  - 结果：5 passed
- `apps/api` 聚焦回归：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_agents_settings.py tests/test_phase3_agent_runtime_integration.py tests/test_lead_enrichment_run_api.py tests/agents/test_http_runtime_compatibility.py tests/agents/test_agent_task_run_external_summary.py tests/contracts/test_http_agent_client_contract.py tests/agents/test_agent_run_result_consumption.py -q`
  - 结果：33 passed
- `apps/agents` 全量测试：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest -q`
  - 结果：59 passed
- `apps/agents` Deep Enrichment API 聚焦测试：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_deep_enrichment_api.py -q`
  - 结果：3 passed
- `apps/api` 导入与路由检查：
  - `app.title` 为 `Overseas Vehicle Leads AI API`。
  - `select_deep_enrichment_runtime(...)` 在开关和 API Key 有效时返回 `HttpAgentRuntime`。
  - `/staging-leads/{lead_id:uuid}/enrichment-runs` 路由存在。

### 服务联调说明

- 已通过 `HttpAgentRuntime` contract tests 和 `apps/agents` FastAPI `TestClient` 覆盖 HTTP envelope、鉴权、状态和输出契约。
- 已尝试启动真实 `apps/agents` 服务并由 `apps/api` 通过真实 HTTP 访问：
  - 命令使用 `uvicorn app.main:app --host 127.0.0.1 --port 18110`。
  - 当前沙箱返回 `ERROR: [Errno 1] error while attempting to bind on address ('127.0.0.1', 18110): operation not permitted`。
  - 因环境禁止 bind 本地端口，本 Story 未能完成真实 socket 级联调；已记录为验证限制。
- 未调用真实 LLM，未连接生产数据库。

## 文件清单

- 修改：`apps/api/app/api/lead_enrichment.py`
- 修改：`apps/api/app/agents/http_runtime.py`
- 修改：`apps/api/app/services/lead_enrichment.py`
- 修改：`apps/api/app/settings.py`
- 修改：`apps/api/tests/test_agents_settings.py`
- 新增：`apps/api/tests/test_deep_enrichment_http_active_run.py`
- 修改：`docs/stories/phase-4-small-run/P4-E4-S3-api-deep-enrichment-active-run.md`

## 两轮独立评审记录

### 第一轮独立评审：验收标准与业务边界复核

评审维度：

- 是否通过 `apps/api` 调用 `apps/agents` Deep Enrichment。
- 是否通过配置开关控制 HTTP active_run。
- 是否保留现有本地 Deep Enrichment 行为。
- 是否保存 `external_agent_run_id`。
- 字段候选是否仍由 `apps/api` 校验和写入待审核候选表。
- 是否避免自动采纳字段候选、修改 core 表或绕过人工确认。

结论：

- 初版基本满足成功路径，但发现一个需要修正的问题。

发现项：

- HTTP active_run 失败时，`agent_task_runs.output_summary_json` 未保存 `external_agent_run_id` 和外部错误摘要，不利于后续观测和排障。

修正结果：

- 新增失败态测试 `test_deep_enrichment_http_active_run_failure_preserves_external_agent_summary`。
- 在失败分支使用 `AgentTaskRunService.fail_with_external_agent_summary(...)` 保存外部失败 envelope 摘要。
- 修正后 P4-E4-S3 聚焦测试 5 passed。

### 第二轮独立评审：回归、联调与风控复核

评审维度：

- 是否破坏 P4-E3 HTTP runtime/client contract。
- 是否破坏 P4-E4-S1 `apps/agents` Deep Enrichment HTTP API。
- 是否保持 `apps/api` 和 `apps/agents` HTTP 服务边界，不做本地包注入。
- 是否保持 `/staging-leads/{lead_id:uuid}/enrichment-runs` 路由可用。
- 是否满足 Story 要求的服务间联调。

结论：

- 代码与契约测试通过；真实 socket 级服务间联调因当前环境禁止端口绑定未完成。

发现项：

- `uvicorn` 绑定 `127.0.0.1:18110` 失败，错误为 `operation not permitted`。该问题来自当前执行环境限制，不是应用代码测试失败。

修正结果：

- 已记录验证限制。
- 以 `apps/api` HTTP runtime contract tests、`apps/agents` FastAPI TestClient 和双方聚焦/全量测试作为本轮替代验证证据。
