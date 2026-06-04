# P1-E1-S4 执行结果

Story：`docs/stories/phase-1-small-run/P1-E1-S4-staging-leads.md`  
执行人：Codex  
执行日期：2026-05-29  
状态：已完成本地实现与可用验证；真实 PostgreSQL migration 待审批通道恢复后复验

## 1. 执行说明

本 Story 按第一阶段实施推进计划执行。用户已明确要求后续不执行任何 Story 锁操作，因此本 Story 未执行锁命令。

## 2. 修改文件

- `apps/api/alembic/versions/20260529_0012_staging_leads.py`
- `apps/api/app/models/enums.py`
- `apps/api/app/models/staging_lead.py`
- `apps/api/app/models/candidate_url.py`
- `apps/api/app/models/__init__.py`
- `apps/api/app/services/staging_leads.py`
- `apps/api/app/schemas/staging_leads.py`
- `apps/api/app/api/staging_leads.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_staging_leads_foundation.py`
- `apps/api/tests/test_integration_postgres_redis.py`
- `docs/stories/phase-1-small-run/P1-E1-S4-staging-leads.md`
- `_bmad-output/implementation-artifacts/codex-p1-e1-s4-执行结果.md`

## 3. 实现内容

### 3.1 数据库迁移

新增 migration：`20260529_0012_staging_leads.py`

新增表：

- `staging_leads`

关键字段：

- `candidate_url_id`
- `customer_name`
- `country`
- `city`
- `customer_type`
- `contacts_json`
- `activity_level`
- `scale_signal`
- `import_used_car_relevance`
- `source_evidence`
- `recommended_grade`
- `recommended_reason`
- `missing_fields`
- `review_status`
- `queue_status`
- `dedupe_key`
- `requires_compliance_review`

### 3.2 后端模型与服务

新增模型：

- `StagingLead`

新增枚举：

- `StagingReviewStatus`
- `StagingQueueStatus`

新增服务：

- `StagingLeadService.validate_candidate_url_id`
- `StagingLeadService.normalize_payload`
- `StagingLeadService.default_queue_status`
- `StagingLeadService.default_review_status`
- `StagingLeadService.default_requires_compliance_review`
- `StagingLeadService.build_dedupe_key`
- `StagingLeadService.create_staging_lead`
- `StagingLeadService.list_staging_leads`
- `StagingLeadService.get_staging_lead`

### 3.3 API

新增 API：

- `POST /staging-leads`
- `GET /staging-leads`
- `GET /staging-leads/{lead_id}`
- `PATCH /staging-leads/{lead_id}`

## 4. 验收结果

| 验收项 | 结论 | 证据 |
|---|---|---|
| 缺失字段允许 Unknown/null/[] | 通过 | `normalize_payload` 测试通过 |
| Invalid/Watch 默认 queue_status 为 not_eligible | 通过 | `default_queue_status` 测试通过 |
| High 来源默认 review_status 为 needs_secondary_verification | 通过 | `default_review_status` 测试通过 |
| C 级默认 requires_compliance_review=true | 通过 | `default_requires_compliance_review` 测试通过 |
| 支持候选 URL 关联 | 通过 | `candidate_url_id` 非空外键 |
| 不实现人工复核晋级 core | 通过 | 未新增 promote/core 写入逻辑 |
| 不允许无来源 URL 的 staging lead 晋级 core | 通过 | 本 Story 不做晋级；staging lead 创建必须有关联 candidate_url_id |

## 5. 测试记录

### 5.1 测试先行

首次运行：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_staging_leads_foundation.py -q
```

结果：失败，原因是 `StagingQueueStatus` 和 `StagingReviewStatus` 尚未实现。

### 5.2 实现后测试

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_staging_leads_foundation.py apps/api/tests/test_page_snapshots_foundation.py -q
```

结果：

```text
13 passed in 0.34s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/models/enums.py apps/api/app/models/staging_lead.py apps/api/app/models/candidate_url.py apps/api/app/services/staging_leads.py apps/api/app/schemas/staging_leads.py apps/api/app/api/staging_leads.py apps/api/alembic/versions/20260529_0012_staging_leads.py apps/api/tests/test_staging_leads_foundation.py apps/api/tests/test_integration_postgres_redis.py
```

结果：通过。

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/alembic heads
```

结果：

```text
20260529_0012 (head)
```

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/alembic upgrade 20260529_0011:head --sql
```

结果：通过，成功生成 PostgreSQL offline SQL，包含 `staging_leads`、`candidate_url_id` 外键、`contacts_json`、`review_status`、`queue_status` 和 `requires_compliance_review`。

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

结论：当前工具审批服务不可用，无法从工具环境完成真实 PostgreSQL 落库验证。集成测试已更新目标 revision 为 `20260529_0012`，待通道恢复后执行同一命令复验。

## 6. 两轮独立评审

### 6.1 第一轮：需求与边界评审

结论：通过。

发现项：

- 本 Story 不能实现 staging 晋级 core，否则会进入 `P1-E3-S3` 范围。
- `contacts_json` 和 `missing_fields` 必须允许空数组，不能强迫 AI 编造数据。

修正结果：

- 仅实现 staging lead 创建、查询和字段修正。
- `contacts_json` 与 `missing_fields` 默认 `[]`。

### 6.2 第二轮：风控与准入评审

结论：通过，存在一个环境残留验证项。

发现项：

- Invalid/Watch 必须从 staging 阶段默认阻断触达队列。
- High 来源必须默认二次复核。
- C 级必须默认合规复核。
- 真实 PostgreSQL migration 未能执行，原因是当前工具审批服务 503。

修正结果：

- `default_queue_status` 将 Invalid/Watch 置为 `not_eligible`。
- `default_review_status` 将 High 置为 `needs_secondary_verification`。
- `default_requires_compliance_review` 将 C 级置为 `true`。
- 在执行结果中记录真实库验证待复验。

## 7. 残留风险

- 真实 PostgreSQL 尚未执行 `alembic upgrade head`，需要审批通道恢复后复验。
- “无来源 URL 不得晋级 core”的强阻断将在 `P1-E3-S3` 实现。

## 8. 下一步建议

继续执行：

`docs/stories/phase-1-small-run/P1-E1-S5-audit-risk-logs.md`

