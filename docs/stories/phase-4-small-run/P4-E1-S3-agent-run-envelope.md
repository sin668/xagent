# Story P4-E1-S3：定义统一 Agent Run request / response envelope

状态：已实现  
Sprint：Sprint 1  
优先级：P0  
Epic：P4-E1

## 用户故事

作为 API 与 Agent 服务集成开发者，我希望所有 Agent Run API 使用统一 request / response envelope，以便 `apps/api` 可以稳定调用、校验和记录兼容摘要。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 定义 `phase4.agent.run.v1` 的请求和响应 schema。

**建议文件：**

- Create: `apps/agents/app/schemas/agent_run.py`
- Modify: `apps/agents/app/schemas/__init__.py`
- Test: `apps/agents/tests/test_agent_run_envelope.py`

**验收标准：**

- Request 包含 `request_id`、`agent_task_run_id`、`trigger_source`、`agent_mode`、`input`、`options`。
- Response 包含 `schema_version`、`agent_service_run_id`、`request_id`、`status`、`agent_type`、`agent_mode`、`output`、`audit`、`error`。
- status 支持 `succeeded`、`failed`、`blocked`、`running`、`retrying`。
- schema 可被 OpenAPI 正确展示。

**非目标：**

- 不实现具体 Agent endpoint。
- 不实现数据库状态存储。

## Codex 提示词

```text
请执行 P4-E1-S3：定义统一 Agent Run request / response envelope。
要求使用 Pydantic schema 和 TDD；不得实现具体 Agent 业务逻辑；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- envelope 必须保留 `writes_core_tables=false` 的审计表达能力。
- 任何 Agent 输出都不得绕过 `apps/api` 业务校验。

## 执行记录

执行日期：2026-06-05  
执行方式：按 `docs/superpowers/plans/2026-06-05-海外车辆采购AI获客系统-第四阶段小范围运行LangGraph-Agent迁移推进计划.md` 执行当前 Story。

### Git / Worktree 记录

- 延续当前环境事实：沙箱禁止写 `.git/FETCH_HEAD` 和 `.git/refs/heads/*.lock`。
- 无法在本环境完成 `git fetch`、创建分支和 worktree。
- 按 `superpowers:using-git-worktrees` 的 sandbox fallback，在当前工作区继续执行本 Story。
- 未执行 git 提交。

### TDD 记录

红灯：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_agent_run_envelope.py -q
```

结果：失败，原因是 `ModuleNotFoundError: No module named 'app.schemas.agent_run'`，符合当前 Story 需要新增 `phase4.agent.run.v1` envelope schema 的预期。

绿灯：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_agent_run_envelope.py -q
```

结果：`5 passed in 0.21s`。

### 实现摘要

- 新增 `apps/agents/app/schemas/agent_run.py`。
- 定义 `AGENT_RUN_SCHEMA_VERSION = "phase4.agent.run.v1"`。
- 定义 `AgentRunRequest`，包含 `request_id`、`agent_task_run_id`、`trigger_source`、`agent_mode`、`input`、`options`。
- 定义 `AgentRunResponse`，包含 `schema_version`、`agent_service_run_id`、`request_id`、`status`、`agent_type`、`agent_mode`、`output`、`audit`、`error`。
- 定义 `AgentRunOptions`、`AgentRunAudit`、`AgentRunError`。
- `AgentRunAudit.writes_core_tables` 默认值为 `False`，且显式拒绝 `True`。
- `status` 支持 `pending`、`running`、`retrying`、`succeeded`、`failed`、`blocked`、`cancelled`，其中覆盖 Story 要求的 `succeeded`、`failed`、`blocked`、`running`、`retrying`。
- 更新 `apps/agents/app/schemas/__init__.py` 导出 envelope schema。
- 未实现具体 Agent endpoint。
- 未实现数据库状态存储。

### 验证命令

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_health_api.py tests/test_internal_api_key_auth.py tests/test_agent_run_envelope.py -q
```

结果：`11 passed in 0.25s`。

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest -q
```

结果：`28 passed in 0.25s`。

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/python - <<'PY'
from app.schemas.agent_run import AgentRunResponse
print(AgentRunResponse.model_json_schema()['title'])
print(sorted(AgentRunResponse.model_json_schema()['properties'].keys()))
PY
```

结果：

```text
AgentRunResponse
['agent_mode', 'agent_service_run_id', 'agent_type', 'audit', 'error', 'output', 'request_id', 'schema_version', 'status']
```

OpenAPI 验证：

- `tests/test_agent_run_envelope.py::test_agent_run_schema_is_visible_in_openapi` 已验证 `AgentRunRequest` 与 `AgentRunResponse` 可出现在 OpenAPI components schemas 中。

`apps/api` 回归导入检查：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/python - <<'PY'
from app.main import app
print(app.title)
print(len(app.routes) > 0)
PY
```

执行目录：`apps/api`  
结果：

```text
Overseas Vehicle Leads AI API
True
```

## 两轮独立评审记录

### 第一轮评审：需求、schema、OpenAPI

结论：

- 通过。Request 已包含 Story 要求的全部字段。
- 通过。Response 已包含 Story 要求的全部字段。
- 通过。status 已支持 `succeeded`、`failed`、`blocked`、`running`、`retrying`。
- 通过。schema 可被 OpenAPI 正确展示。
- 通过。`writes_core_tables=false` 有默认表达，并拒绝设置为 `true`。

发现项：

- 产品技术设计中响应 status 示例未列出 `running`，但同步/异步策略和 Story 明确要求支持 `running`。当前实现支持 `running`，并额外保留 `pending`、`cancelled` 以匹配运行状态表设计。

修正结果：

- 无需修正；额外状态与产品技术设计第 7 节运行状态字段一致，不扩大业务行为。

### 第二轮评审：边界、回归、可维护性

结论：

- 通过。当前实现仅新增 Pydantic schema，没有实现具体 Agent endpoint 或数据库状态存储。
- 通过。未修改 `apps/api`，`apps/api` 可正常导入自身 `app.main`。
- 通过。`apps/agents` 全量测试通过：`28 passed in 0.25s`。
- 通过。schema 使用 `extra="forbid"`，可减少 contract 漂移风险。
- 通过。任何 Agent 输出仍需后续由 `apps/api` 业务校验消费，当前 Story 没有绕过业务校验。

发现项：

- 未发现新增实质阻塞问题。

修正结果：

- 无需修正。
