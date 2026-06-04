# P2-E5-S1 APScheduler 开关、任务注册和 Redis lock 执行结果

## 基本信息

- Story：`docs/stories/phase-2-small-run/P2-E5-S1-agent-scheduler-redis-lock.md`
- 状态：已完成
- 执行日期：2026-06-02
- 执行原则：每次只执行一个 Story；不做锁操作；不做 git 操作；使用 TDD；完成前执行验证；完成后执行两轮独立多维度评审。

## 交付内容

- 新增：`apps/api/app/services/agent_locks.py`
- 新增：`apps/api/app/services/agent_scheduler.py`
- 新增：`apps/api/tests/test_agent_locks.py`
- 新增：`apps/api/tests/test_agent_scheduler.py`
- 修改：`apps/api/app/settings.py`
- 修改：`apps/api/pyproject.toml`
- 修改：`apps/api/tests/test_integration_postgres_redis.py`

## 功能说明

### 调度开关

新增配置项：

- `AGENT_SCHEDULER_ENABLED` / `VEHICLE_LEADS_AGENT_SCHEDULER_ENABLED`
  - 默认：`false`
  - 行为：关闭时不得注册或启动定时任务。
- `AGENT_SCHEDULER_LOCK_TTL_SECONDS` / `VEHICLE_LEADS_AGENT_SCHEDULER_LOCK_TTL_SECONDS`
  - 默认：`300`
  - 行为：控制 Redis lock 的短期互斥 TTL。

### 调度任务

`AgentSchedulerService` 在开启时注册三类任务：

- `source_discovery_hourly`
  - trigger：`interval`
  - seconds：`3600`
- `lead_extraction_interval`
  - trigger：`interval`
  - seconds：`900`
- `retry_failed_tasks`
  - trigger：`interval`
  - seconds：`300`

每个任务使用：

- `max_instances=1`
- `coalesce=True`
- `replace_existing=True`

### Redis lock

`AgentRedisLockManager` 使用 Redis `SET key token NX EX ttl` 实现短期互斥：

- 相同 job_id 重复获取锁会失败。
- 未获取锁时返回 `{"status":"skipped","reason":"lock_not_acquired","job_id":...}`。
- 释放锁时校验 token，避免误删其他执行者持有的锁。
- Redis lock 不写审计表，不作为事实来源。

## TDD 记录

### RED 1

先创建：

- `apps/api/tests/test_agent_scheduler.py`
- `apps/api/tests/test_agent_locks.py`

运行：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_agent_scheduler.py apps/api/tests/test_agent_locks.py
```

结果：收集失败。

失败原因符合预期：

- `ModuleNotFoundError: No module named 'app.services.agent_scheduler'`
- `ModuleNotFoundError: No module named 'app.services.agent_locks'`

### GREEN 1

新增 `agent_locks.py`、`agent_scheduler.py` 和 settings 配置后，目标测试通过：

```text
7 passed
```

### RED 2

补充 APScheduler 依赖声明测试后，目标测试失败：

```text
assert "apscheduler" in pyproject.lower()
```

失败原因符合预期：环境已安装 APScheduler，但 `pyproject.toml` 未声明部署依赖。

### GREEN 2

补充 `apscheduler>=3.11` 后，目标测试通过：

```text
8 passed
```

## 验证结果

### 目标测试

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_agent_scheduler.py apps/api/tests/test_agent_locks.py
```

结果：`8 passed`。

### 相关后端回归

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest \
  apps/api/tests/test_settings.py \
  apps/api/tests/test_integration_postgres_redis.py \
  apps/api/tests/test_source_discovery_agent_api.py \
  apps/api/tests/test_agent_task_run_model.py \
  apps/api/tests/test_phase2_data_foundation.py
```

结果：`20 passed`。

### 语法检查

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile \
  apps/api/app/services/agent_locks.py \
  apps/api/app/services/agent_scheduler.py \
  apps/api/app/settings.py
```

结果：通过。

## 调试记录

相关后端回归首次失败：

```text
test_real_postgres_has_mvp_data_foundation_tables
assert '20260602_0022' == '20260529_0016'
```

根因：

- `test_integration_postgres_redis.py` 仍断言第一阶段旧 Alembic head `20260529_0016`。
- 第二阶段数据底座已在 `P2-E1-S4` 中升级真实库至 `20260602_0022`，且当前真实库查询结果也是 `20260602_0022`。

修正：

- 将真实库集成测试期望 head 更新为 `20260602_0022`。
- 补充第二阶段表集合检查：
  - `llm_prompt_templates`
  - `agent_task_runs`
  - `lead_source_candidates`

复验：

- 相关后端回归 `20 passed`。

## 验收对照

- 调度开关可控：通过。
- 开关关闭时不得启动定时任务：通过。
- 注册 `source_discovery_hourly`：通过。
- 注册 `lead_extraction_interval`：通过。
- 注册 `retry_failed_tasks`：通过。
- 每个任务启动前必须获取 Redis lock：通过，调度 wrapper 调用 `lock_manager.run_with_lock()`。
- Redis lock 防止重复执行：通过。
- Redis lock 只做短期互斥，不作为审计事实来源：通过。

## 第一轮独立多维度评审

- 结论：通过，无实质阻塞问题。
- 功能完整性：调度开关、任务注册和 Redis lock 均已实现并测试。
- 可部署性：APScheduler 已声明为依赖，避免环境偶然安装导致部署缺失。
- 风险合规：当前实现仅是调度基础设施，不执行触达、不采集登录态、不绕过 High/Forbidden 风险闸门。
- 测试覆盖：目标测试覆盖开关、注册、执行包装、互斥、释放和 token 保护。
- 发现项：真实库集成测试的 Alembic head 断言过期。
- 修正结果：已更新为 `20260602_0022` 并复跑通过。

## 第二轮独立多维度评审

- 结论：通过，连续两轮未发现新增实质阻塞问题。
- 回归风险：目标测试 `8 passed`，相关后端回归 `20 passed`。
- 环境风险：`agent_scheduler_enabled` 默认关闭，避免上线后意外自动运行。
- 数据事实边界：Redis lock 不写审计，审计事实仍保留在 `agent_task_runs` 等数据库表。
- 范围控制：未执行下一 Story；未实现失败重试恢复、来源池消费或抽取写回。
- 修正结果：无需新增修正。

## 后续建议

下一 Story 可进入 `P2-E5-S2-agent-retry-timeout-recovery.md`，实现失败重试、超时恢复和任务状态机收敛。但本次执行未进入下一 Story。
