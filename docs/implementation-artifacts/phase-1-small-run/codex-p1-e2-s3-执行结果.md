# P1-E2-S3 执行结果

Story：`docs/stories/phase-1-small-run/P1-E2-S3-high-risk-public-discovery-isolation.md`  
执行人：Codex  
执行日期：2026-05-29  
状态：已完成本地实现与可用验证；真实 PostgreSQL migration 待当前工具出网/审批通道恢复后复验

## 1. 执行说明

本 Story 按第一阶段实施推进计划执行。用户已明确要求后续不执行任何 Story 锁操作，因此本 Story 未执行锁命令。

## 2. 修改文件

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

## 3. 实现内容

### 3.1 数据库迁移

新增 migration：`20260529_0015_high_risk_public_discovery_isolation.py`

扩展表：

- `collection_tasks.max_sample_size`
- `candidate_urls.queue_eligible`

### 3.2 RawCollectionService 规则

新增常量：

- `HIGH_RISK_PUBLIC_DISCOVERY_TASK_TYPE = "high_risk_public_discovery"`
- `DEFAULT_HIGH_RISK_MAX_SAMPLE_SIZE = 20`

新增规则方法：

- `resolve_task_defaults`
- `default_queue_eligible`
- `task_status_after_snapshot`

规则效果：

- `high_risk_public_discovery` 必须使用 High 风险等级。
- High 任务默认 `source_usage_type=public_discovery_only`。
- High 任务默认 `max_sample_size=20`。
- High candidate 默认 `queue_eligible=false`。
- High candidate 默认 `requires_secondary_verification=true`。
- High 公开发现遇到验证码、登录墙、访问策略墙时，任务状态更新为 `blocked`。

### 3.3 API 适配

`CollectionTaskCreate` / `CollectionTaskResponse` 新增：

- `max_sample_size`

`CandidateUrlResponse` 新增：

- `queue_eligible`

## 4. 验收结果

| 验收项 | 结论 | 证据 |
|---|---|---|
| 支持 `task_type=high_risk_public_discovery` | 通过 | `resolve_task_defaults` 测试覆盖 |
| High task 默认 max sample 限制 | 通过 | 默认 `20`，测试覆盖 |
| High candidate 默认 `queue_eligible=false` | 通过 | `default_queue_eligible` 测试覆盖 |
| High candidate 默认 `requires_secondary_verification=true` | 通过 | 复用并测试 `requires_secondary_verification` |
| High 任务无法触发触达类 action | 通过 | `message` 动作由 validator 阻断 |
| High 线索无法直接进入 core 或 outreach queue | 通过 | candidate 默认不可进入 queue，staging 已要求 High 二次复核 |
| High 任务出现验证码/登录墙时自动进入 blocked | 通过 | `task_status_after_snapshot` 测试覆盖 |
| 不实现 High 平台登录访问 | 通过 | 未新增登录能力 |
| 不允许采集评论、粉丝、好友、关系链 | 通过 | 全局动作策略阻断相关动作 |

## 5. 测试记录

### 5.1 测试先行

首次运行：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_high_risk_public_discovery_isolation.py -q
```

结果：失败，原因是 migration、`resolve_task_defaults`、`default_queue_eligible`、`task_status_after_snapshot` 尚未实现。

### 5.2 实现后测试

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_high_risk_public_discovery_isolation.py -q
```

结果：

```text
8 passed in 0.35s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/models/collection_task.py apps/api/app/models/candidate_url.py apps/api/app/services/raw_collection.py apps/api/app/schemas/raw_collection.py apps/api/app/api/raw_collection.py apps/api/alembic/versions/20260529_0015_high_risk_public_discovery_isolation.py apps/api/tests/test_high_risk_public_discovery_isolation.py
```

结果：通过。

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_high_risk_public_discovery_isolation.py apps/api/tests/test_channel_action_policy_validator.py apps/api/tests/test_channel_plans_foundation.py apps/api/tests/test_raw_collection_foundation.py apps/api/tests/test_page_snapshots_foundation.py apps/api/tests/test_staging_leads_foundation.py apps/api/tests/test_audit_risk_logs_foundation.py apps/api/tests/test_phase1_data_layer_baseline.py -q
```

结果：

```text
55 passed in 0.30s
```

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/alembic heads
```

结果：

```text
20260529_0015 (head)
```

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/alembic upgrade 20260529_0014:head --sql
```

结果：通过，成功生成 PostgreSQL offline SQL，包含 `collection_tasks.max_sample_size`、`candidate_urls.queue_eligible` 和索引。

### 5.3 真实 PostgreSQL migration 验证

命令：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/alembic upgrade head
```

结果：

```text
PermissionError: [Errno 1] Operation not permitted
```

结论：当前沙箱阻止连接远程 PostgreSQL，命令尚未实际进入数据库侧执行。

外部网络权限第一次重试：审批超时未完成。  
外部网络权限第二次重试：审批服务返回 503。

结论：真实 PostgreSQL migration 仍无法在当前工具环境完成。`apps/api/tests/test_integration_postgres_redis.py` 已将目标 revision 更新为 `20260529_0015`，待通道恢复后复验。

## 6. 两轮独立评审

### 6.1 第一轮：需求与数据流评审

结论：通过。

发现项：

- 原有 `requires_secondary_verification` 已覆盖 High 二次复核，但缺少候选 URL 层面的 `queue_eligible` 显式隔离标记。
- High 任务需要样本上限，否则可能被后续 Agent 执行器误用为普通任务。
- High 遇到验证码/登录墙不能继续排队等待自动处理。

修正结果：

- `candidate_urls` 新增 `queue_eligible`，High 默认 `false`。
- `collection_tasks` 新增 `max_sample_size`，High 公开发现默认 `20`。
- `create_page_snapshot` 在 High 任务遇到需人工/受限读取状态时自动将任务设为 `blocked`。

### 6.2 第二轮：合规与安全评审

结论：通过，存在一个环境残留验证项。

发现项：

- High 任务不能通过 `task_type` 伪装成 Medium/Low 自动任务。
- High 结果不得直接进入 core 或 outreach queue。
- 真实 PostgreSQL migration 未能执行，原因是当前工具网络/审批通道阻断。

修正结果：

- `high_risk_public_discovery` 强制 High 风险等级。
- High candidate 默认 `queue_eligible=false` 且 `requires_secondary_verification=true`。
- 在执行结果中记录真实库验证待复验。

## 7. 残留风险

- 真实 PostgreSQL 尚未执行 `alembic upgrade head`，需要在可出网执行环境中复验。
- 后续 Sprint 2 晋级 core 时，还需要继续强制读取 `queue_eligible` 与二次复核状态，避免 High 来源越级交付。

## 8. 下一步建议

继续执行：

`docs/stories/phase-1-small-run/P1-E2-S4-channel-pause-risk-events.md`
