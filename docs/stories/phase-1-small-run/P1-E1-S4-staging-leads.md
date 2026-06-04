# Story P1-E1-S4：实现 staging_leads 候选线索表

状态：Done  
Sprint：Sprint 1  
优先级：P0  
Epic：P1-E1 PostgreSQL 数据底座

## 用户故事

作为线索运营，我希望 AI 抽取结果先进入 staging，以便人工复核后再进入正式客户库。

## 业务价值

防止 AI 错误或低质量数据污染 core。

## 依赖

- P1-E1-S3

## 实现范围

- 新增 `staging_leads`。
- 字段覆盖客户名称、国家、城市、客户类型、contacts_json、经营信号、证据、推荐等级、推荐原因、缺失字段、review_status、queue_status、dedupe_key、requires_compliance_review。
- 支持候选 URL 关联。

## 数据/API 影响

- 新增 staging lead create/list/detail/update API。

## 验收标准

- 缺失字段允许 Unknown/null/[]。
- Invalid/Watch 默认 queue_status 为 not_eligible。
- High 来源默认 review_status 为 needs_secondary_verification。
- C 级默认 requires_compliance_review=true。

## 非目标

- 不实现人工复核晋级 core。

## 风控检查

- 不允许无来源 URL 的 staging lead 晋级 core。

## 实施结果

完成日期：2026-05-29

### 修改文件

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
- `_bmad-output/implementation-artifacts/codex-p1-e1-s4-执行结果.md`

### 验收结果

- 新增 `staging_leads` migration，revision 为 `20260529_0012`，down_revision 为 `20260529_0011`。
- 新增 `StagingLead` 模型并注册到 `app.models`。
- 新增 `StagingReviewStatus` 与 `StagingQueueStatus`。
- 字段覆盖客户名称、国家、城市、客户类型、contacts_json、经营信号、证据、推荐等级、推荐原因、缺失字段、review_status、queue_status、dedupe_key、requires_compliance_review。
- `candidate_url_id` 为非空外键，关联 `candidate_urls.id`。
- 缺失字段保留 `Unknown`、`null` 或空数组。
- Invalid/Watch 默认 `queue_status=not_eligible`。
- High 来源默认 `review_status=needs_secondary_verification`。
- C 级默认 `requires_compliance_review=true`。
- 新增 `/staging-leads` create/list/detail/update API。
- 真实 PostgreSQL migration 因当前工具沙箱网络权限和外部审批服务 503 暂未完成，已在集成测试中将目标版本更新为 `20260529_0012`，待网络通道可用后执行 `alembic upgrade head` 复验。

### 测试结果

- `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_staging_leads_foundation.py apps/api/tests/test_page_snapshots_foundation.py -q`：13 passed。
- `/opt/miniconda3/envs/booking-room/bin/python -m py_compile ...`：通过。
- `cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic heads`：输出 `20260529_0012 (head)`。
- `cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic upgrade 20260529_0011:head --sql`：成功生成 PostgreSQL offline SQL，包含 `staging_leads`、`candidate_url_id` 外键、`contacts_json`、`review_status`、`queue_status`、`requires_compliance_review`。

### 风控结果

- 未实现人工复核晋级 core。
- staging lead 必须关联 `candidate_url_id`。
- 无来源 URL 的 staging lead 无法被创建为合规 staging 记录。
- Invalid/Watch 默认不可进入触达队列。
- High 来源默认需要二次复核。
- C 级默认需要合规复核。
