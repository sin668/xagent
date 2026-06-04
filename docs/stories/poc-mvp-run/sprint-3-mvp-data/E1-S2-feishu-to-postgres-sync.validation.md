# E1-S2 Validation：飞书到 PostgreSQL 单向同步

验证日期：2026-05-28  
Story：`E1-S2 实现飞书到 PostgreSQL 单向同步`

## 输入包检查

| 项目 | 结果 | 证据 |
|---|---|---|
| Story ID | 通过 | `docs/stories/sprint-3-mvp-data/E1-S2-feishu-to-postgres-sync.md` |
| 用户价值 | 通过 | Story 用户故事定义系统运营需要稳定数据库数据源 |
| 依赖 | 通过 | `E1-S1` 已提供客户主体、来源、联系方式、触达、报价、风险、审计等模型 |
| 技术栈 | 通过 | FastAPI、SQLAlchemy、Alembic、PostgreSQL、Redis；环境使用 `conda activate booking-room` 和 `nvm use v22.22.0` |
| 强约束 | 通过 | 不自动社交私信、不自动加好友、不反写飞书、不使用内存 SQLite 测试 |

## 验收映射

| 验收项 | 当前证据 | 结论 |
|---|---|---|
| 支持客户线索、渠道来源、车源/报价、触达记录、话术库单向同步 | `SUPPORTED_OBJECTS == ["客户线索", "渠道来源", "车源报价", "触达记录", "话术库"]`；`test_sync_writes_all_five_feishu_objects_to_postgres` 使用真实 PostgreSQL 验证五类对象均写入 | 通过 |
| 写入 PostgreSQL | `apps/api/app/db/session.py` 使用 `postgresql+asyncpg`；`test_real_postgres_has_mvp_data_foundation_tables` 验证真实库表 | 通过 |
| 同步日志记录同步时间、对象、成功条数、失败条数 | `SyncLog` 包含 `started_at`、`finished_at`、`object_name`、`success_count`、`failure_count`；同步成功和失败测试均断言日志 | 通过 |
| 勿扰状态同步后不丢失 | `test_customer_mapping_preserves_do_not_contact_status` 验证 `是否勿扰=是` 映射到 `do_not_contact=True` 与 `do_not_contact` 状态 | 通过 |
| 同步冲突不反写飞书 | `FeishuClient` 仅定义 `list_records` 只读接口；同步服务没有任何飞书写入方法 | 通过 |
| 同步失败不得造成原始飞书数据变更 | `test_sync_failure_is_logged_and_does_not_mutate_feishu_client` 验证字段缺失只记录失败，不写客户数据；飞书客户端为只读协议 | 通过 |
| 凭证不得写入代码仓库 | `settings.py` 从 `apps/api/.env` 读取配置；代码未硬编码飞书凭证、数据库密码或 Redis 密码 | 通过 |
| 后续不再使用内存 SQLite 测试 | `rg -n "sqlite|memory|create_engine"` 未发现测试继续使用 SQLite；同步测试使用真实 PostgreSQL | 通过 |

## 真实环境验证

`apps/api/.env` 当前连接元信息：

| 服务 | 结果 |
|---|---|
| PostgreSQL | `postgresql+asyncpg://***@8.129.17.71:5432/xagent` |
| Redis | `redis://***@8.129.17.71:6379/0` |

真实 PostgreSQL 查询结果：

| 项目 | 结果 |
|---|---|
| `current_database()` | `xagent` |
| `current_schema()` | `public` |
| `current_user` | `postgres` |
| Alembic 版本 | `20260528_0001` |

已创建表：

- `public.ai_audit_logs`
- `public.alembic_version`
- `public.channel_risk_rules`
- `public.compliance_reviews`
- `public.contact_methods`
- `public.customers`
- `public.inventory_items`
- `public.lead_sources`
- `public.outreach_records`
- `public.script_templates`
- `public.sync_logs`

## 验证命令

```bash
source ~/.zshrc >/dev/null 2>&1 || true
conda activate booking-room
nvm use v22.22.0 >/dev/null
PYTHONPATH=apps/api alembic -c apps/api/alembic.ini upgrade head
```

结果：通过。

```bash
PYTHONPATH=apps/api alembic -c apps/api/alembic.ini current
PYTHONPATH=apps/api alembic -c apps/api/alembic.ini history
```

结果：

```text
20260528_0001 (head)
<base> -> 20260528_0001 (head), Initial MVP data foundation.
```

```bash
PYTHONPATH=apps/api pytest -q apps/api/tests
```

结果：

```text
22 passed, 39 warnings
```

```bash
python -m compileall apps/api
```

结果：通过。

```bash
PYTHONPATH=apps/api python - <<'PY'
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
print(client.get('/health').json())
print(client.post('/sync/feishu', json={'object_names':['客户线索'], 'dry_run': True}).json())
PY
```

结果：

```text
{'status': 'ok', 'service': 'vehicle-leads-api'}
{'status': 'failed', 'dry_run': True, 'results': [{'object_name': '客户线索', 'success_count': 0, 'failure_count': 1, 'skipped_count': 0, 'errors': ['客户线索 fetch failed: Feishu credentials are not configured.']}]}
```

## 两轮独立评审记录

### 第一轮评审

结论：发现一个实质问题，初版验证只覆盖客户线索单表，不能充分证明五张飞书表均可同步到 PostgreSQL。

发现项：

- `test_customer_sync_writes_customer_source_contacts_and_log` 只能证明客户线索及其来源、联系方式写入成功。
- Story 验收要求覆盖客户线索、渠道来源、车源/报价、触达记录、话术库五张表。

修正结果：

- 新增 `test_sync_writes_all_five_feishu_objects_to_postgres`。
- 测试使用真实 PostgreSQL 写入五类对象，并断言五类对象均创建成功。
- 重新运行 `PYTHONPATH=apps/api pytest -q apps/api/tests/test_feishu_sync_service.py`，结果 `8 passed`。

### 第二轮评审

结论：未发现新增实质阻塞问题。

发现项：

- 真实 PostgreSQL 与 Redis 集成测试通过。
- `rg -n "sqlite|memory|create_engine"` 未发现测试继续使用内存 SQLite。
- API dry-run 在飞书凭证缺失时返回可审计失败，符合“凭证不得入仓库”和“不反写飞书”的边界。
- 存在 `datetime.utcnow()` 弃用警告，但不影响本 Story 验收，建议后续统一处理。

修正结果：

- 无需新增修正。
- 保留 `datetime.utcnow()` 警告为后续技术债。

## 残留风险

| 风险 | 影响 | 后续处理 |
|---|---|---|
| 真实飞书 API 尚未接入 | 当前只能验证同步服务、映射、日志、数据库写入和凭证缺失失败路径；不能验证飞书接口字段 ID | 后续拿到飞书应用权限、表 token、字段 ID 后补真实 Feishu API client |
| `datetime.utcnow()` 弃用警告 | 长期可能受 Python/SQLAlchemy 行为变化影响 | 后续 Story 统一切换为 timezone-aware UTC 时间 |

## 结论

E1-S2 已完成。当前实现满足飞书五张表到 PostgreSQL 的单向同步服务、手动触发入口、同步日志、失败处理、勿扰保留、凭证外置和真实 PostgreSQL/Redis 验证要求。MVP 非目标中的双向同步未实现，符合范围边界。

