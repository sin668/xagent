# Story P1-E2-S1：实现 channel_plans 渠道计划管理

状态：Done  
Sprint：Sprint 1  
优先级：P0  
Epic：P1-E2 渠道计划与风险规则

## 用户故事

作为线索运营，我希望能配置每天运行哪些渠道、关键词、城市和配额，以便控制小范围运行节奏。

## 业务价值

让每日 100 条候选线索目标可控、可调、可复盘。

## 依赖

- P1-E1-S1

## 实现范围

- 新增 `channel_plans`。
- 支持国家、城市、渠道名称、渠道类型、风险等级、关键词、daily_url_limit、daily_lead_limit、status、owner。
- 支持启用、暂停、归档。

## 数据/API 影响

- 新增 channel plan CRUD API。

## 验收标准

- Low/Medium/High/Forbidden 风险等级必须枚举校验。
- daily_url_limit 不得为空。
- Forbidden 计划不能启用。
- High 计划启用时必须限定 public_discovery_only。

## 非目标

- 不实现自动搜索执行。

## 风控检查

- 不允许创建包含自动私信、加好友、登录采集的计划。

## 实施结果

完成日期：2026-05-29

### 修改文件

- `apps/api/alembic/versions/20260529_0014_channel_plans.py`
- `apps/api/app/models/enums.py`
- `apps/api/app/models/channel_plan.py`
- `apps/api/app/models/__init__.py`
- `apps/api/app/schemas/channel_plans.py`
- `apps/api/app/services/channel_plans.py`
- `apps/api/app/api/channel_plans.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_channel_plans_foundation.py`
- `apps/api/tests/test_integration_postgres_redis.py`
- `_bmad-output/implementation-artifacts/codex-p1-e2-s1-执行结果.md`

### 验收结果

- 新增 `channel_plans` 表，覆盖国家、城市、渠道名称、渠道类型、风险等级、关键词、每日 URL 配额、每日线索配额、状态、负责人。
- 新增 `source_usage_type` 字段，用于表达 High 风险渠道的 `public_discovery_only` 执行边界。
- 新增 `ChannelPlanStatus`：`draft`、`enabled`、`paused`、`archived`。
- 新增 CRUD API：`POST /channel-plans`、`GET /channel-plans`、`GET /channel-plans/{plan_id}`、`PATCH /channel-plans/{plan_id}`、`DELETE /channel-plans/{plan_id}`。
- Low/Medium/High/Forbidden 风险等级通过 schema 和 service 双层枚举校验。
- `daily_url_limit` 必填且必须大于 0。
- Forbidden 计划不能启用。
- High 计划启用时必须限定 `public_discovery_only`。
- 风控检查会拒绝包含自动私信、自动加好友、登录采集、批量私信等动作描述的计划。
- 未实现自动搜索执行。

### 测试结果

- `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_channel_plans_foundation.py -q`：9 passed。
- `/opt/miniconda3/envs/booking-room/bin/python -m py_compile ...`：通过。
- `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_channel_plans_foundation.py apps/api/tests/test_audit_risk_logs_foundation.py apps/api/tests/test_staging_leads_foundation.py apps/api/tests/test_page_snapshots_foundation.py apps/api/tests/test_raw_collection_foundation.py apps/api/tests/test_phase1_data_layer_baseline.py -q`：39 passed。
- `cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic heads`：输出 `20260529_0014 (head)`。
- `cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic upgrade 20260529_0013:head --sql`：成功生成 PostgreSQL offline SQL，包含 `channel_plans` 表和索引。
- `cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic upgrade head`：当前工具沙箱网络拦截，错误为 `PermissionError: [Errno 1] Operation not permitted`；外部网络权限重试被审批服务 503 阻断，真实 PostgreSQL 落库需在可出网环境复验。

### 风控结果

- 未加入自动搜索执行、自动私信、自动加好友、登录后批量采集或反爬规避能力。
- High 计划默认 `public_discovery_only`。
- Forbidden 计划可保留为非启用状态用于治理记录，但不能启用。
