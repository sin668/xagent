# Story P4-E2-S4：将节点 trace 摘要写入 audit_json.executed_nodes

状态：已实现  
Sprint：Sprint 2  
优先级：P1  
Epic：P4-E2

## 用户故事

作为运维和研发排障人员，我希望每次 LangGraph 运行都记录节点级摘要，以便定位失败节点、耗时和风险 flags。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 设计并实现 `audit_json.executed_nodes` 的稳定结构。

**建议文件：**

- Create/Modify: `apps/agents/app/schemas/trace.py`
- Modify: `apps/agents/app/services/agent_service_runs.py`
- Test: `apps/agents/tests/test_agent_node_trace_summary.py`

**验收标准：**

- 节点摘要包含 node、status、duration_ms、input_summary、output_summary、error。
- run 摘要包含 failed_node、risk_flags、source_urls、writes_core_tables。
- 失败 case 至少记录 failed_node、error_type、retryable。
- 第四阶段不强制新增 `agent_service_node_runs` 表。

**非目标：**

- 不实现外部 trace 平台。
- 不实现 LangSmith 集成。

## Codex 提示词

```text
请执行 P4-E2-S4：将节点 trace 摘要写入 audit_json.executed_nodes。
要求使用 TDD；保持结构稳定，便于后续迁移到 agent_service_node_runs；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- trace 不得包含 API Key 或敏感密钥。
- trace 不得记录非公开数据全文。

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
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_agent_node_trace_summary.py -q
```

结果：失败，原因是 `ModuleNotFoundError: No module named 'app.schemas.trace'`，符合当前 Story 需要新增 trace schema 的预期。

实现后的第一次运行：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_agent_node_trace_summary.py -q
```

结果：`5 passed in 0.34s`。

第一轮评审补充测试后发现：

- `audit_json` 未来可能已包含 graph 侧扩展字段，例如 `output_table`、`llm_provider`。
- 初版 service 直接用 `AgentRunTraceAudit(extra="forbid")` 解析完整 `audit_json`，会拒绝已有扩展字段。

修正：

- 新增 `test_trace_updates_preserve_existing_audit_metadata`。
- service 解析 trace audit 时只读取 trace 已知字段。
- 写回时将 trace 字段合并回原始 `audit_json`，保留已有审计元数据。

绿灯：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_agent_node_trace_summary.py -q
```

结果：`6 passed in 0.24s`。

### 实现摘要

- 新增 `apps/agents/app/schemas/trace.py`。
- 新增 `AgentNodeTrace`，稳定字段包含 `node`、`status`、`duration_ms`、`input_summary`、`output_summary`、`error`。
- 新增 `AgentNodeTraceError`，字段包含 `error_type`、`message`、`retryable`。
- 新增 `AgentRunTraceAudit`，字段包含 `writes_core_tables`、`executed_nodes`、`failed_node`、`risk_flags`、`source_urls`。
- trace schema 会拒绝 `writes_core_tables=True`。
- trace summary 会对 `api_key`、`authorization`、`cookie`、`password`、`secret`、`token` 等敏感 key 做 `[REDACTED]`。
- `AgentServiceRunService` 新增 `append_node_trace`。
- `AgentServiceRunService` 新增 `update_trace_summary`。
- `AgentServiceRunService` 新增 `record_failed_node_trace`。
- trace 写入会保留 `audit_json` 里已有的扩展审计元数据。
- `apps/agents/app/schemas/__init__.py` 导出 trace schema。
- 未新增 `agent_service_node_runs` 表。
- 未实现外部 trace 平台。
- 未实现 LangSmith 集成。

### 验证命令

当前 Story 测试：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_agent_node_trace_summary.py -q
```

结果：`6 passed in 0.24s`。

`apps/agents` 全量测试：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest -q
```

结果：`49 passed in 0.53s`。

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

### 第一轮评审：验收标准、数据边界和风控

结论：

- 通过。节点摘要包含 `node`、`status`、`duration_ms`、`input_summary`、`output_summary`、`error`。
- 通过。run 摘要包含 `failed_node`、`risk_flags`、`source_urls`、`writes_core_tables`。
- 通过。失败 case 至少记录 `failed_node`、`error_type`、`retryable`。
- 通过。没有新增 `agent_service_node_runs` 表。
- 通过。没有实现外部 trace 平台或 LangSmith 集成。
- 通过。敏感 key 会被 `[REDACTED]`，避免记录 API Key 或密钥。

发现项：

- 初版 trace 写入会用严格 schema 解析完整 `audit_json`，对已有扩展字段不兼容。

修正结果：

- 已新增保留已有 audit 元数据的测试。
- 已修正 service 的 trace audit 解析和合并逻辑，只校验 trace 字段，同时保留原始 `audit_json` 的扩展字段。

### 第二轮评审：回归风险、可维护性和后续迁移

结论：

- 通过。`apps/agents` 全量测试通过：`49 passed in 0.53s`。
- 通过。`apps/api` 可正常导入自身 `app.main`，现有 API agent 行为未被改动。
- 通过。trace 写入集中在 `AgentServiceRunService`，后续 HTTP API 和 LangGraph runner 可复用。
- 通过。trace 结构足够稳定，后续可迁移到 `agent_service_node_runs` 表。
- 通过。当前实现只写 `agent_service_runs.audit_json`，未写 core 业务表。

发现项：

- trace schema 初版可通过 `app.schemas.trace` 直接导入，但未加入 `app.schemas` 命名空间导出。

修正结果：

- 已在 `apps/agents/app/schemas/__init__.py` 导出 `AgentNodeTrace`、`AgentNodeTraceError`、`AgentRunTraceAudit`。
