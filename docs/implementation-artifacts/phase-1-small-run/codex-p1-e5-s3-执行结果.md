# P1-E5-S3 执行结果

Story：`docs/stories/phase-1-small-run/P1-E5-S3-knowledge-search-api.md`  
执行人：Codex  
执行日期：2026-05-29  
状态：已完成本地实现、TDD、定向回归、编译检查和 Story 状态回写；真实 PostgreSQL/pgvector 检索验证受当前沙箱出网限制影响，待可出网环境复验

## 1. 执行说明

本 Story 按 `docs/AI协同开发执行标准.md`、第一阶段实施计划和 superpowers TDD/verification 规范执行。用户已明确要求不执行 Story lock 操作，因此本 Story 未执行任何锁命令。

## 2. 修改文件

- `apps/api/app/services/knowledge_search.py`
- `apps/api/app/schemas/knowledge.py`
- `apps/api/app/api/knowledge.py`
- `apps/api/tests/test_knowledge_search_api.py`
- `docs/stories/phase-1-small-run/P1-E5-S3-knowledge-search-api.md`
- `_bmad-output/implementation-artifacts/codex-p1-e5-s3-执行结果.md`

## 3. 实现内容

### 3.1 知识检索服务

新增 `KnowledgeSearchService`：

- `resolve_search_mode`
- `item_is_production_rag_eligible`
- `item_matches_filters`
- `keyword_score`
- `keyword_fallback_search`
- `search`

支持过滤：

- `collection`
- `country`
- `language`
- `channel`
- `query`

### 3.2 向量检索与 fallback

支持：

- 有 `query_embedding` 时走 pgvector 近邻排序：`embedding <-> query_vector`
- 无 `query_embedding` 且允许 fallback 时使用关键词 fallback
- pgvector 查询失败且允许 fallback 时使用关键词 fallback，并返回明确 `fallback_reason`
- 禁止 fallback 且 pgvector 不可用时返回明确错误

### 3.3 API

新增：

```text
POST /knowledge/search
```

请求：

```json
{
  "collection": "channel_sop",
  "country": "Russia",
  "language": "zh",
  "channel": "maps",
  "query": "公开页面",
  "query_embedding": null,
  "allow_keyword_fallback": true,
  "limit": 10
}
```

响应：

- `items`
- `search_mode`
- `fallback_reason`

## 4. 验收结果

| 验收项 | 结论 | 证据 |
|---|---|---|
| 支持按 collection 检索 | 通过 | `item_matches_filters(collection=...)` |
| 支持按 country 检索 | 通过 | `item_matches_filters(country=...)` |
| 支持按 language 检索 | 通过 | `item_matches_filters(language=...)` |
| 支持按 channel 检索 | 通过 | `item_matches_filters(channel=...)` |
| 支持按 query 检索 | 通过 | `keyword_score` |
| 支持向量检索 | 通过 | `KnowledgeEmbedding.embedding <-> query_vector` |
| 支持关键词 fallback | 通过 | `keyword_fallback_search` |
| 只返回 approved 条目 | 通过 | `status=active` + `review_status=approved` |
| 查询 channel_sop 只返回 approved SOP | 通过 | 测试覆盖 |
| 查询 faq/script_template 可按语言过滤 | 通过 | 测试覆盖 |
| pgvector 不可用时明确 fallback | 通过 | `fallback_reason` |
| 不实现多模型 rerank | 通过 | 仅向量排序或关键词 fallback |
| 不返回 deprecated 或未审核合规规则 | 通过 | `item_is_production_rag_eligible` + status 排除 |

## 5. 测试记录

### 5.1 测试先行

首次运行：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_knowledge_search_api.py -q
```

结果：

```text
ModuleNotFoundError: No module named 'app.services.knowledge_search'
```

### 5.2 实现后测试

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_knowledge_search_api.py -q
```

结果：

```text
5 passed in 0.27s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/knowledge_search.py apps/api/app/schemas/knowledge.py apps/api/app/api/knowledge.py
```

结果：通过。

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_knowledge_search_api.py apps/api/tests/test_knowledge_schema.py apps/api/tests/test_phase_one_knowledge_import.py -q
```

结果：

```text
16 passed in 0.22s
```

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m alembic heads
```

结果：

```text
20260529_0018 (head)
```

## 6. 两轮独立评审

### 6.1 第一轮：RAG 准入和过滤评审

结论：通过。

发现项：

- 生产检索必须强制 `active + approved`，不能让未审核知识通过 query/filter 绕过。
- `deprecated` 即使曾经 approved，也不能进入 RAG。
- channel 过滤应基于 `applicable_channels`，而不是只看 collection 名称。

修正结果：

- `item_is_production_rag_eligible` 固定复用 `KnowledgeService.is_rag_eligible`。
- `item_matches_filters` 显式排除 `deprecated`。
- 增加 channel/country/language 组合过滤测试。

### 6.2 第二轮：向量 fallback 和排序语义评审

结论：通过，存在真实 pgvector 检索残留验证项。

发现项：

- 没有 `query_embedding` 时应明确使用关键词 fallback，而不是静默假装向量检索。
- 向量检索返回的 score 应该越高越好。
- 当前 Codex 沙箱无法连接真实 PostgreSQL/pgvector。

修正结果：

- `resolve_search_mode` 返回 `search_mode` 和 `fallback_reason`。
- 向量结果 score 使用 `1/rank`。
- 将真实 pgvector 验证阻塞原因记录为残留风险。

## 7. 残留风险

- 当前 Codex 沙箱无法连接真实 PostgreSQL/pgvector，`POST /knowledge/search` 的真实向量检索需在可出网环境复验。
- 关键词 fallback 为基础匹配，不做多模型 rerank；更复杂排序可在后续 Story 或优化阶段处理。

## 8. 下一步建议

继续执行：

`docs/stories/phase-1-small-run/P1-E5-S4-rag-in-llm-prompts.md`

