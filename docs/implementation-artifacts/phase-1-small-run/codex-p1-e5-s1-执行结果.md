# P1-E5-S1 执行结果

Story：`docs/stories/phase-1-small-run/P1-E5-S1-pgvector-knowledge-schema.md`  
执行人：Codex  
执行日期：2026-05-29  
状态：已完成本地实现、迁移、TDD、定向回归、编译检查、离线 SQL 验证和 Story 状态回写；真实 PostgreSQL migration/联调验证受当前沙箱出网限制影响，待可出网环境复验

## 1. 执行说明

本 Story 按 `docs/AI协同开发执行标准.md`、第一阶段实施计划、产品技术设计和 superpowers TDD/verification 规范执行。用户已明确要求不执行 Story lock 操作，因此本 Story 未执行任何锁命令。

## 2. 修改文件

- `apps/api/alembic/versions/20260529_0018_knowledge_pgvector_schema.py`
- `apps/api/app/db/types.py`
- `apps/api/app/models/enums.py`
- `apps/api/app/models/knowledge.py`
- `apps/api/app/models/__init__.py`
- `apps/api/app/services/knowledge.py`
- `apps/api/app/schemas/knowledge.py`
- `apps/api/app/api/knowledge.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_knowledge_schema.py`
- `docs/stories/phase-1-small-run/P1-E5-S1-pgvector-knowledge-schema.md`
- `_bmad-output/implementation-artifacts/codex-p1-e5-s1-执行结果.md`

## 3. 实现内容

### 3.1 知识库表

新增 migration：

```text
20260529_0018_knowledge_pgvector_schema.py
```

新增表：

- `knowledge_collections`
- `knowledge_items`
- `knowledge_embeddings`

关键字段覆盖：

- `status`
- `review_status`
- `version`
- `source_ref`
- `applicable_channels`
- `metadata_json`
- `embedding vector(1536)`
- `embedding_status`
- `error_message`

### 3.2 pgvector 类型

新增 `VectorType(1536)`：

- Alembic SQL 生成 `vector(1536)`
- Python list 写入时转换为 pgvector 字符串格式
- pgvector 扩展由 migration 执行 `CREATE EXTENSION IF NOT EXISTS vector`

### 3.3 知识库服务和 CRUD API

新增 `KnowledgeService`：

- `create_collection`
- `list_collections`
- `create_item`
- `list_items`
- `create_embedding`
- `is_rag_eligible`
- `production_rag_filters`
- `build_embedding_payload`

新增 API：

```text
POST /knowledge/collections
GET /knowledge/collections
POST /knowledge/items
GET /knowledge/items
POST /knowledge/items/{item_id}/embedding
```

## 4. 验收结果

| 验收项 | 结论 | 证据 |
|---|---|---|
| 新增 knowledge_collections | 通过 | migration + model |
| 新增 knowledge_items | 通过 | migration + model |
| 新增 knowledge_embeddings | 通过 | migration + model |
| 支持 status、review_status、version、source_ref | 通过 | 三层模型和 migration 字段 |
| 配置 pgvector embedding 字段 | 通过 | `embedding vector(1536)` |
| 新增知识库 CRUD API | 通过 | `/knowledge/*` 路由 |
| 只有 approved 知识可被生产检索 | 通过 | `is_rag_eligible(active, approved)` |
| deprecated 知识不得进入 RAG | 通过 | `production_rag_filters.exclude_statuses` |
| embedding 写入失败不影响结构化知识保存，但要记录错误 | 通过 | `build_embedding_payload(error_message)` 生成 `embedding_status=failed` |
| 不做复杂知识图谱 | 通过 | 仅 collection/item/embedding 三表 |
| 合规规则不可仅作为语义建议 | 通过 | 本 Story 只建知识 schema，不替代结构化规则执行 |

## 5. 测试记录

### 5.1 测试先行

首次运行：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_knowledge_schema.py -q
```

结果：

```text
ImportError: cannot import name 'KnowledgeItemStatus'
```

### 5.2 实现后测试

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_knowledge_schema.py -q
```

结果：

```text
6 passed in 0.27s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/db/types.py apps/api/app/models/knowledge.py apps/api/app/services/knowledge.py apps/api/app/schemas/knowledge.py apps/api/app/api/knowledge.py apps/api/alembic/versions/20260529_0018_knowledge_pgvector_schema.py apps/api/app/main.py
```

结果：通过。

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_knowledge_schema.py apps/api/tests/test_phase1_data_layer_baseline.py apps/api/tests/test_failed_cases_library.py -q
```

结果：

```text
15 passed in 0.30s
```

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m alembic heads
```

结果：

```text
20260529_0018 (head)
```

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m alembic upgrade 20260529_0017:head --sql
```

结果：成功生成 PostgreSQL 离线 SQL，包含：

```text
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE knowledge_collections ...
CREATE TABLE knowledge_items ...
CREATE TABLE knowledge_embeddings ...
embedding vector(1536)
```

## 6. 两轮独立评审

### 6.1 第一轮：RAG 准入和数据结构评审

结论：通过。

发现项：

- 生产 RAG 准入不能只看 `review_status=approved`，还必须排除 `deprecated`。
- embedding 失败不能影响知识条目的结构化保存。
- 知识库 schema 不能替代结构化合规规则执行。

修正结果：

- `is_rag_eligible` 要求 `status=active` 且 `review_status=approved`。
- `production_rag_filters` 明确 `exclude_statuses=[deprecated]`。
- `KnowledgeEmbedding` 增加 `embedding_status` 和 `error_message`。

### 6.2 第二轮：pgvector、迁移和真实环境风险评审

结论：通过，存在真实 PostgreSQL migration 残留验证项。

发现项：

- 自定义 pgvector 类型需要能把 Python list 转为 PostgreSQL pgvector 可接受的字符串。
- Alembic 需要能生成 `vector(1536)`，不能退化成普通 JSON/Text。
- 当前 Codex 沙箱无法连接真实 PostgreSQL。

修正结果：

- `VectorType.bind_processor` 将 list 转为 `[0.1,0.2,...]` 字符串。
- 离线 SQL 已确认 `embedding vector(1536)`。
- 将真实库验证阻塞原因记录为残留风险。

## 7. 残留风险

- 当前 Codex 沙箱无法连接真实 PostgreSQL，`20260529_0018_knowledge_pgvector_schema.py` 需在可出网环境执行 `alembic upgrade head` 复验。
- 目标 PostgreSQL 必须安装 pgvector；migration 会执行 `CREATE EXTENSION IF NOT EXISTS vector`。
- 当前仅完成 schema 与 CRUD，知识导入由 P1-E5-S2 承接，检索 API 由 P1-E5-S3 承接。

## 8. 下一步建议

继续执行：

`docs/stories/phase-1-small-run/P1-E5-S2-import-phase-one-knowledge.md`

