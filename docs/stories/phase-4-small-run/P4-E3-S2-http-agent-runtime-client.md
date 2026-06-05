# Story P4-E3-S2：实现 HttpAgentRuntime HTTP 调用客户端

状态：已实现  
Sprint：Sprint 3  
优先级：P0  
Epic：P4-E3

## 用户故事

作为 `apps/api` 的 Agent 调用方，我希望有一个 `HttpAgentRuntime` 通过统一 envelope 调用 `apps/agents`，以便后续 active_run 和 shadow_run 都能走同一套服务间调用协议。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`
- `docs/brainstorm/brainstorming-session-2026-06-04-第四阶段小范围运行-LangGraph-Agent迁移.md`

## Story 定义

**目标：** 在 `apps/api` 中实现 HTTP Agent runtime client，负责鉴权 header、超时、错误映射和响应解析。

**建议文件：**

- Create: `apps/api/app/agents/http_runtime.py`
- Modify: `apps/api/app/agents/__init__.py`
- Test: `apps/api/tests/agents/test_http_agent_runtime.py`

**验收标准：**

- client 请求必须带 `X-Agents-Api-Key`。
- client 支持统一 request envelope 和 response envelope。
- 对 HTTP 401、4xx、5xx、timeout 有明确异常类型或错误返回。
- `apps/api` 不 import `apps/agents` 代码。
- 默认不替换现有本地 Agent runtime。

**非目标：**

- 不实现具体 Deep Enrichment 或 Lead Cleanup 方法适配。
- 不写入 `agent_task_runs`。
- 不实现结果轮询消费。

## Codex 提示词

```text
请执行 P4-E3-S2：实现 HttpAgentRuntime HTTP 调用客户端。
要求使用 TDD；覆盖成功、鉴权失败、服务错误和超时；不得 import apps/agents；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- `apps/api` 中现有 LLM Agent 保持不变。
- `apps/agents` 独立服务运行，通过 HTTP API 交互。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。

## 执行记录

执行日期：2026-06-05  
执行方式：按 `docs/superpowers/plans/2026-06-05-海外车辆采购AI获客系统-第四阶段小范围运行LangGraph-Agent迁移推进计划.md` 执行当前 Story。

### Git / Worktree 记录

- 延续当前环境事实：沙箱禁止写 `.git/FETCH_HEAD` 和 `.git/refs/heads/*.lock`。
- 无法在本环境完成 `git fetch`、创建分支和 worktree。
- 按当前目标的 sandbox fallback，在当前工作区继续执行本 Story。
- 未执行 git 提交。

### TDD 记录

红灯：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/agents/test_http_agent_runtime.py -q
```

结果：失败，原因是 `ModuleNotFoundError: No module named 'app.agents'`，符合当前 Story 需要新增 HTTP Agent runtime client 的预期。

绿灯：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/agents/test_http_agent_runtime.py -q
```

结果：`6 passed in 0.08s`。

第一轮评审补充测试后发现：

- 初版 client 会解析 JSON，但没有校验响应是否真的是第四阶段统一 response envelope。
- 这会导致任意 JSON 被误认为成功 Agent run 响应。

修正：

- 新增 `test_http_agent_runtime_rejects_invalid_response_envelope`。
- `HttpAgentRuntime` 增加响应 envelope 最小校验：`schema_version` 必须为 `phase4.agent.run.v1`，并且必须包含 `agent_service_run_id`、`request_id`、`status`。

修正后绿灯：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/agents/test_http_agent_runtime.py -q
```

结果：`7 passed in 0.33s`。

### 实现摘要

- 新增 `apps/api/app/agents/__init__.py`。
- 新增 `apps/api/app/agents/http_runtime.py`。
- 新增 `HttpAgentRuntime`。
- 请求统一发送到 `{AGENTS_BASE_URL}/agent-runs/{agent_endpoint}`。
- 请求 header 包含 `X-Agents-Api-Key`。
- 请求 body 使用第四阶段统一 request envelope：`request_id`、`agent_task_run_id`、`trigger_source`、`agent_mode`、`input`、`options`。
- 响应必须是第四阶段统一 response envelope。
- 未配置 `AGENTS_API_KEY` 时抛 `HttpAgentRuntimeConfigurationError`，且不发起 HTTP 请求。
- HTTP 401 映射为 `HttpAgentRuntimeAuthError`。
- HTTP 4xx 映射为 `HttpAgentRuntimeValidationError`。
- HTTP 5xx 映射为 `HttpAgentRuntimeServerError`。
- timeout 映射为 `HttpAgentRuntimeTimeoutError`。
- 非 JSON 或无效 response envelope 映射为 `HttpAgentRuntimeValidationError`。
- 未实现 Deep Enrichment 或 Lead Cleanup 方法适配。
- 未写入 `agent_task_runs`。
- 未实现结果轮询消费。
- 未替换现有本地 Agent runtime。
- 未 import `apps/agents` 代码。

### 验证命令

当前 Story 测试：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/agents/test_http_agent_runtime.py -q
```

结果：`7 passed in 0.33s`。

`apps/api` 聚焦回归：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/agents/test_http_agent_runtime.py tests/test_agents_settings.py tests/test_llm_settings.py tests/test_llm_client.py -q
```

结果：`18 passed in 0.47s`。

`apps/api` 导入检查：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/python - <<'PY'
from app.main import app
from app.agents import HttpAgentRuntime
print(app.title)
print(len(app.routes) > 0)
print(HttpAgentRuntime.__name__)
PY
```

执行目录：`apps/api`  
结果：

```text
Overseas Vehicle Leads AI API
True
HttpAgentRuntime
```

`apps/agents` 回归：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest -q
```

执行目录：`apps/agents`  
结果：`49 passed in 0.58s`。

## 两轮独立评审记录

### 第一轮评审：协议、错误映射和服务边界

结论：

- 通过。client 请求会携带 `X-Agents-Api-Key`。
- 通过。client 支持统一 request envelope 和 response envelope。
- 通过。HTTP 401、4xx、5xx、timeout 都有明确异常类型。
- 通过。`apps/api` 没有 import `apps/agents` 代码。
- 通过。默认没有替换现有本地 Agent runtime。

发现项：

- 初版 client 只验证响应为 JSON，没有校验第四阶段 response envelope。

修正结果：

- 已新增无效 response envelope 测试。
- 已补充 `schema_version=phase4.agent.run.v1` 和核心字段校验。

### 第二轮评审：回归风险、安全和可维护性

结论：

- 通过。`HttpAgentRuntime` 是独立新增模块，未接入现有 Deep Enrichment、Lead Cleanup 或 Source Discovery 执行入口。
- 通过。未配置 `AGENTS_API_KEY` 时不发起 HTTP 请求，避免静默降级或匿名调用。
- 通过。异常类型保留 `status_code` 和 `response_json`，便于后续日志和兼容摘要记录。
- 通过。`apps/api` 聚焦回归通过：`18 passed in 0.47s`。
- 通过。`apps/api` 导入检查通过。
- 通过。`apps/agents` 回归通过：`49 passed in 0.58s`。

发现项：

- 当前 Story 只实现通用 `run_agent`，尚未提供 `run_deep_enrichment`、`run_lead_cleanup` 等兼容方法。

修正结果：

- 无需在本 Story 扩展；具体方法适配属于后续 `P4-E3-S3`。
