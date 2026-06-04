# P1-E5-S4 执行结果

Story：`docs/stories/phase-1-small-run/P1-E5-S4-rag-in-llm-prompts.md`  
执行人：Codex  
执行日期：2026-05-29  
状态：已完成本地实现、TDD、定向回归、编译检查、两轮复核和 Story 状态回写

## 1. 执行说明

本 Story 按 `docs/AI协同开发执行标准.md`、第一阶段实施推进计划和 superpowers TDD 规范执行。用户已明确要求不执行 Story lock 操作，因此本 Story 未执行任何锁命令。

## 2. 修改文件

- `apps/api/app/services/rag_prompt_context.py`
- `apps/api/app/services/llm_lead_extraction.py`
- `apps/api/app/services/llm_lead_grading.py`
- `apps/api/app/services/outreach_draft.py`
- `apps/api/app/schemas/outreach_draft.py`
- `apps/api/tests/test_rag_in_llm_prompts.py`
- `docs/stories/phase-1-small-run/P1-E5-S4-rag-in-llm-prompts.md`
- `_bmad-output/implementation-artifacts/codex-p1-e5-s4-执行结果.md`

## 3. 实现内容

### 3.1 RAG prompt 上下文服务

新增 `RAGPromptContextService`：

- 抽取任务检索 `keyword_library`、`channel_sop`。
- 分级任务检索 `compliance_rules`、`failed_cases`、`channel_sop`。
- 话术任务检索 `faq`、`script_template`、`compliance_rules`。
- 输出统一 `rag_context`，包含 `context_status`、`context_text`、`knowledge_item_refs`、`fallback_notes` 和 `hard_rule_boundary`。

### 3.2 抽取和分级审计接入

- `LLMLeadExtractionService` 在 AI 审计 `input_payload` 中保存 `rag_context`。
- `LLMLeadGradingService` 在 AI 审计 `input_payload` 中保存 `rag_context`。
- 未命中或检索异常时记录 `empty_context`，不阻塞基础抽取或分级。

### 3.3 话术审计接入

- `OutreachDraftService.get_existing_draft` 支持传入 `rag_context`。
- `OutreachDraftAudit` 响应结构支持返回 `rag_context`。
- 未传入 RAG 上下文时默认记录 `empty_context`。

## 4. 验收结果

| 验收项 | 结论 | 证据 |
|---|---|---|
| 抽取任务检索关键词库、渠道 SOP | 通过 | `RAGPromptContextService.COLLECTIONS_BY_TASK` |
| 分级任务检索分级/合规规则、失败案例、渠道 SOP | 通过 | `LEAD_GRADING` collection 映射 |
| 话术任务检索 FAQ、触达模板、合规规则 | 通过 | `OUTREACH_DRAFT` collection 映射 |
| 每次 RAG 调用保存知识条目引用 | 通过 | 审计输入 `rag_context.knowledge_item_refs` |
| 未命中知识库时记录 `empty_context` | 通过 | `test_empty_rag_context_is_auditable_and_does_not_block_prompt` |
| 未命中不阻塞基础抽取/分级 | 通过 | `safe_build_context` 返回空上下文 |
| 合规硬规则仍由规则服务执行 | 通过 | C 级合规复核测试覆盖 |
| 禁止用未审核话术生成外发内容 | 通过 | 仅 `active + approved` 进入 RAG，测试排除 pending FAQ |

## 5. TDD 记录

### 5.1 首次 RED

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_rag_in_llm_prompts.py -q
```

结果：

```text
ModuleNotFoundError: No module named 'app.services.rag_prompt_context'
```

### 5.2 话术侧 RED

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_rag_in_llm_prompts.py -q
```

结果：

```text
TypeError: OutreachDraftService.get_existing_draft() got an unexpected keyword argument 'rag_context'
```

### 5.3 实现后测试

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_rag_in_llm_prompts.py -q
```

结果：

```text
4 passed, 1 warning
```

## 6. 回归验证

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/rag_prompt_context.py apps/api/app/services/llm_lead_extraction.py apps/api/app/services/llm_lead_grading.py apps/api/app/services/outreach_draft.py apps/api/app/schemas/outreach_draft.py
```

结果：通过。

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_rag_in_llm_prompts.py apps/api/tests/test_knowledge_search_api.py apps/api/tests/test_llm_lead_extraction.py apps/api/tests/test_llm_lead_grading.py apps/api/tests/test_outreach_draft_api.py -q
```

结果：

```text
23 passed, 2 warnings
```

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m alembic heads
```

结果：

```text
20260529_0018 (head)
```

## 7. 两轮独立评审

### 7.1 第一轮：实现完整性和代码洁净度评审

结论：通过，发现一个非阻塞实现残留。

发现项：

- `rag_prompt_context.py` 中存在未使用的 enum 辅助函数和 import。

修正结果：

- 已删除未使用函数和 import。
- 修正后重新执行语法编译和相关回归，结果仍为 `23 passed`。

### 7.2 第二轮：验收口径和风控边界评审

结论：通过，无新增实质阻塞问题。

发现项：

- 审计链路需要明确包含 `knowledge_item_refs`。
- 未命中 RAG 时必须可追踪为 `empty_context`。
- 未审核或废弃知识不得进入 prompt 上下文。
- C 级合规复核、High/Forbidden 阻断、勿扰阻断等硬规则不能交给 RAG 或 LLM 自行决定。

修正结果：

- `rag_context` 固定包含 `knowledge_item_refs` 和 `hard_rule_boundary`。
- `safe_build_context` 将检索异常记录为 `empty_context` + `fallback_notes`。
- RAG 复用 `KnowledgeSearchService` 的 `active + approved` 准入规则。
- 分级硬规则仍保留在 `LLMLeadGradingService.apply_hard_rules`，测试验证 C 级即使 LLM 省略也会强制合规复核。

## 8. 残留风险

- 本次 Story 未新增数据库表或 migration；RAG 引用通过现有 `ai_audit_logs.input_payload` JSON 保存。
- 当前 Codex 沙箱仍无法连接真实 PostgreSQL，真实库端到端审计落库需在可出网环境复验。
- 话术 API 目前是已有静态草稿服务，本 Story 只让其审计结构可携带 RAG 引用；后续若实现真实 LLM 话术生成，应在生成服务中直接调用 `RAGPromptContextService`。

## 9. 下一步建议

继续执行 `docs/stories/phase-1-small-run` 中下一个未完成 Story。
