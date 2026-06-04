# P1-E1-S3 执行结果

Story：`docs/stories/phase-1-small-run/P1-E1-S3-page-snapshots-source-evidence.md`  
执行人：Codex  
执行日期：2026-05-29  
状态：已完成本地实现与可用验证；真实 PostgreSQL migration 待审批通道恢复后复验

## 1. 执行说明

本 Story 按第一阶段实施推进计划执行。用户已明确要求后续不执行任何 Story 锁操作，因此本 Story 未执行锁命令。

## 2. 修改文件

- `apps/api/alembic/versions/20260529_0011_page_snapshots_source_evidence.py`
- `apps/api/app/models/enums.py`
- `apps/api/app/models/page_snapshot.py`
- `apps/api/app/models/candidate_url.py`
- `apps/api/app/models/__init__.py`
- `apps/api/app/services/raw_collection.py`
- `apps/api/app/schemas/raw_collection.py`
- `apps/api/app/api/raw_collection.py`
- `apps/api/tests/test_page_snapshots_foundation.py`
- `apps/api/tests/test_integration_postgres_redis.py`
- `docs/stories/phase-1-small-run/P1-E1-S3-page-snapshots-source-evidence.md`
- `_bmad-output/implementation-artifacts/codex-p1-e1-s3-执行结果.md`

## 3. 实现内容

### 3.1 数据库迁移

新增 migration：`20260529_0011_page_snapshots_source_evidence.py`

新增表：

- `page_snapshots`

关键字段：

- `candidate_url_id`
- `page_title`
- `text_excerpt`
- `evidence_note`
- `read_status`
- `captured_at`
- `robots_or_policy_note`

关键约束：

- `page_snapshots.candidate_url_id` 非空外键关联 `candidate_urls.id`
- `read_status` 使用枚举：`success`、`blocked`、`failed`、`needs_manual_review`

### 3.2 后端模型与服务

新增模型：

- `PageSnapshot`

新增枚举：

- `PageSnapshotReadStatus`

扩展服务：

- `RawCollectionService.validate_candidate_url_id`
- `RawCollectionService.normalize_evidence_note`
- `RawCollectionService.normalize_read_status`
- `RawCollectionService.create_page_snapshot`
- `RawCollectionService.latest_page_snapshot_for_candidate`
- `RawCollectionService.list_page_snapshots`

### 3.3 API

新增 API：

- `POST /raw-collection/page-snapshots`
- `GET /raw-collection/page-snapshots`

## 4. 验收结果

| 验收项 | 结论 | 证据 |
|---|---|---|
| 无 candidate_url_id 不允许写入 snapshot | 通过 | `validate_candidate_url_id(None)` 测试通过；migration 中 `candidate_url_id` 非空外键 |
| evidence_note 为空时允许进入 raw，但不得进入 core | 通过 | `normalize_evidence_note(None)` 返回空字符串；core 准入规则由后续 Story 阻断 |
| read_status 可表达 success、blocked、failed、needs_manual_review | 通过 | `PageSnapshotReadStatus` 测试通过 |
| 登录墙、验证码、访问异常必须写入 read_status | 通过 | `captcha`、`login_wall`、`access_error` 映射到 `needs_manual_review` |
| 不保存完整网页镜像 | 通过 | 仅保存 `text_excerpt`，无完整 HTML 字段 |
| 不保存评论、粉丝、关系链 | 通过 | 未新增相关字段或采集逻辑 |

## 5. 测试记录

### 5.1 测试先行

首次运行：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_page_snapshots_foundation.py -q
```

结果：失败，原因是 `PageSnapshotReadStatus` 尚未实现。

### 5.2 实现后测试

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_page_snapshots_foundation.py apps/api/tests/test_raw_collection_foundation.py -q
```

结果：

```text
15 passed in 0.30s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/models/enums.py apps/api/app/models/page_snapshot.py apps/api/app/models/candidate_url.py apps/api/app/services/raw_collection.py apps/api/app/schemas/raw_collection.py apps/api/app/api/raw_collection.py apps/api/alembic/versions/20260529_0011_page_snapshots_source_evidence.py apps/api/tests/test_page_snapshots_foundation.py apps/api/tests/test_integration_postgres_redis.py
```

结果：通过。

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/alembic heads
```

结果：

```text
20260529_0011 (head)
```

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/alembic upgrade 20260529_0010:head --sql
```

结果：通过，成功生成 PostgreSQL offline SQL，包含 `page_snapshots`、`candidate_url_id` 外键、`read_status` 和 `robots_or_policy_note`。

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

结论：当前工具审批服务不可用，无法从工具环境完成真实 PostgreSQL 落库验证。集成测试已更新目标 revision 为 `20260529_0011`，待通道恢复后执行同一命令复验。

## 6. 两轮独立评审

### 6.1 第一轮：需求与边界评审

结论：通过。

发现项：

- 本 Story 只能保存读取结果，不应实现网页抓取器。
- evidence_note 为空允许进入 raw，但不能被误认为可进入 core。

修正结果：

- API/service 只接收并保存外部读取结果。
- 执行结果明确 core 准入阻断属于后续 Story。

### 6.2 第二轮：风控与数据最小化评审

结论：通过，存在一个环境残留验证项。

发现项：

- 登录墙、验证码、访问异常不能继续自动读取，必须变成可复核状态。
- 保存完整网页 HTML 会超出本 Story 数据最小化边界。
- 真实 PostgreSQL migration 未能执行，原因是当前工具审批服务 503。

修正结果：

- `captcha`、`login_wall`、`access_error`、`policy_wall` 映射为 `needs_manual_review`。
- 只保存 `text_excerpt`，不保存完整 HTML。
- 在执行结果中记录真实库验证待复验。

## 7. 残留风险

- 真实 PostgreSQL 尚未执行 `alembic upgrade head`，需要审批通道恢复后复验。
- “无证据不进 core”的实际阻断将在 staging/core 晋级 Story 中实现。

## 8. 下一步建议

继续执行：

`docs/stories/phase-1-small-run/P1-E1-S4-staging-leads.md`

