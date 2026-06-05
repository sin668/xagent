# Story P4-E3-S6：实现 Agent run 查询结果消费

状态：已实现  
Sprint：Sprint 3  
优先级：P1  
Epic：P4-E3

## 用户故事

作为 `apps/api` 的上层业务流程，我希望能通过 `external_agent_run_id` 查询 `apps/agents` 的最终结果，以便异步或重试中的 Agent run 能在完成后被安全消费。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 在 `HttpAgentRuntime` 中实现 `GET /agent-runs/{id}` 查询消费，支持 `running`、`retrying`、`succeeded`、`failed` 状态。

**建议文件：**

- Modify: `apps/api/app/agents/http_runtime.py`
- Modify: `apps/api/app/services/`
- Test: `apps/api/tests/agents/test_agent_run_result_consumption.py`

**验收标准：**

- 可通过 `external_agent_run_id` 查询 run 当前状态和最终输出。
- `running` / `retrying` 不被误判为失败。
- `succeeded` 时返回可被上层 service 使用的结构化输出。
- `failed` 时保留错误类型、错误消息和是否可重试信息。

**非目标：**

- 不实现轮询 worker。
- 不删除 `apps/api` retry worker。
- 不写入 core 业务表。

## Codex 提示词

```text
请执行 P4-E3-S6：实现 Agent run 查询结果消费。
要求使用 TDD；支持 running/retrying/succeeded/failed；不得让 apps/api 成为 Agent run 事实源；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- `apps/api.agent_task_runs` 第四阶段只做兼容摘要。
- `apps/agents` 是 Agent 执行事实源。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。

## 实施记录

### 实现内容

- 在 `apps/api/app/agents/http_runtime.py` 中新增 `HttpAgentRuntime.get_agent_run(external_agent_run_id)`。
- 通过 `GET {AGENTS_BASE_URL}/agent-runs/{external_agent_run_id}` 查询 `apps/agents` 的 Agent run 结果。
- 查询请求继续使用 `X-Agents-Api-Key`，未配置 `AGENTS_API_KEY` 时不发起 HTTP 请求。
- 复用统一 response envelope 校验，继续要求 `schema_version=phase4.agent.run.v1` 且 `audit.writes_core_tables=false`。
- 为查询消费结果补充：
  - `is_terminal`
  - `is_success`
  - `is_failure`
  - `error_type`
  - `error_message`
  - `retryable`
- `running` / `retrying` 返回非终态消费结果，不误判为失败。
- `succeeded` 必须携带结构化 `output`，供上层 service 后续消费。
- `failed` / `blocked` / `cancelled` 必须携带结构化 `error`，保留错误类型、错误消息和是否可重试信息。

### TDD 记录

- RED：先新增 `apps/api/tests/agents/test_agent_run_result_consumption.py`，初次运行 7 个用例因 `HttpAgentRuntime` 缺少 `get_agent_run` 失败。
- GREEN：实现 `get_agent_run` 和消费结果转换后，新测试 7 passed。
- 第一轮评审发现 `failed` 状态缺失结构化 `error` 时仍会被接受，补充失败测试并确认先失败。
- REFACTOR/FIX：收紧失败类终态校验，最终 Story 测试 8 passed。

### 验证结果

- `apps/api` Story 测试：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/agents/test_agent_run_result_consumption.py -q`
  - 结果：8 passed
- `apps/api` 聚焦回归：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/contracts/test_http_agent_client_contract.py tests/agents/test_http_agent_runtime.py tests/agents/test_http_runtime_compatibility.py tests/agents/test_agent_run_result_consumption.py tests/agents/test_agent_task_run_external_summary.py tests/test_agents_settings.py tests/test_llm_settings.py tests/test_llm_client.py -q`
  - 结果：39 passed
- `apps/agents` 全量测试：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest -q`
  - 结果：49 passed
- `apps/api` 导入检查：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/python - <<'PY' ...`
  - 结果：`Overseas Vehicle Leads AI API`，`True`

### 服务联调说明

- 本 Story 属于 `apps/api` 到 `apps/agents` 的 HTTP client 消费契约实现，已使用 `httpx.MockTransport` 做服务间 HTTP 请求/响应契约验证。
- 未启动真实 `apps/agents` 服务，未调用真实 LLM，未实现轮询 worker，未写入 core 业务表，符合本 Story 非目标。

## 文件清单

- 修改：`apps/api/app/agents/http_runtime.py`
- 新增：`apps/api/tests/agents/test_agent_run_result_consumption.py`
- 修改：`docs/stories/phase-4-small-run/P4-E3-S6-agent-run-result-consumption.md`

## 两轮独立评审记录

### 第一轮独立评审：契约与验收标准复核

评审维度：

- 是否通过 HTTP GET 查询 `apps/agents`，而不是本地包注入。
- 是否保持 `apps/agents` 为 Agent run 事实源。
- 是否覆盖 `running`、`retrying`、`succeeded`、`failed`。
- 是否保留失败态的错误类型、错误消息和是否可重试信息。
- 是否未写入 core 业务表、未实现轮询 worker、未删除 `apps/api` retry worker。

结论：

- 基本通过，但发现一个需要修正的问题。

发现项：

- `failed` 状态如果缺失结构化 `error`，初版实现仍会返回消费结果，无法满足“保留错误类型、错误消息和是否可重试信息”的验收标准。

修正结果：

- 新增 `test_get_agent_run_rejects_failed_without_structured_error`，先确认失败。
- 在 `_agent_run_consumption_result` 中收紧失败类终态校验：`failed` / `blocked` / `cancelled` 必须包含结构化 `error`。
- 修正后 Story 测试 8 passed，聚焦回归 39 passed。

### 第二轮独立评审：回归、边界与风控复核

评审维度：

- 是否破坏 P4-E3-S2 / S3 / S5 已建立的 HTTP runtime 和 contract tests。
- 是否继续校验 `audit.writes_core_tables=false`。
- 是否对 `running` / `retrying` 保持非终态、非失败语义。
- 是否避免新增数据库迁移、业务表写入和生产入口切换。
- 是否满足第四阶段小范围运行边界。

结论：

- 通过。未发现新增实质阻塞问题。

发现项：

- 未发现新增实质阻塞问题。

修正结果：

- 无需进一步修正。
