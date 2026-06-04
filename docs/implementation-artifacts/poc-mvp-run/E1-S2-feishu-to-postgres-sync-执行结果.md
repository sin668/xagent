# E1-S2 飞书到 PostgreSQL 单向同步执行结果

执行日期：2026-05-28  
Story：`docs/stories/sprint-3-mvp-data/E1-S2-feishu-to-postgres-sync.md`  
Story lock owner：`codex-E1-S2-feishu-to-postgres-sync`

## 执行范围

- 修复 API 配置读取路径，确保 `apps/api/.env` 中的 PostgreSQL 和 Redis 配置生效。
- 使用真实 PostgreSQL/Redis 环境验证，不再使用内存 SQLite 测试。
- 实现飞书五张表到 PostgreSQL 的单向同步服务骨架：
  - 客户线索
  - 渠道来源
  - 车源报价
  - 触达记录
  - 话术库
- 提供 `POST /sync/feishu` 手动触发入口。
- 实现 dry-run 与非 dry-run 分支：dry-run 只校验和计数，不写数据库；非 dry-run 写 PostgreSQL 并记录同步日志。
- 保留飞书只读边界：当前仅定义 `list_records`，没有任何反写飞书动作。
- 对字段缺失、飞书凭证缺失、拉取失败和写库失败进行可审计失败记录。

## 主要改动

### 后端实现

- `apps/api/app/settings.py`
  - 将 `.env` 路径修正为 `apps/api/.env`。
  - 支持 `DATABASE_URL`、`REDIS_URL`、`FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`FEISHU_BITABLE_APP_TOKEN` 以及 `VEHICLE_LEADS_` 前缀变量。
- `apps/api/app/db/session.py`
  - 使用 `postgresql+asyncpg` 创建 SQLAlchemy 异步会话。
  - 使用 `NullPool` 避免 pytest 多事件循环场景下复用 asyncpg 连接。
- `apps/api/app/api/sync.py`
  - 增加异步数据库 session 注入。
  - 通过 `AsyncSession.run_sync()` 复用同步 ORM 写入逻辑。
  - 非 dry-run 时提交 PostgreSQL 事务。
- `apps/api/app/services/feishu_mapping.py`
  - 覆盖五张飞书表字段映射。
- `apps/api/app/services/sync_service.py`
  - 实现五类对象 upsert、同步日志、失败汇总、勿扰状态写入。

### 测试

- `apps/api/tests/test_settings.py`
  - 验证配置从 `apps/api/.env` 读取，并且数据库/Redis 不再回落 localhost 默认值。
- `apps/api/tests/test_feishu_sync_service.py`
  - 使用真实 PostgreSQL 验证 dry-run 不写库。
  - 使用真实 PostgreSQL 验证客户线索写入客户、来源、联系方式和同步日志。
  - 使用真实 PostgreSQL 验证五张飞书表均能写入对应表。
  - 验证字段缺失和拉取失败会记录失败日志，不写客户数据，不反写飞书。
- `apps/api/tests/test_integration_postgres_redis.py`
  - 验证真实 PostgreSQL 里存在 MVP 数据底座表。
  - 验证 `alembic_version` 为 `20260528_0001`。
  - 验证真实 Redis `PING` 成功。

## 真实环境验证

连接元信息来自 `apps/api/.env`，未输出任何密码：

- PostgreSQL：`8.129.17.71:5432/xagent`
- Redis：`8.129.17.71:6379/0`

真实 PostgreSQL 查询确认：

- `current_database()`：`xagent`
- `current_schema()`：`public`
- `current_user`：`postgres`
- Alembic revision：`20260528_0001`

真实落库表：

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

## 验收结果

| 验收项 | 结果 | 证据 |
|---|---|---|
| 支持五张飞书表单向同步 | 通过 | `test_sync_writes_all_five_feishu_objects_to_postgres` |
| 写入 PostgreSQL | 通过 | 真实 PostgreSQL 集成测试通过，表已落在 `xagent.public` |
| 同步日志记录时间、对象、成功条数、失败条数 | 通过 | `SyncLog` 模型与同步成功/失败测试 |
| 勿扰状态同步后不丢失 | 通过 | `test_customer_mapping_preserves_do_not_contact_status` |
| 同步冲突不反写飞书 | 通过 | 飞书客户端协议只暴露 `list_records`；代码无飞书写接口 |
| 凭证不得写入代码仓库 | 通过 | 凭证从 `.env` 读取；代码未硬编码敏感值 |
| 后续不使用内存 SQLite 测试 | 通过 | `rg -n "sqlite|memory|create_engine"` 未发现 SQLite 测试残留 |

## 验证命令与结果

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

## 两轮独立评审

### 第一轮评审

结论：初始实现存在验收证据不足问题，必须补强。

发现项：

- 初始真实 PostgreSQL 写库测试只覆盖客户线索表，未直接证明渠道来源、车源报价、触达记录和话术库均可同步。
- Story 验收明确要求五张飞书表均支持单向同步。

修正结果：

- 新增五对象真实写库测试 `test_sync_writes_all_five_feishu_objects_to_postgres`。
- 测试数据统一使用 `TEST-E1S2-` 前缀，测试前后只清理测试数据，避免误删业务数据。
- 重新运行同步服务测试：`8 passed`。

### 第二轮评审

结论：连续第二轮未发现新增实质阻塞问题，当前 Story 可视为完成。

发现项：

- 全量测试 `22 passed`。
- 真实 PostgreSQL 已落表，`xagent.public` 下存在 11 张表。
- Redis 真实 `PING` 成功。
- 配置读取已从错误的 `apps/.env` 修正为 `apps/api/.env`。
- API dry-run 在飞书凭证缺失时返回可审计失败，符合凭证外置和不反写边界。
- 仅剩 `datetime.utcnow()` 弃用警告，属于后续技术债，不阻塞 E1-S2。

修正结果：

- 无新增修正。
- 在 validation 和 Story 交付记录中明确残留风险。

## 残留风险与后续建议

| 风险 | 当前处理 | 后续建议 |
|---|---|---|
| 真实飞书 API 未接入 | 当前 Feishu API client 在凭证缺失或权限未具备时返回可审计失败 | 拿到飞书应用权限、表 token、字段 ID 后补真实 client |
| `datetime.utcnow()` 弃用警告 | 不阻塞本 Story | 后续统一切换为 timezone-aware UTC 时间 |
| 当前目录 Git 元数据异常 | `git status` 报不是 Git 仓库，但 Story lock 可用 | 后续由仓库维护者核查 `.git` 结构或当前工作区挂载方式 |

## 下一接力点

Prompt 8 的下一个 Story：`E6-S1 渠道风险等级配置`。

