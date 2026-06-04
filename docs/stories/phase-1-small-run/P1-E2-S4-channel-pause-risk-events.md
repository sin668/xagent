# Story P1-E2-S4：实现渠道暂停与风险事件处理

状态：Done  
Sprint：Sprint 2  
优先级：P1  
Epic：P1-E2 渠道计划与风险规则

## 用户故事

作为运营负责人，我希望某个渠道出现异常时能立即暂停，以便保护账号、平台和品牌风险。

## 业务价值

让小范围运行有可控的止损机制。

## 依赖

- P1-E2-S1
- P1-E1-S5

## 实现范围

- 支持 channel_plan status=pause。
- 风险事件可关联 channel_plan。
- 暂停后不允许创建新 collection_task。
- 支持风险事件 resolution_status。

## 数据/API 影响

- 更新 channel plan 状态 API。
- 新增 risk event create/resolve API。

## 验收标准

- 暂停渠道无法启动新任务。
- 恢复渠道必须记录处理说明。
- 风险事件可按 severity 查询。

## 非目标

- 不做自动发消息告警。

## 风控检查

- 投诉、封禁、违规风险必须触发暂停建议。

## 实施结果

完成日期：2026-05-29

### 修改文件

- `apps/api/alembic/versions/20260529_0016_channel_pause_risk_events.py`
- `apps/api/app/models/risk_event.py`
- `apps/api/app/services/audit_risk.py`
- `apps/api/app/services/channel_plans.py`
- `apps/api/app/services/raw_collection.py`
- `apps/api/app/schemas/channel_plans.py`
- `apps/api/app/schemas/risk_events.py`
- `apps/api/app/api/risk_events.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_channel_pause_risk_events.py`
- `apps/api/tests/test_integration_postgres_redis.py`
- `docs/stories/phase-1-small-run/P1-E2-S4-channel-pause-risk-events.md`
- `_bmad-output/implementation-artifacts/codex-p1-e2-s4-执行结果.md`

### 验收结果

- `channel_plans` 已支持 `paused` 状态。
- 暂停或归档的 channel plan 无法创建新的 `collection_task`。
- `risk_events` 可关联 `channel_plan_id`。
- `risk_events` 支持 `resolution_status`、`resolution_note`、`resolved_by`、`resolved_at`。
- 新增 `POST /risk-events`、`GET /risk-events`、`POST /risk-events/{event_id}/resolve`。
- 风险事件可按 `severity` 查询。
- 恢复暂停渠道时必须提供 `resolution_note`，并写入 review log。
- 投诉、封禁、违规风险以及 High/Critical severity 会触发 `pause_suggested=true`。
- 未实现自动发消息告警。

### 测试结果

- `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_channel_pause_risk_events.py -q`：8 passed。
- `/opt/miniconda3/envs/booking-room/bin/python -m py_compile ...`：通过。
- `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_channel_pause_risk_events.py apps/api/tests/test_high_risk_public_discovery_isolation.py apps/api/tests/test_channel_action_policy_validator.py apps/api/tests/test_channel_plans_foundation.py apps/api/tests/test_raw_collection_foundation.py apps/api/tests/test_audit_risk_logs_foundation.py -q`：47 passed。
- `cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic heads`：输出 `20260529_0016 (head)`。
- `cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic upgrade 20260529_0015:head --sql`：成功生成 PostgreSQL offline SQL。
- `cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic upgrade head`：当前工具沙箱网络拦截，错误为 `PermissionError: [Errno 1] Operation not permitted`；外部网络权限重试被审批服务 503 阻断。

### 风控结果

- 暂停/归档渠道无法启动新任务。
- 恢复渠道必须留下处理说明。
- 投诉、封禁、违规风险只触发暂停建议，不自动发消息告警。
