# Story P1-E1-S2：实现 raw 层采集任务和候选 URL 表

状态：Done  
Sprint：Sprint 1  
优先级：P0  
Epic：P1-E1 PostgreSQL 数据底座

## 用户故事

作为线索运营，我希望每个候选 URL 都能关联任务、渠道和风险等级，以便追溯线索来源。

## 业务价值

让候选数据有来源、有证据、有任务上下文。

## 依赖

- P1-E1-S1

## 实现范围

- 新增 `collection_tasks`。
- 新增 `candidate_urls`。
- 支持 URL hash 幂等。
- 保存 source_platform、source_risk_level、source_usage_type、requires_secondary_verification、discovery_reason。

## 数据/API 影响

- 新增创建/查询 collection task API。
- 新增候选 URL upsert API 或 service。

## 验收标准

- 同一 URL 重复写入不会产生重复记录。
- High URL 默认 `requires_secondary_verification=true`。
- Forbidden 渠道不得创建可执行任务。
- 每条 candidate URL 必须关联 task_id。

## 非目标

- 不读取页面正文。
- 不调用 LLM。

## 风控检查

- High 任务只能标记为 public_discovery_only。
- 禁止动作字段必须可记录。

## 实施结果

完成日期：2026-05-29

### 修改文件

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
- `_bmad-output/implementation-artifacts/codex-p1-e1-s2-执行结果.md`

### 验收结果

- 新增 `collection_tasks` 与 `candidate_urls` migration，revision 为 `20260529_0010`，down_revision 为 `20260529_0009`。
- 新增 `CollectionTask`、`CandidateUrl` 模型并注册到 `app.models`。
- 新增 `RawCollectionService`，支持 URL 标准化、SHA-256 url_hash、collection task 创建、candidate URL upsert。
- 同一 URL 通过标准化 hash 幂等，重复 upsert 返回既有记录并更新候选信息。
- High 风险任务默认 `public_discovery_only`，且拒绝 `automatic_collection`。
- Forbidden 渠道创建可执行任务时抛出明确错误。
- candidate URL 必须关联 `task_id`。
- `forbidden_actions` 持久化在 `collection_tasks`。
- 新增 `/raw-collection/tasks` 和 `/raw-collection/candidate-urls/upsert` API。
- 真实 PostgreSQL migration 因当前工具沙箱网络权限和外部审批服务 503 暂未完成，已在集成测试中将目标版本更新为 `20260529_0010`，待网络通道可用后执行 `alembic upgrade head` 复验。

### 测试结果

- `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_raw_collection_foundation.py apps/api/tests/test_phase1_data_layer_baseline.py -q`：12 passed。
- `/opt/miniconda3/envs/booking-room/bin/python -m py_compile ...`：通过。
- `cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic heads`：输出 `20260529_0010 (head)`。
- `cd apps/api && /opt/miniconda3/envs/booking-room/bin/alembic upgrade 20260529_0009:head --sql`：成功生成 PostgreSQL offline SQL，包含 `collection_tasks`、`candidate_urls`、`uq_candidate_urls_url_hash` 和 task 外键。

### 风控结果

- 未读取页面正文。
- 未调用 LLM。
- High 任务只能使用 `public_discovery_only`。
- Forbidden 渠道不得创建可执行任务。
- 禁止动作字段已在 `collection_tasks.forbidden_actions` 中保留。
