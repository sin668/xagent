# 第一阶段 PostgreSQL 数据分层基线

创建日期：2026-05-29  
对应 Story：`docs/stories/phase-1-small-run/P1-E1-S1-data-layer-migration-baseline.md`  
对应迁移：`apps/api/alembic/versions/20260529_0009_phase1_data_layer_baseline.py`

## 1. 目标

第一阶段小范围运行统一采用 PostgreSQL 直入库，不再以飞书表格作为主数据载体。本基线明确 `raw`、`staging`、`core`、`audit`、`knowledge` 五层职责，避免 Agent 结果直接污染正式客户库。

后续 Story 必须沿用本分层：

- `raw` 保存公开采集过程和原始证据。
- `staging` 保存 AI 抽取后的候选线索，等待人工复核。
- `core` 保存已通过人工复核的正式业务对象。
- `audit` 保存 AI、Agent、人工操作、规则阻断和风险事件。
- `knowledge` 保存 RAG、SOP、FAQ、关键词、合规规则和失败案例。

## 2. 数据层定义

| 层 | 用途 | 当前/规划表 | 准入原则 |
|---|---|---|---|
| raw | 保存采集任务、候选 URL、公开页面摘要和来源证据 | `collection_tasks`, `candidate_urls`, `page_snapshots` | Low/Medium 可进入受控自动发现；High 仅 `public_discovery_only`；Forbidden 不入库 |
| staging | 保存 AI 抽取后的候选线索和联系方式 | `staging_leads`, `staging_contacts`, `staging_sources` | 必须有关联来源和证据；缺失字段保留 `Unknown`、`null` 或空数组 |
| core | 保存正式客户、联系方式、来源、触达和合规复核 | `customers`, `contact_methods`, `lead_sources`, `outreach_records`, `compliance_reviews` | 无来源、无证据、Invalid/Watch、勿扰、High 未二次复核不得进入待触达 |
| audit | 保存 AI、Agent、人工操作和风险事件 | `ai_audit_logs`, `agent_run_logs`, `review_logs`, `risk_events` | AI 输出必须保存输入引用、输出 JSON、模型、prompt 版本、来源证据和校验结果 |
| knowledge | 保存规则和 RAG 知识 | `knowledge_collections`, `knowledge_items`, `knowledge_embeddings`, `rule_configs` | 只有 `approved` 知识可进入生产 RAG，`deprecated` 知识不得被检索给 Agent |

## 3. 现有 core 表

本 Story 不修改现有 core 表结构，仅在数据层登记表中记录它们的职责：

- `customers`：正式客户主体。
- `contact_methods`：正式联系方式。
- `lead_sources`：正式来源证据。
- `outreach_records`：人工触达记录。
- `compliance_reviews`：C 级线索报价/合同前的合规复核记录。

## 4. 后续 Story 落点

| 表 | 层 | 状态 | Story |
|---|---|---|---|
| `collection_tasks` | raw | planned | `P1-E1-S2` |
| `candidate_urls` | raw | planned | `P1-E1-S2` |
| `page_snapshots` | raw | planned | `P1-E1-S3` |
| `staging_leads` | staging | planned | `P1-E1-S4` |
| `staging_contacts` | staging | planned | `P1-E1-S4` |
| `staging_sources` | staging | planned | `P1-E1-S4` |
| `ai_audit_logs` | audit | existing | MVP baseline，后续扩展 |
| `agent_run_logs` | audit | planned | `P1-E1-S5` |
| `review_logs` | audit | planned | `P1-E1-S5` |
| `risk_events` | audit | planned | `P1-E1-S5` |
| `knowledge_collections` | knowledge | planned | `P1-E5-S1` |
| `knowledge_items` | knowledge | planned | `P1-E5-S1` |
| `knowledge_embeddings` | knowledge | planned | `P1-E5-S1` |
| `rule_configs` | knowledge | planned | `P1-E5-S1` |

## 5. pgvector 检测与安装指引

迁移 `20260529_0009` 会执行：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

如果目标 PostgreSQL 未安装 pgvector，迁移会抛出明确错误：

```text
pgvector extension is required for phase 1 knowledge embeddings.
```

处理步骤：

1. 在 PostgreSQL 服务器安装 pgvector 扩展包。
2. 使用具备扩展权限的数据库用户连接目标库。
3. 执行：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

4. 重新执行 Alembic migration。

## 6. 验证命令

后端验证必须读取 `apps/api/.env` 中的真实 PostgreSQL/Redis 配置，不使用内存 SQLite。

推荐命令：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase1_data_layer_baseline.py -q
/opt/miniconda3/envs/booking-room/bin/alembic upgrade head
```

如使用 shell 环境激活方式：

```bash
conda activate booking-room
python -m pytest tests/test_phase1_data_layer_baseline.py -q
alembic upgrade head
```

## 7. 风控边界

本数据层基线不改变业务风控规则：

- 不自动社交私信。
- 不自动加好友。
- 不登录后批量采集。
- 不反爬规避。
- Invalid 和 Watch 不进入触达队列。
- 勿扰客户不得再次进入触达队列。
- High 来源未二次复核不得进入 core 或触达队列。
- C 级线索报价或合同前必须合规复核。

