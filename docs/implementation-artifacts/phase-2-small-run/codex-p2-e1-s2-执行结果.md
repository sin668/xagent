# P2-E1-S2 执行结果：创建 `agent_task_runs` 数据表、模型和状态机 schema

执行日期：2026-06-02  
Story 文件：`docs/stories/phase-2-small-run/P2-E1-S2-agent-task-runs-state-machine.md`  
状态：Done

## 1. 执行范围

本次只执行 P2-E1-S2，不执行下一个 Story。

已完成：

- 创建 `agent_task_runs` Alembic migration。
- 创建 `AgentTaskRun` SQLAlchemy model。
- 创建 `AgentTaskRunCreate`、`AgentTaskRunUpdate`、`AgentTaskRunResponse`、`AgentTaskRunListResponse` Pydantic schema。
- 新增 `AgentTaskType` 和 `AgentTaskRunStatus` 枚举。
- 实现 `AgentTaskRunService` 的基础状态机方法。
- 测试覆盖合法状态流转、非法状态流转和最大重试次数。

未执行：

- 未实现 APScheduler。
- 未实现 Redis lock。
- 未实现 LLMClient。
- 未实现 Source Discovery Agent。
- 未实现 `LEAD_EXTRACTION` 消费。
- 未执行 P2-E1-S3 或其他 Story。

## 2. 修改文件

- `apps/api/alembic/versions/20260602_0021_create_agent_task_runs.py`
- `apps/api/app/models/agent_task_run.py`
- `apps/api/app/schemas/agent_task_run.py`
- `apps/api/app/services/agent_task_runs.py`
- `apps/api/app/models/enums.py`
- `apps/api/app/models/__init__.py`
- `apps/api/tests/test_agent_task_run_model.py`
- `docs/stories/phase-2-small-run/P2-E1-S2-agent-task-runs-state-machine.md`

## 3. TDD 记录

RED：

- 先创建 `apps/api/tests/test_agent_task_run_model.py`。
- 首次运行 `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_agent_task_run_model.py -q`。
- 结果：失败，原因是 `AgentTaskRunStatus` 和 `AgentTaskType` 尚不存在。

GREEN：

- 新增枚举、模型、schema、service 和 migration。
- 运行目标测试，通过。
- 修正模型注册和 timezone-aware 时间生成后重新验证。

## 4. 验证命令与结果

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_agent_task_run_model.py apps/api/tests/test_llm_prompt_template_model.py -q
```

结果：

```text
12 passed in 0.36s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/models/agent_task_run.py apps/api/app/schemas/agent_task_run.py apps/api/app/services/agent_task_runs.py apps/api/alembic/versions/20260602_0021_create_agent_task_runs.py apps/api/tests/test_agent_task_run_model.py
```

结果：通过，退出码 0。

```bash
cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic heads
```

结果：

```text
20260602_0021 (head)
```

```bash
cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic upgrade 20260602_0020:head --sql
```

结果：成功生成 PostgreSQL offline SQL，包含：

- `CREATE TYPE agenttasktype AS ENUM ('SOURCE_DISCOVERY', 'LEAD_EXTRACTION', 'LEAD_GRADING', 'RETRY_WORKER')`
- `CREATE TYPE agenttaskrunstatus AS ENUM ('pending', 'running', 'succeeded', 'failed', 'retry_pending', 'paused', 'cancelled', 'manual_review_required')`
- `CREATE TABLE agent_task_runs`
- `FOREIGN KEY(prompt_template_id) REFERENCES llm_prompt_templates (id) ON DELETE SET NULL`

## 5. 验收结果

- `agent_task_runs` 可审计任务输入、输出、错误、模型和重试。
- 状态机包含 pending、running、succeeded、failed、retry_pending、paused、cancelled、manual_review_required。
- task_type 支持 SOURCE_DISCOVERY、LEAD_EXTRACTION、LEAD_GRADING、RETRY_WORKER。
- 非法状态流转被测试覆盖。
- 最大重试次数规则被测试覆盖。

## 6. 风控结果

- 不自动社交私信。
- 不自动加好友。
- 不登录后批量采集。
- 不反爬规避。
- 不抓取非公开数据。
- 未改变 High/Forbidden 风险边界。
- 未引入触达、采集、抽取或自动调度能力。

## 7. 双轮评审记录

### 第一轮评审：Story 范围与需求一致性

结论：通过。

发现项：

- 已完成 Story 指定的 migration、model、schema 和基础状态机 service。
- 字段覆盖 Story 要求的审计字段。
- 实现未扩展到 APScheduler、Redis lock、LLM 调用、Source Discovery Agent 或 LEAD_EXTRACTION。

修正结果：

- 已补充 `AgentTaskRun` 和新枚举到 `models/__init__.py` 的实际导入和 `__all__`。

### 第二轮评审：测试、迁移与合规边界

结论：通过。

发现项：

- 目标测试与 P2-E1-S1 回归测试通过：12 passed。
- 新增 Python 文件编译通过。
- Alembic offline SQL 生成成功，迁移链 head 为 `20260602_0021`。
- 本 Story 仅建立审计事实表，不涉及外部渠道动作或客户触达。

修正结果：

- 已将 service 时间生成改为 `datetime.now(UTC)`，避免 `datetime.utcnow()` 告警。
