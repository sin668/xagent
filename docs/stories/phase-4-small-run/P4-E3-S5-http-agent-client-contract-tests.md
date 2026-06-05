# Story P4-E3-S5：HTTP Agent client contract tests

状态：已实现  
Sprint：Sprint 3  
优先级：P0  
Epic：P4-E3

## 用户故事

作为跨服务调用的维护者，我希望用 contract tests 固化 `apps/api` 与 `apps/agents` 的 HTTP 协议，以便后续 LangGraph Agent 迭代不会破坏调用兼容性。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 建立 HTTP Agent client 契约测试，覆盖成功、失败、鉴权失败和超时。

**建议文件：**

- Create: `apps/api/tests/contracts/test_http_agent_client_contract.py`
- Create/Modify: `apps/api/tests/fixtures/`
- Modify: `apps/api/app/agents/http_runtime.py`

**验收标准：**

- contract tests 覆盖 2xx 成功 envelope。
- contract tests 覆盖 401 鉴权失败。
- contract tests 覆盖 4xx/5xx 业务或服务错误。
- contract tests 覆盖请求超时。
- 测试不得依赖真实外部 LLM 调用。

**非目标：**

- 不要求启动真实 `apps/agents` 服务。
- 不做端到端业务联调。
- 不扩大 Agent 迁移范围。

## Codex 提示词

```text
请执行 P4-E3-S5：HTTP Agent client contract tests。
要求使用 TDD；用 mock server 或等价方式覆盖成功、失败、鉴权失败、超时；不得发起真实 LLM 调用；完成后执行两轮独立评审。
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
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/contracts/test_http_agent_client_contract.py -q
```

结果：`5 passed, 1 failed`。失败项为 `test_contract_rejects_success_envelope_that_claims_core_table_writes`，原因是 `HttpAgentRuntime` 初版会接受 `audit.writes_core_tables=true` 的成功 envelope。

修正：

- 在 `HttpAgentRuntime._validate_response_envelope` 中补充 `audit.writes_core_tables is False` 校验。
- `apps/agents` 返回声明写 core 表的成功响应时，`apps/api` client 会抛 `HttpAgentRuntimeValidationError`。

绿灯：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/contracts/test_http_agent_client_contract.py -q
```

结果：`6 passed in 0.09s`。

### 实现摘要

- 新增 `apps/api/tests/fixtures/http_agent_contracts.py`。
- 新增 `apps/api/tests/contracts/test_http_agent_client_contract.py`。
- contract tests 覆盖 2xx 成功 envelope 和请求契约。
- contract tests 覆盖 `X-Agents-Api-Key` header。
- contract tests 覆盖 HTTP 401 鉴权失败。
- contract tests 覆盖 HTTP 4xx 业务/请求错误。
- contract tests 覆盖 HTTP 5xx 服务错误。
- contract tests 覆盖请求 timeout。
- contract tests 使用 `httpx.MockTransport`，不启动真实 `apps/agents` 服务。
- contract tests 不发起真实 LLM 调用。
- 补强 `HttpAgentRuntime`：成功 response envelope 中 `audit.writes_core_tables` 必须为 `False`。
- 未做端到端业务联调。
- 未扩大 Agent 迁移范围。

### 验证命令

当前 Story 测试：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/contracts/test_http_agent_client_contract.py -q
```

结果：`6 passed in 0.09s`。

`apps/api` 聚焦回归：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/contracts/test_http_agent_client_contract.py tests/agents/test_http_agent_runtime.py tests/agents/test_http_runtime_compatibility.py tests/agents/test_agent_task_run_external_summary.py tests/test_agents_settings.py tests/test_llm_settings.py tests/test_llm_client.py -q
```

结果：`31 passed in 0.55s`。

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
结果：`49 passed in 0.52s`。

## 两轮独立评审记录

### 第一轮评审：契约覆盖、边界和非目标

结论：

- 通过。contract tests 覆盖 2xx 成功 envelope。
- 通过。contract tests 覆盖 401 鉴权失败。
- 通过。contract tests 覆盖 4xx 业务/请求错误。
- 通过。contract tests 覆盖 5xx 服务错误。
- 通过。contract tests 覆盖请求 timeout。
- 通过。测试使用 `httpx.MockTransport`，不依赖真实 `apps/agents` 服务。
- 通过。测试没有真实 LLM 调用。
- 通过。未做端到端业务联调，未扩大 Agent 迁移范围。

发现项：

- 初版 `HttpAgentRuntime` 对成功 envelope 只校验 schema 和核心字段，没有拒绝 `audit.writes_core_tables=true`。

修正结果：

- 已补充契约测试覆盖该场景。
- 已补强 runtime 校验，`audit.writes_core_tables` 不是 `False` 时抛 `HttpAgentRuntimeValidationError`。

### 第二轮评审：回归风险、安全和可维护性

结论：

- 通过。新增 contract fixture 可复用，后续可继续沉淀更多跨服务协议样例。
- 通过。`apps/api` 聚焦回归通过：`31 passed in 0.55s`。
- 通过。`apps/api` 导入检查通过。
- 通过。`apps/agents` 回归通过：`49 passed in 0.52s`。
- 通过。现有 LLM Agent 行为未被替换或接入。
- 通过。契约测试未记录 API Key 明文以外的敏感 payload；测试 key 是本地假值。

发现项：

- 当前 contract tests 仍是 mock server 级别，不验证真实 `apps/agents` 启动后的路由行为。

修正结果：

- 无需在本 Story 扩展；真实服务联调属于后续 active_run / 端到端联调 Story。
