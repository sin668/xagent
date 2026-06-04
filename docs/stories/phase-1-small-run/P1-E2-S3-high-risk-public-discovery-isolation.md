# Story P1-E2-S3：实现 High 只读公开发现任务隔离

状态：Done  
Sprint：Sprint 1  
优先级：P0  
Epic：P1-E2 渠道计划与风险规则

## 用户故事

作为合规负责人，我希望 High 渠道任务与 Low/Medium 自动任务隔离，以便防止 High 结果误入触达队列。

## 业务价值

在探索 High 公开线索密度的同时控制平台和触达风险。

## 依赖

- P1-E1-S2
- P1-E2-S2

## 实现范围

- 支持 task_type=`high_risk_public_discovery`。
- High task 默认 max sample 限制。
- High candidate 默认 queue_eligible=false。
- High candidate 默认 requires_secondary_verification=true。

## 数据/API 影响

- 更新 collection task 创建逻辑。
- 更新 candidate URL 默认值规则。

## 验收标准

- High 任务无法触发触达类 action。
- High 线索无法直接进入 core 或 outreach queue。
- High 任务出现验证码/登录墙时自动进入 blocked。

## 非目标

- 不实现 High 平台登录访问。

## 风控检查

- 不允许采集评论、粉丝、好友、关系链。

## 实施结果

完成日期：2026-05-29

### 修改文件

- `apps/api/alembic/versions/20260529_0015_high_risk_public_discovery_isolation.py`
- `apps/api/app/models/collection_task.py`
- `apps/api/app/models/candidate_url.py`
- `apps/api/app/schemas/raw_collection.py`
- `apps/api/app/api/raw_collection.py`
- `apps/api/app/services/raw_collection.py`
- `apps/api/tests/test_high_risk_public_discovery_isolation.py`
- `apps/api/tests/test_integration_postgres_redis.py`
- `docs/stories/phase-1-small-run/P1-E2-S3-high-risk-public-discovery-isolation.md`
- `_bmad-output/implementation-artifacts/codex-p1-e2-s3-执行结果.md`

### 验收结果

- 支持 `task_type=high_risk_public_discovery`。
- High 公开发现任务默认 `source_usage_type=public_discovery_only`。
- High 公开发现任务默认 `max_sample_size=20`。
- `high_risk_public_discovery` 必须使用 High 风险等级。
- `candidate_urls` 新增 `queue_eligible`，High candidate 默认 `false`。
- High candidate 默认 `requires_secondary_verification=true`。
- High 任务的触达类 action 由 `ChannelActionPolicyValidator` 阻断。
- High 任务遇到 `captcha`、`login_wall`、`access_error`、`policy_wall` 会将任务状态更新为 `blocked`。
- 不实现 High 平台登录访问。
- 不允许采集评论、粉丝、好友、关系链，此类动作由全局动作策略阻断。

### 测试结果

- `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_high_risk_public_discovery_isolation.py -q`：8 passed。
- `/opt/miniconda3/envs/booking-room/bin/python -m py_compile ...`：通过。
- `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_high_risk_public_discovery_isolation.py apps/api/tests/test_channel_action_policy_validator.py apps/api/tests/test_channel_plans_foundation.py apps/api/tests/test_raw_collection_foundation.py apps/api/tests/test_page_snapshots_foundation.py apps/api/tests/test_staging_leads_foundation.py apps/api/tests/test_audit_risk_logs_foundation.py apps/api/tests/test_phase1_data_layer_baseline.py -q`：55 passed。
- `cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic heads`：输出 `20260529_0015 (head)`。
- `cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic upgrade 20260529_0014:head --sql`：成功生成 PostgreSQL offline SQL。
- `cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic upgrade head`：当前工具沙箱网络拦截，错误为 `PermissionError: [Errno 1] Operation not permitted`；外部网络权限重试一次超时、再次重试被审批服务 503 阻断。

### 风控结果

- High 结果默认不可进入触达队列。
- High 结果必须二次复核。
- High 公开发现遇到登录墙或验证码即阻断任务。
- 未引入登录访问、评论/粉丝/好友/关系链采集能力。
