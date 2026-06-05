# Story P4-E4-S4：apps/api 接入 Lead Cleanup HTTP active_run

状态：已实现  
Sprint：Sprint 4  
优先级：P0  
Epic：P4-E4

## 用户故事

作为业务操作人员，我希望 Lead Cleanup 可以通过 `apps/api` 调用 `apps/agents` active_run，并仍由 `apps/api` 控制人工审核和清洗执行，以便小范围验证清洗建议质量。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 在 `apps/api` 中为 Lead Cleanup 接入 HTTP active_run，保留现有业务写入、人工审核和清洗执行边界。

**建议文件：**

- Modify: `apps/api/app/services/`
- Modify: `apps/api/app/agents/`
- Test: `apps/api/tests/test_lead_cleanup_http_active_run.py`

**验收标准：**

- `apps/api` 通过 HTTP 调用 `apps/agents` Lead Cleanup。
- `agent_task_runs.output_summary_json` 保存 `external_agent_run_id`。
- 清洗建议仍由 `apps/api` schema 校验、风险门禁和人工确认后处理。
- 不出现自动归并、自动恢复 Invalid 或自动删除数据。

**非目标：**

- 不删除现有本地 Lead Cleanup 逻辑。
- 不自动执行清洗建议。
- 不改 core 表结构。

## Codex 提示词

```text
请执行 P4-E4-S4：apps/api 接入 Lead Cleanup HTTP active_run。
要求使用 TDD；保留现有本地 Agent 行为；清洗建议必须由 apps/api 审核后处理；完成后执行两轮独立评审。
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
- Lead Cleanup 只输出建议，不自动执行。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。

## 实施记录

### 实现内容

- 在 `apps/api` 增加 Lead Cleanup HTTP active_run 开关：
  - `AGENT_LEAD_CLEANUP_HTTP_ACTIVE_ENABLED`
  - `VEHICLE_LEADS_AGENT_LEAD_CLEANUP_HTTP_ACTIVE_ENABLED`
- 默认关闭；未配置 `AGENTS_API_KEY` 时不会启用 HTTP active_run。
- 新增 `select_lead_cleanup_runtime(settings)`：
  - 开关关闭时返回 `None`。
  - 开关开启且 `AGENTS_API_KEY` 有效时返回 `HttpAgentRuntime`。
- `HttpAgentRuntime` 新增 `run_lead_cleanup_response()`，用于保留完整 phase4 envelope。
- 保留原有 `run_lead_cleanup()`，继续返回 phase3 output，兼容既有本地 service 调用。
- `LeadCleanupSuggestionService.run_cleanup_agent(...)` 支持 HTTP active_run：
  - HTTP runtime 返回 phase4 envelope 时，从 `output` 中取 phase3 Lead Cleanup 结果。
  - 清洗建议仍由 `apps/api` 创建 `lead_cleanup_suggestions`，且 `review_status=pending`。
  - 成功时 `agent_task_runs.output_summary_json` 保存 `external_agent_run_id`、`external_agent_status`、`external_agent_type`、`external_agent_mode`、`agents_base_url` 和脱敏审计摘要。
  - 失败时保留 `external_agent_run_id`、`external_agent_error` 和外部失败节点摘要。
- 未新增 Lead Cleanup 自动创建 run 的 API 入口；当前 `apps/api/app/api/lead_cleanup.py` 仍只提供建议查询、审核和执行接口。
- 未删除现有本地 Lead Cleanup runtime 行为；开关关闭或传入本地 runtime 时仍保持原流程。

### TDD 记录

- RED 1：新增 `tests/test_lead_cleanup_http_active_run.py`，初次运行因缺少 `select_lead_cleanup_runtime` 导入失败。
- GREEN 1：新增 Lead Cleanup HTTP active_run 配置开关、runtime 选择器、`HttpAgentRuntime.run_lead_cleanup_response()`，并让 service 保存 HTTP active_run 的 external summary。
- RED 2：补充失败态测试，要求外部 Lead Cleanup 返回 failed envelope 时仍保存 `external_agent_run_id`、`external_agent_error` 和 `failed_node`。
- GREEN 2：在失败分支使用 `AgentTaskRunService.fail_with_external_agent_summary(...)` 保存外部失败摘要。
- 补充 settings alias 测试，确认 prefixed 和 unprefixed 环境变量都能启用 Lead Cleanup HTTP active_run。
- 补充 API 边界断言，确认当前 Lead Cleanup API 不新增自动创建/自动执行 agent run 的入口。

### 验证结果

- P4-E4-S4 聚焦测试：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_lead_cleanup_http_active_run.py -q`
  - 结果：5 passed
- `apps/api` 聚焦回归：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_lead_cleanup_http_active_run.py tests/test_phase3_agent_runtime_integration.py tests/agents/test_http_runtime_compatibility.py tests/agents/test_agent_task_run_external_summary.py tests/contracts/test_http_agent_client_contract.py tests/agents/test_agent_run_result_consumption.py tests/test_agents_settings.py -q`
  - 结果：33 passed
- `apps/agents` 全量测试：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest -q`
  - 结果：59 passed

### 服务联调说明

- 已通过 `HttpAgentRuntime` contract tests 覆盖 `apps/api -> apps/agents` HTTP 请求 payload、endpoint、API Key、phase4 envelope 和 phase3 output 兼容逻辑。
- 已通过 `apps/agents` 全量 FastAPI 测试覆盖 Lead Cleanup 服务端 API、鉴权、状态写入和 LangGraph runner 合同。
- 已尝试启动真实 `apps/agents` 服务并由 `apps/api` 通过真实 HTTP 访问：
  - 命令使用 `uvicorn app.main:app --host 127.0.0.1 --port 18111`。
  - 当前沙箱返回 `ERROR: [Errno 1] error while attempting to bind on address ('127.0.0.1', 18111): operation not permitted`。
  - 因环境禁止 bind 本地端口，本 Story 未能完成真实 socket 级联调；已记录为验证限制。
- 未调用真实 LLM，未连接生产数据库。

## 文件清单

- 修改：`apps/api/app/agents/http_runtime.py`
- 修改：`apps/api/app/services/lead_cleanup.py`
- 修改：`apps/api/app/settings.py`
- 修改：`apps/api/tests/test_agents_settings.py`
- 新增：`apps/api/tests/test_lead_cleanup_http_active_run.py`
- 修改：`docs/stories/phase-4-small-run/P4-E4-S4-api-lead-cleanup-active-run.md`

## 两轮独立评审记录

### 第一轮独立评审：验收标准与业务边界复核

评审维度：

- 是否通过 `apps/api` 调用 `apps/agents` Lead Cleanup。
- 是否通过配置开关控制 HTTP active_run。
- 是否保留现有本地 Lead Cleanup 行为。
- 是否保存 `external_agent_run_id`。
- 清洗建议是否仍由 `apps/api` 写入待审核建议表。
- 是否避免自动归并、自动恢复 Invalid、自动删除数据或绕过人工确认。

结论：

- 初版实现满足成功路径和本地兼容路径，但发现一个需要修正的问题。

发现项：

- 新增配置开关只被 service 选择器测试覆盖，`apps/api` settings 合同测试尚未覆盖 `AGENT_LEAD_CLEANUP_HTTP_ACTIVE_ENABLED` 与 `VEHICLE_LEADS_AGENT_LEAD_CLEANUP_HTTP_ACTIVE_ENABLED`。

修正结果：

- 已在 `tests/test_agents_settings.py` 补充默认值、unprefixed alias、prefixed alias 三类断言。
- 修正后 `apps/api` 聚焦回归 33 passed。

### 第二轮独立评审：回归、联调与风控复核

评审维度：

- 是否破坏 P4-E3 HTTP runtime/client contract。
- 是否破坏 P4-E4-S2 `apps/agents` Lead Cleanup HTTP API。
- 是否保持 `apps/api` 和 `apps/agents` HTTP 服务边界，不做本地包注入。
- 是否保留人工审核和人工执行边界。
- 是否满足 Story 要求的服务间联调。

结论：

- 代码、合同测试和双服务测试通过；真实 socket 级服务间联调因当前环境禁止端口绑定未完成。

发现项：

- `uvicorn` 绑定 `127.0.0.1:18111` 失败，错误为 `operation not permitted`。该问题来自当前执行环境限制，不是应用代码测试失败。
- 当前 `apps/api/app/api/lead_cleanup.py` 没有创建 cleanup run 并触发 agent 的入口；本 Story 按现有边界只完成 service active_run 接入，未擅自新增 API 行为。

修正结果：

- 已记录验证限制。
- 已用 `apps/api` HTTP runtime contract tests、`apps/agents` FastAPI 测试和双方聚焦/全量测试作为替代验证证据。
- 第二轮未发现新增实质阻塞问题，当前 Story 可收口。
