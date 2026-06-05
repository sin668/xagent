# Story P4-E2-S2：实现 Agent run 创建、状态流转和失败记录

状态：已实现  
Sprint：Sprint 2  
优先级：P0  
Epic：P4-E2

## 用户故事

作为 Agent 服务开发者，我希望 `apps/agents` 能创建 run、更新状态并记录失败，以便它成为 LangGraph Agent 执行事实源。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 实现 `agent_service_runs` 的创建、状态流转、失败记录和查询服务。

**建议文件：**

- Create: `apps/agents/app/services/agent_service_runs.py`
- Modify: `apps/agents/app/schemas/agent_service_run.py`
- Test: `apps/agents/tests/test_agent_run_state_service.py`

**验收标准：**

- 支持创建 pending run。
- 支持状态流转到 running、retrying、succeeded、failed、blocked、cancelled。
- 失败记录包含 `error_type` 和 `error_message`。
- 状态流转更新 `started_at`、`finished_at`、`updated_at`。
- 非法状态流转被拒绝或显式处理。

**非目标：**

- 不实现具体 Agent API。
- 不实现重试调度。

## Codex 提示词

```text
请执行 P4-E2-S2：实现 Agent run 创建、状态流转和失败记录。
要求使用 TDD；apps/agents 是 Agent 执行事实源；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- 不写 core 业务表。
- 不隐藏失败原因。

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
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_agent_run_state_service.py -q
```

结果：失败，原因是 `ModuleNotFoundError: No module named 'app.services.agent_service_runs'`，符合当前 Story 需要新增 Agent run 状态服务的预期。

实现后的第一次运行发现：

- 使用 PostgreSQL 方言 `UUID` 类型的模型在 SQLite 内存测试中反序列化 UUID 失败。
- 根因是模型直接使用 `sqlalchemy.dialects.postgresql.UUID`，不适合跨方言 service 单元测试。
- 修正为 SQLAlchemy 跨方言 `Uuid(as_uuid=True)`；PostgreSQL DDL 仍生成 `UUID`，SQLite 测试使用 `CHAR(32)`。

绿灯：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_agent_run_state_service.py -q
```

结果：`6 passed in 0.26s`。

### 实现摘要

- 新增 `apps/agents/app/services/agent_service_runs.py`。
- 新增 `AgentServiceRunService`。
- 支持创建 pending run。
- 支持查询 run。
- 支持状态流转到 `running`、`retrying`、`succeeded`、`failed`、`blocked`、`cancelled`。
- 失败和阻断记录 `error_type`、`error_message`。
- 状态流转更新 `started_at`、`finished_at`、`updated_at`。
- 终态 `succeeded`、`failed`、`blocked`、`cancelled` 后继续流转会抛出 `InvalidAgentRunTransition`。
- 未实现具体 Agent API。
- 未实现重试调度。
- 未写 core 业务表。

### 验证命令

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_agent_run_state_service.py -q
```

结果：`6 passed in 0.26s`。

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest -q
```

结果：`38 passed in 0.58s`。

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/python - <<'PY'
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.services.agent_service_runs import AgentServiceRunService
engine = create_engine('sqlite:///:memory:')
Base.metadata.create_all(engine)
session = sessionmaker(bind=engine)()
service = AgentServiceRunService(session)
run = service.create_run(request_id='11111111-1111-1111-1111-111111111111', agent_type='deep_enrichment', agent_mode='active', trigger_source='manual_api', input_json={})
print(run.status)
print(service.mark_running(run.id).status)
print(service.mark_failed(run.id, error_type='timeout_error', error_message='timeout').status)
print(service.get_run(run.id).error_type, service.get_run(run.id).error_message)
session.close()
engine.dispose()
PY
```

结果：

```text
pending
running
failed
timeout_error timeout
```

跨方言 UUID 验证：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/python - <<'PY'
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql, sqlite
from app.models.agent_service_run import AgentServiceRun
print(str(CreateTable(AgentServiceRun.__table__).compile(dialect=postgresql.dialect())).splitlines()[2].strip())
print(str(CreateTable(AgentServiceRun.__table__).compile(dialect=sqlite.dialect())).splitlines()[2].strip())
PY
```

结果：

```text
id UUID NOT NULL,
id CHAR(32) NOT NULL,
```

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

### 第一轮评审：状态服务与验收标准

结论：

- 通过。支持创建 pending run。
- 通过。支持流转到 `running`、`retrying`、`succeeded`、`failed`、`blocked`、`cancelled`。
- 通过。失败记录包含 `error_type` 和 `error_message`。
- 通过。状态流转更新 `started_at`、`finished_at`、`updated_at`。
- 通过。终态后继续流转会显式拒绝。
- 通过。未实现具体 Agent API 或重试调度。

发现项：

- 直接使用 PostgreSQL 方言 UUID 类型会导致 SQLite service 单元测试失败。

修正结果：

- 已改为 SQLAlchemy 跨方言 `Uuid(as_uuid=True)`，同时保留 PostgreSQL DDL 的 `UUID` 表达。

### 第二轮评审：边界、回归、可运维性

结论：

- 通过。`apps/agents` 作为 Agent 执行事实源的 service 基础已建立。
- 通过。当前 service 只操作 `agent_service_runs` 模型，不写 core 业务表。
- 通过。失败原因没有被隐藏，`error_type` 和 `error_message` 可查询。
- 通过。`apps/agents` 全量测试通过：`38 passed in 0.58s`。
- 通过。`apps/api` 可正常导入自身 `app.main`，未受影响。

发现项：

- 当前 service 仍为同步 SQLAlchemy Session 版本，后续接入 FastAPI endpoint 时需按项目实际 session 管理方式封装。

修正结果：

- 无需在本 Story 扩展；API 接入和 session 生命周期属于后续 Agent Run API Story。
