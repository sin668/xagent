# Story P1-E1-S3：实现 page_snapshots 与来源证据保存

状态：Done  
Sprint：Sprint 1  
优先级：P0  
Epic：P1-E1 PostgreSQL 数据底座

## 用户故事

作为复核人员，我希望看到候选页面标题、公开文本摘要和证据摘录，以便判断线索是否可信。

## 业务价值

支撑“无证据不进 core”的准入规则。

## 依赖

- P1-E1-S2

## 实现范围

- 新增 `page_snapshots`。
- 保存 page_title、text_excerpt、evidence_note、read_status、captured_at、robots_or_policy_note。
- 支持一个 candidate URL 多次读取，但有最新快照。

## 数据/API 影响

- 新增 page snapshot upsert/list API 或 service。

## 验收标准

- 无 candidate_url_id 不允许写入 snapshot。
- evidence_note 为空时允许进入 raw，但不得进入 core。
- read_status 可表达 success、blocked、failed、needs_manual_review。

## 非目标

- 不保存完整网页镜像。
- 不保存评论、粉丝、关系链等非业务必要数据。

## 风控检查

- 登录墙、验证码、访问异常必须写入 read_status，不得继续执行读取任务。

## 实施结果

完成日期：2026-05-29

### 修改文件

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
- `_bmad-output/implementation-artifacts/codex-p1-e1-s3-执行结果.md`

### 验收结果

- 新增 `page_snapshots` migration，revision 为 `20260529_0011`，down_revision 为 `20260529_0010`。
- 新增 `PageSnapshot` 模型并注册到 `app.models`。
- 新增 `PageSnapshotReadStatus`，覆盖 `success`、`blocked`、`failed`、`needs_manual_review`。
- `page_snapshots.candidate_url_id` 为非空外键，关联 `candidate_urls.id`。
- `evidence_note` 允许空字符串进入 raw 层，但后续进入 core 仍需由准入规则阻断。
- `captcha`、`login_wall`、`access_error`、`policy_wall` 会标准化为 `needs_manual_review`。
- 新增 `/raw-collection/page-snapshots` 创建与查询 API。
- 未保存完整网页镜像，未保存评论、粉丝、关系链。
- 真实 PostgreSQL migration 因当前工具沙箱网络权限和外部审批服务 503 暂未完成，已在集成测试中将目标版本更新为 `20260529_0011`，待网络通道可用后执行 `alembic upgrade head` 复验。

### 测试结果

- `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_page_snapshots_foundation.py apps/api/tests/test_raw_collection_foundation.py -q`：15 passed。
- `/opt/miniconda3/envs/booking-room/bin/python -m py_compile ...`：通过。
- `cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic heads`：输出 `20260529_0011 (head)`。
- `cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic upgrade 20260529_0010:head --sql`：成功生成 PostgreSQL offline SQL，包含 `page_snapshots`、`candidate_url_id` 外键、`read_status` 与 `robots_or_policy_note`。

### 风控结果

- 未读取网页正文。
- 未保存完整网页镜像。
- 未保存评论、粉丝、关系链。
- 登录墙、验证码、访问异常可通过 `needs_manual_review` 记录并阻断后续自动读取。
