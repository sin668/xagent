# Story E1-S2：实现飞书到 PostgreSQL 单向同步

## 基本信息

- Epic：E1 线索数据模型与同步
- Sprint：Sprint 3 MVP 数据底座
- 优先级：P0
- 状态：Done
- 负责人建议：后端工程 + 系统运营

## 用户故事

作为系统运营，我希望飞书表格数据能同步到数据库，以便 MVP CRM 使用稳定数据源。

## 业务价值

保留 PoC 的飞书协作优势，同时让 CRM 具备结构化能力。

## 依赖

- E1-S1 定义客户主体模型

## 任务清单

- [x] 初始化 FastAPI 同步服务。
- [x] 配置飞书 API 凭证读取方式。
- [x] 同步客户线索、渠道来源、车源/报价、触达记录、话术库。
- [x] 写入 PostgreSQL。
- [x] 记录同步日志。
- [x] 处理同步失败和字段缺失。
- [x] 提供手动触发同步入口。
- [x] 编写基础测试。

## 验收标准

- 支持客户线索、渠道来源、车源/报价、触达记录、话术库单向同步。
- 同步日志记录同步时间、对象、成功条数、失败条数。
- 勿扰状态同步后不丢失。
- 同步冲突不反写飞书。

## 非目标

- MVP 不做双向同步。

## QA / 风控检查

- [x] 同步失败不得造成原始飞书数据变更。
- [x] 凭证不得写入代码仓库。

## 交付记录

完成日期：2026-05-28

### 实现文件

- `apps/api/app/settings.py`：读取 `apps/api/.env`，支持未加前缀和 `VEHICLE_LEADS_` 前缀的数据库、Redis、飞书配置。
- `apps/api/app/db/session.py`：使用 `postgresql+asyncpg` 和 `NullPool` 创建真实 PostgreSQL 异步会话，避免后续测试回退内存 SQLite。
- `apps/api/app/api/sync.py`：提供 `POST /sync/feishu` 手动触发入口，dry-run 不写库，非 dry-run 通过真实数据库 session 写入 PostgreSQL。
- `apps/api/app/services/feishu_client.py`：定义飞书只读客户端接口，凭证缺失时返回可审计失败，不写死凭证。
- `apps/api/app/services/feishu_mapping.py`：覆盖客户线索、渠道来源、车源报价、触达记录、话术库五类飞书对象映射。
- `apps/api/app/services/sync_service.py`：实现单向同步、字段缺失失败报告、勿扰状态保留、同步日志记录。
- `apps/api/tests/test_settings.py`：验证配置来自 `apps/api/.env`。
- `apps/api/tests/test_feishu_sync_service.py`：使用真实 PostgreSQL 验证五类对象同步写库、dry-run 不写库、失败记录日志。
- `apps/api/tests/test_integration_postgres_redis.py`：验证真实 PostgreSQL 已建表、Alembic 版本和 Redis 连接。

### 验收命令

```bash
source ~/.zshrc >/dev/null 2>&1 || true
conda activate booking-room
nvm use v22.22.0 >/dev/null
PYTHONPATH=apps/api alembic -c apps/api/alembic.ini upgrade head
```

结果：通过，真实 PostgreSQL 数据库 `xagent` 已升级到 `20260528_0001`。

```bash
PYTHONPATH=apps/api pytest -q apps/api/tests
```

结果：`22 passed, 39 warnings`。警告为 `datetime.utcnow()` 弃用提示，未阻塞本 Story。

```bash
python -m compileall apps/api
```

结果：通过。

### 真实落库确认

`apps/api/.env` 当前连接到：

- PostgreSQL：`8.129.17.71:5432/xagent`
- Redis：`8.129.17.71:6379/0`

已确认 PostgreSQL `public` schema 下存在：

- `ai_audit_logs`
- `alembic_version`
- `channel_risk_rules`
- `compliance_reviews`
- `contact_methods`
- `customers`
- `inventory_items`
- `lead_sources`
- `outreach_records`
- `script_templates`
- `sync_logs`

### 残留风险

- 真实飞书 API 调用仍为接口骨架：当前缺少正式飞书应用权限、表格 token 和字段 ID 对照，未执行真实飞书接口拉取。当前实现保证凭证缺失时可审计失败，不反写飞书。
- `datetime.utcnow()` 存在弃用警告，建议在后续 Story 统一切换为 timezone-aware 时间。
