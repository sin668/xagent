# P1-E1-S2 执行结果

Story：`docs/stories/phase-1-small-run/P1-E1-S2-raw-collection-task-candidate-url.md`  
执行人：Codex  
执行日期：2026-05-29  
状态：已完成本地实现与可用验证；真实 PostgreSQL migration 待审批通道恢复后复验

## 1. 执行说明

本 Story 按第一阶段实施推进计划执行。用户已明确要求后续不执行任何 Story 锁操作，因此本 Story 未执行锁命令。

## 2. 修改文件

- `apps/api/alembic/versions/20260529_0010_raw_collection_tasks_candidate_urls.py`
- `apps/api/app/models/enums.py`
- `apps/api/app/models/collection_task.py`
- `apps/api/app/models/candidate_url.py`
- `apps/api/app/models/__init__.py`
- `apps/api/app/services/raw_collection.py`
- `apps/api/app/schemas/raw_collection.py`
- `apps/api/app/api/raw_collection.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_raw_collection_foundation.py`
- `apps/api/tests/test_integration_postgres_redis.py`
- `docs/stories/phase-1-small-run/P1-E1-S2-raw-collection-task-candidate-url.md`
- `_bmad-output/implementation-artifacts/codex-p1-e1-s2-执行结果.md`

## 3. 实现内容

### 3.1 数据库迁移

新增 migration：`20260529_0010_raw_collection_tasks_candidate_urls.py`

新增表：

- `collection_tasks`
- `candidate_urls`

关键字段：

- `collection_tasks.task_type`
- `collection_tasks.channel_name`
- `collection_tasks.risk_level`
- `collection_tasks.source_usage_type`
- `collection_tasks.allowed_actions`
- `collection_tasks.forbidden_actions`
- `collection_tasks.status`
- `candidate_urls.task_id`
- `candidate_urls.url`
- `candidate_urls.url_hash`
- `candidate_urls.source_platform`
- `candidate_urls.source_risk_level`
- `candidate_urls.source_usage_type`
- `candidate_urls.requires_secondary_verification`
- `candidate_urls.discovery_reason`
- `candidate_urls.status`

关键约束：

- `candidate_urls.task_id` 外键关联 `collection_tasks.id`
- `candidate_urls.url_hash` 唯一约束 `uq_candidate_urls_url_hash`

### 3.2 后端模型与服务

新增模型：

- `CollectionTask`
- `CandidateUrl`

新增枚举：

- `SourceUsageType`
- `CollectionTaskStatus`
- `CandidateUrlStatus`

新增服务：

- `RawCollectionService.normalize_url`
- `RawCollectionService.hash_url`
- `RawCollectionService.resolve_source_usage_type`
- `RawCollectionService.requires_secondary_verification`
- `RawCollectionService.validate_candidate_task_id`
- `RawCollectionService.create_collection_task`
- `RawCollectionService.upsert_candidate_url`

### 3.3 API

新增 API：

- `POST /raw-collection/tasks`
- `GET /raw-collection/tasks`
- `POST /raw-collection/candidate-urls/upsert`
- `GET /raw-collection/candidate-urls`

## 4. 验收结果

| 验收项 | 结论 | 证据 |
|---|---|---|
| 同一 URL 重复写入不会产生重复记录 | 通过 | `url_hash` 唯一约束；`RawCollectionService.upsert_candidate_url` 按 hash 查询并更新既有记录 |
| High URL 默认 `requires_secondary_verification=true` | 通过 | `requires_secondary_verification(ChannelRiskLevel.HIGH)` 测试通过 |
| Forbidden 渠道不得创建可执行任务 | 通过 | `resolve_source_usage_type(ChannelRiskLevel.FORBIDDEN, ...)` 测试通过 |
| 每条 candidate URL 必须关联 task_id | 通过 | `validate_candidate_task_id(None)` 测试通过；migration 中 `task_id` 非空外键 |
| High 任务只能标记为 public_discovery_only | 通过 | High 风险 source usage 测试通过 |
| 禁止动作字段必须可记录 | 通过 | `collection_tasks.forbidden_actions` 非空字段 |
| 不读取页面正文 | 通过 | 未新增页面读取逻辑 |
| 不调用 LLM | 通过 | 未新增 LLM service 调用 |

## 5. 测试记录

### 5.1 测试先行

首次运行：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_raw_collection_foundation.py -q
```

结果：失败，原因是 `app.services.raw_collection` 尚未实现。

### 5.2 实现后测试

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_raw_collection_foundation.py apps/api/tests/test_phase1_data_layer_baseline.py -q
```

结果：

```text
12 passed in 0.18s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/models/enums.py apps/api/app/models/collection_task.py apps/api/app/models/candidate_url.py apps/api/app/services/raw_collection.py apps/api/app/schemas/raw_collection.py apps/api/app/api/raw_collection.py apps/api/alembic/versions/20260529_0010_raw_collection_tasks_candidate_urls.py apps/api/tests/test_raw_collection_foundation.py apps/api/tests/test_integration_postgres_redis.py
```

结果：通过。

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/alembic heads
```

结果：

```text
20260529_0010 (head)
```

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/alembic upgrade 20260529_0009:head --sql
```

结果：通过，成功生成 PostgreSQL offline SQL，包含 `collection_tasks`、`candidate_urls`、`uq_candidate_urls_url_hash` 和 `FOREIGN KEY(task_id)`。

### 5.3 真实 PostgreSQL migration 验证

命令：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/alembic upgrade head
```

结果：

```text
Rejected: Automatic approval review failed: unexpected status 503 Service Unavailable
```

结论：当前工具审批服务不可用，无法从工具环境完成真实 PostgreSQL 落库验证。集成测试已更新目标 revision 为 `20260529_0010`，待通道恢复后执行同一命令复验。

## 6. 两轮独立评审

### 6.1 第一轮：需求与边界评审

结论：通过。

发现项：

- 本 Story 不应读取页面正文，否则会进入 `P1-E1-S3` 范围。
- 本 Story 不应调用 LLM，否则会进入 Sprint 3 的 Agent/LLM 范围。

修正结果：

- 仅实现 raw 任务和候选 URL 入库服务/API。
- 页面正文、快照、LLM 抽取均未实现。

### 6.2 第二轮：风控与幂等评审

结论：通过，存在一个环境残留验证项。

发现项：

- High 风险必须被强制限制为 `public_discovery_only`。
- Forbidden 渠道不能创建可执行任务。
- URL 幂等不能依赖原始 URL 字符串，否则查询参数顺序和 fragment 会导致重复。
- 真实 PostgreSQL migration 未能执行，原因是当前工具审批服务 503。

修正结果：

- 增加 `resolve_source_usage_type` 强制规则。
- 增加 URL 标准化和 SHA-256 hash。
- 增加 `uq_candidate_urls_url_hash` 唯一约束。
- 在执行结果中记录真实库验证待复验。

## 7. 残留风险

- 真实 PostgreSQL 尚未执行 `alembic upgrade head`，需要审批通道恢复后复验。
- `collection_tasks.plan_id` 暂未外键关联 `channel_plans`，因为 `channel_plans` 属于后续 `P1-E2-S1`。

## 8. 下一步建议

继续执行：

`docs/stories/phase-1-small-run/P1-E1-S3-page-snapshots-source-evidence.md`

