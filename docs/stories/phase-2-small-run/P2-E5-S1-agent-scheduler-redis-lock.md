# Story P2-E5-S1：APScheduler 开关、任务注册和 Redis lock

状态：Done  
Sprint：Sprint 4  
优先级：P1  
Epic：P2-E5

## 用户故事

作为第二阶段小范围运行的研发执行者，我希望完成“APScheduler 开关、任务注册和 Redis lock”，以便系统可以按 BMAD 已冻结方案推进真实 LLM、来源发现、审核、抽取、审计和联调闭环。

## 上下文来源

- `docs/product/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行方案与产品技术设计.md`
- `_bmad-output/brainstorming/brainstorming-session-2026-06-02-第二阶段小范围运行-LLM来源发现Agent.md`
- `docs/superpowers/plans/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行Codex推进计划.md`
- `docs/AI协同开发执行标准.md`
- `AGENTS.md`

## Story 定义

**目标：** 建立自动任务调度基础。

**Files:**

- Modify: `apps/api/app/settings.py`
- Create: `apps/api/app/services/agent_scheduler.py`
- Create: `apps/api/app/services/agent_locks.py`
- Test: `apps/api/tests/test_agent_scheduler.py`
- Test: `apps/api/tests/test_agent_locks.py`

**Codex 提示词：**

```text
请执行 P2-E5-S1：APScheduler 开关、任务注册和 Redis lock。

要求：
1. 使用 superpowers:test-driven-development。
2. 增加 AGENT_SCHEDULER_ENABLED 开关，默认 false。
3. 注册 source_discovery_hourly、lead_extraction_interval、retry_failed_tasks。
4. 每个任务启动前必须获取 Redis lock。
5. Redis lock 只做短期互斥，不作为审计事实来源。
6. 开关关闭时不得启动定时任务。
7. 运行 pytest apps/api/tests/test_agent_scheduler.py apps/api/tests/test_agent_locks.py。
8. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p2-e5-s1-执行结果.md。
不要执行下一个 Story。
```

**验收标准：**

- 调度开关可控。
- Redis lock 防止重复执行。

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作。
- 不做 git 操作。
- 代码实现 Story 必须使用 `superpowers:test-driven-development`。
- 调试异常必须使用 `superpowers:systematic-debugging`。
- 完成前必须使用 `superpowers:verification-before-completion`。
- 完成后必须执行两轮独立多维度评审，并记录结论、发现项和修正结果。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- 不自动社交私信。
- 不自动加好友。
- 不登录后批量采集。
- 不反爬规避。
- 不抓取非公开数据。
- High 来源未审核不得进入自动抽取。
- Forbidden 来源不得进入自动抽取。
- Invalid 和 Watch 不进入触达队列。
- 勿扰客户不得再次进入触达队列。
- C 级线索报价、合同或实质交易前必须合规复核。
- 所有 AI 输出必须保存来源证据、prompt 版本、模型和审计记录。

## 实施结果

已完成。

### 本次变更

- 新增调度开关配置：
  - `AGENT_SCHEDULER_ENABLED` / `VEHICLE_LEADS_AGENT_SCHEDULER_ENABLED`，默认 `false`。
  - `AGENT_SCHEDULER_LOCK_TTL_SECONDS` / `VEHICLE_LEADS_AGENT_SCHEDULER_LOCK_TTL_SECONDS`，默认 `300`。
- 新增 Redis 短期互斥锁服务：`apps/api/app/services/agent_locks.py`。
- 新增 Agent 调度服务：`apps/api/app/services/agent_scheduler.py`。
- 新增测试：
  - `apps/api/tests/test_agent_locks.py`
  - `apps/api/tests/test_agent_scheduler.py`
- 更新 `apps/api/pyproject.toml`，声明 `apscheduler>=3.11`。
- 更新 `apps/api/tests/test_integration_postgres_redis.py`，将真实库 Alembic head 断言更新为第二阶段当前 head `20260602_0022`，并补充第二阶段表集合。

### 验收结果

- 调度开关可控：通过。`agent_scheduler_enabled` 默认 `false`；关闭时 `AgentSchedulerService.start()` 不注册、不启动任务。
- 注册必要任务：通过。开启时注册：
  - `source_discovery_hourly`，间隔 `3600` 秒。
  - `lead_extraction_interval`，间隔 `900` 秒。
  - `retry_failed_tasks`，间隔 `300` 秒。
- Redis lock 防止重复执行：通过。相同 job_id 第二次获取锁失败并返回 `skipped`，不会执行 handler。
- Redis lock 只做短期互斥：通过。锁使用 `SET key token NX EX ttl`，未写入审计表；审计仍由任务执行链路负责。
- 锁释放安全：通过。仅 token 匹配时释放，不删除其他持有者的锁。
- APScheduler 依赖已声明：通过。

### TDD 记录

- RED 1：创建 `test_agent_scheduler.py` 和 `test_agent_locks.py` 后运行目标测试，结果收集失败，原因符合预期：`agent_scheduler.py` 和 `agent_locks.py` 不存在。
- GREEN 1：新增服务和 settings 配置后，目标测试 `7/7 passed`。
- RED 2：补充 APScheduler 依赖声明测试，目标测试失败，原因符合预期：`pyproject.toml` 未声明 `apscheduler`。
- GREEN 2：补充 `apscheduler>=3.11` 后，目标测试 `8/8 passed`。

### 验证命令

- `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_agent_scheduler.py apps/api/tests/test_agent_locks.py`：`8 passed`。
- `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_settings.py apps/api/tests/test_integration_postgres_redis.py apps/api/tests/test_source_discovery_agent_api.py apps/api/tests/test_agent_task_run_model.py apps/api/tests/test_phase2_data_foundation.py`：`20 passed`。
- `/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/agent_locks.py apps/api/app/services/agent_scheduler.py apps/api/app/settings.py`：通过。

### 调试记录

- 相关回归首次失败在 `test_integration_postgres_redis.py`：真实 PostgreSQL `alembic_version` 已是 `20260602_0022`，测试仍断言旧 head `20260529_0016`。
- 根因：该测试是第一阶段真实库集成断言，第二阶段数据底座已升级真实库并在 `P2-E1-S4` 记录 `20260602_0022 (head)`。
- 修正：将测试期望 head 更新为 `20260602_0022`，并补充 `llm_prompt_templates`、`agent_task_runs`、`lead_source_candidates` 表检查。

### 第一轮独立多维度评审

- 结论：通过，无实质阻塞问题。
- 功能完整性：调度开关、三类任务注册、Redis 互斥锁均已覆盖。
- 安全合规：锁只做短期互斥，不作为审计事实来源；没有新增任何自动触达能力。
- 可部署性：APScheduler 已声明为后端依赖。
- 测试覆盖：目标测试覆盖开关默认关闭、关闭不启动、开启注册、锁包装执行、锁互斥、锁释放和 token 保护。
- 发现项：真实库集成测试使用旧 Alembic head，已不符合第二阶段现状。
- 修正结果：已更新为 `20260602_0022` 并复跑通过。

### 第二轮独立多维度评审

- 结论：通过，连续两轮未发现新增实质阻塞问题。
- 回归风险：目标测试 `8 passed`，相关后端回归 `20 passed`。
- 环境风险：实现未自动接入 FastAPI lifespan，避免开关关闭时误启动；后续接入可在更明确 Story 中完成。
- 合规边界：调度注册的是作业基础设施，没有绕过 High/Forbidden 风险闸门，也没有触达行为。
- 范围控制：未执行下一 Story；未实现重试恢复、Lead Extraction 消费或结果写回。
- 修正结果：无需新增修正。

### 归档

- `_bmad-output/implementation-artifacts/codex-p2-e5-s1-执行结果.md`
