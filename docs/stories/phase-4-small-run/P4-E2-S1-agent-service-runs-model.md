# Story P4-E2-S1：新增 agent_service_runs 模型与迁移

状态：已实现  
Sprint：Sprint 2  
优先级：P0  
Epic：P4-E2

## 用户故事

作为 Agent 服务开发者，我希望 `apps/agents` 拥有自己的 `agent_service_runs` 运行状态表，以便 Agent 执行事实源从 `apps/api.agent_task_runs` 逐步迁移出来。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 在 `apps/agents` 中创建 `agent_service_runs` 数据模型、迁移和 schema。

**建议文件：**

- Create: `apps/agents/app/models/agent_service_run.py`
- Create/Modify: `apps/agents/app/db/`
- Create/Modify: `apps/agents/alembic/versions/`
- Create: `apps/agents/app/schemas/agent_service_run.py`
- Test: `apps/agents/tests/test_agent_service_runs_model.py`

**验收标准：**

- `agent_service_runs` 包含 agent_type、agent_mode、status、request_id、trigger_source、input_json、output_json、audit_json、retry_count、max_retries、error_type、error_message、时间字段。
- 模型和 schema 字段一致。
- 迁移可生成 PostgreSQL DDL。
- 不创建或修改 core 业务表。

**非目标：**

- 不创建 `agent_service_node_runs`。
- 不实现重试 worker。

## Codex 提示词

```text
请执行 P4-E2-S1：新增 agent_service_runs 模型与迁移。
要求使用 TDD；表只归 apps/agents 管理；不得写 customers、lead_sources、contact_methods、staging_leads；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- `apps/agents` 只写 Agent 运行表。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。

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
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_agent_service_runs_model.py -q
```

第一次红灯暴露测试导入 `CreateTable` 的路径错误，已修正为 `from sqlalchemy.schema import CreateTable`。重新运行后，失败原因为本地 `apps/agents/app/models` 尚不存在，Python 解析到了环境中其他项目的 `app.models`，符合当前 Story 需要新增 `apps/agents` 自有模型包和数据库基础设施的预期。

绿灯：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_agent_service_runs_model.py -q
```

结果：`4 passed in 0.35s`。

### 实现摘要

- 新增 `apps/agents/app/db/base.py`，定义 `apps/agents` 自己的 SQLAlchemy `Base`。
- 新增 `apps/agents/app/db/types.py`，定义 PostgreSQL JSONB variant。
- 新增 `apps/agents/app/models/agent_service_run.py`，定义 `AgentServiceRun` 模型。
- 新增 `apps/agents/app/schemas/agent_service_run.py`，定义 `AgentServiceRunRead` schema。
- 新增 `apps/agents/alembic/script.py.mako`。
- 新增 `apps/agents/alembic/versions/20260605_0001_create_agent_service_runs.py`。
- 更新 `apps/agents/pyproject.toml`，声明 `sqlalchemy` 和 `alembic` 依赖。
- 未创建 `agent_service_node_runs`。
- 未实现重试 worker。
- 未创建或修改 `customers`、`lead_sources`、`contact_methods`、`staging_leads` 等 core 业务表。

### 字段覆盖

`agent_service_runs` 当前包含：

- `id`
- `request_id`
- `agent_type`
- `agent_mode`
- `status`
- `trigger_source`
- `input_json`
- `output_json`
- `output_summary_json`
- `audit_json`
- `retry_count`
- `max_retries`
- `next_retry_at`
- `error_type`
- `error_message`
- `started_at`
- `finished_at`
- `created_at`
- `updated_at`

### 验证命令

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_agent_service_runs_model.py -q
```

结果：`4 passed in 0.35s`。

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest -q
```

结果：`32 passed in 0.55s`。

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/python - <<'PY'
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql
from app.models.agent_service_run import AgentServiceRun
print(str(CreateTable(AgentServiceRun.__table__).compile(dialect=postgresql.dialect())))
PY
```

结果包含：

```text
CREATE TABLE agent_service_runs
JSONB
```

并未包含 `customers`、`lead_sources`、`contact_methods`、`staging_leads`。

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/python - <<'PY'
from app.models.agent_service_run import AgentServiceRun
from app.schemas.agent_service_run import AgentServiceRunRead
print(AgentServiceRun.__tablename__)
print(sorted(AgentServiceRun.__table__.columns.keys()))
print(sorted(AgentServiceRunRead.model_fields.keys()))
PY
```

结果：模型字段与 schema 字段一致。

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

### 第一轮评审：模型、schema、迁移和数据边界

结论：

- 通过。`agent_service_runs` 模型包含 Story 要求的 agent_type、agent_mode、status、request_id、trigger_source、input_json、output_json、audit_json、retry_count、max_retries、error_type、error_message 和时间字段。
- 通过。模型和 `AgentServiceRunRead` schema 字段一致。
- 通过。PostgreSQL DDL 可生成，并使用 JSONB 表达 JSON 字段。
- 通过。迁移只创建 `agent_service_runs`，未创建 `agent_service_node_runs`。
- 通过。未创建或修改 core 业务表。

发现项：

- 初始测试断言迁移文本时对换行格式过于敏感，导致误报。

修正结果：

- 已改为正则匹配 `op.create_table("agent_service_runs")` 的语义，避免格式变化导致误报。

### 第二轮评审：回归、架构独立性、后续可扩展性

结论：

- 通过。`apps/agents` 拥有独立 `db`、`models` 和 Alembic 目录，不复用 `apps/api` 模型。
- 通过。`apps/api` 可正常导入自身 `app.main`，未受 `apps/agents` 新增模型影响。
- 通过。`apps/agents` 全量测试通过：`32 passed in 0.55s`。
- 通过。当前只建立运行事实源表基础，没有实现重试 worker 或节点级表，符合非目标。
- 通过。`apps/agents` 仍未触达、晋级、归并或恢复 Invalid。

发现项：

- 当前迁移文件为 `apps/agents` 独立 Alembic 目录的首个 revision，尚未接入真实数据库迁移执行命令；后续 P4-E1-S4/P4-E2 后续 Story 或部署手册需要明确运行方式。

修正结果：

- 本 Story 保持在模型与迁移文件层面；迁移执行 runbook 后续在本地启动/部署或状态服务 Story 中补齐。
