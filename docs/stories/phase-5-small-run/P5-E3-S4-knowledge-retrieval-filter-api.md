# Story P5-E3-S4：知识库召回过滤 API

状态：已完成
Sprint：Sprint 3  
优先级：P0  
Epic：P5-E3（Q&A/邮件回复知识库）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望提供 EMAIL_REPLY 可用的知识检索过滤 API，强制按语言、场景、内容类型、状态和风险过滤，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

## 上下文来源

- `docs/brainstorm/brainstorming-session-2026-06-05-第五阶段小范围运行-Prompt与邮件自动回复知识库.md`
- `docs/product/2026-06-05-海外车辆采购AI获客系统-第五阶段小范围运行方案与产品技术设计.md`
- `prototypes/mvp-mobile-agent/design-brief.md`
- `prototypes/mvp-mobile-agent/pages/email-replies.html`
- `prototypes/mvp-mobile-agent/pages/email-reply-detail.html`
- `prototypes/mvp-mobile-agent/pages/admin-prompt-governance.html`
- `prototypes/mvp-mobile-agent/pages/admin-knowledge-base.html`
- `prototypes/mvp-mobile-agent/pages/admin-email-replies.html`
- `prototypes/mvp-mobile-agent/pages/admin-email-quality.html`

## Story 定义

**目标：** 提供 EMAIL_REPLY 可用的知识检索过滤 API，强制按语言、场景、内容类型、状态和风险过滤。

**建议文件：**

- apps/api/app/services/*rag*
- apps/api/app/routers/*knowledge*
- apps/api/tests/*retrieval*

**验收标准：**

- 自动发送场景只召回 active/published + embedding_ready + auto_reply_allowed=true。
- 同语言知识缺失时返回明确原因。
- 召回结果包含 knowledge_item_id、version、similarity_score 和 filter_conditions。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E3-S4：知识库召回过滤 API。
目标：提供 EMAIL_REPLY 可用的知识检索过滤 API，强制按语言、场景、内容类型、状态和风险过滤。
要求：使用 TDD；只实现本 Story；接入真实 PostgreSQL/API；完成后执行两轮独立多维度评审并用中文记录结论、发现项和修正结果。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 代码实现必须使用 `superpowers:test-driven-development`；调试异常必须使用 `superpowers:systematic-debugging`；完成前必须使用 `superpowers:verification-before-completion`。
- 环境按项目约定使用 `conda activate booking-room` 和 `nvm use v22.22.0`。
- 后端、Agent、后台和移动端联调必须使用真实 API、真实 PostgreSQL 和 Redis，不允许只验证 seed 静态页面。
- 每个 Story 完成后必须执行两轮独立多维度评审，并在 Story 或执行记录中写明结论、发现项和修正结果。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- `apps/api` 是唯一业务数据权威，业务 core 表写入、权限、审计、DNC/勿扰、自动发送准入、硬拦截和邮件发送提交必须由 `apps/api` 控制。
- `apps/agents` 只做编排、LLM 调用、节点追踪和结果回传，不直接写 `customers`、`contact_methods`、`lead_sources`、`knowledge_items`、`email_reply_drafts`、`outreach_records` 等业务 core 表。
- 不自动社交私信、不自动加好友、不登录后批量采集、不反爬规避、不抓取非公开数据。
- DNC/勿扰、Watch/Invalid（对外 D/E 级）、语言不确定、知识召回不足、缺少知识证据、价格/付款/合同/发票/税务/法律/交付/出口管制等场景不得自动发送。
- LLM 输出必须结构化；缺失字段输出 `Unknown`、`null` 或空数组，不得编造。
- AI 建议回复和最终发送内容必须分开保存并可审计。

## 执行记录

### TDD 红灯

- 新增 `apps/api/tests/test_phase5_knowledge_retrieval_filter_api.py`。
- 覆盖 EMAIL_REPLY 专用召回过滤：
  - 自动发送候选只召回 `active + approved + embedding ready + auto_reply_allowed=true`。
  - 强制按语言、渠道、内容类型、业务场景和市场过滤。
  - 排除未 ready embedding、manual only、blocked 风险和不同语言知识。
  - 同语言 `embedding_ready` 知识缺失时返回明确原因。
  - 结果包含 `knowledge_item_id`、`version`、`similarity_score` 和 `filter_conditions`。
- 首次运行：`/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_knowledge_retrieval_filter_api.py -q`
- 红灯修正过程：
  - 第一次失败为测试夹具错误：真实 pgvector 列固定 1536 维，测试误写 3 维向量，触发 `expected 1536 dimensions, not 3`。
  - 修正测试夹具为 1536 维向量后重新运行，红灯落在目标缺口：`/knowledge/retrieval-filter` 返回 404。

### 实现摘要

- 新增专用请求/响应 schema：
  - `KnowledgeRetrievalFilterRequest`
  - `KnowledgeRetrievalFilterResultResponse`
  - `KnowledgeRetrievalFilterResponse`
- 在 `KnowledgeSearchService` 中新增 EMAIL_REPLY 专用召回过滤：
  - `retrieve_for_email_reply`
  - `retrieval_filter_conditions`
  - `KnowledgeRetrievalFilterResult`
- 新增 API：
  - `POST /knowledge/retrieval-filter`
- 召回硬门槛：
  - `KnowledgeItem.status=active`
  - `KnowledgeItem.review_status=approved`
  - `KnowledgeEmbedding.embedding_status=ready`
  - `KnowledgeItem.language` 与请求语言一致
  - 自动发送候选要求 `auto_reply_allowed=true`
  - 排除 `risk_level` 为 `blocked`、`Forbidden`、`High` 的知识
  - 按 `channel`、`content_types`、`business_scene`、`market`、`tone` 继续过滤
- 返回结构包含召回过滤条件，供 EMAIL_REPLY Agent 后续审计和自动发送判断链路使用。

### 真实 PostgreSQL / API 验证

- 当前 Story 单测：
  - `/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_knowledge_retrieval_filter_api.py -q`
  - 结果：`2 passed, 34 warnings`。
- 已知 warning：
  - 知识库服务仍使用 `datetime.utcnow()`，触发 Python 3.12 deprecation warning，非本 Story 行为阻塞。

## 两轮独立多维度评审

### 第一轮评审：召回硬门槛、同语言缺失和自动发送边界

- 结论：P5-E3-S4 已提供 EMAIL_REPLY 专用召回过滤 API，自动发送候选不会复用较宽松的通用 `/knowledge/search`。
- 发现项 1：如果继续使用通用 `/knowledge/search`，keyword fallback 可能召回未生成 ready embedding 的知识。
- 修正结果 1：新增 `/knowledge/retrieval-filter`，查询时强制 join `knowledge_embeddings` 且要求 `embedding_status=ready`。
- 发现项 2：如果只按业务字段过滤，不按语言过滤，会让 EMAIL_REPLY 在语言不确定或缺少同语言知识时继续生成回复。
- 修正结果 2：查询层强制 `KnowledgeItem.language == request.language`；同语言 ready 知识完全缺失时返回 `缺少同语言 embedding_ready 知识，不能自动发送。`。
- 发现项 3：自动发送候选不得召回 `auto_reply_allowed=false` 或 blocked/High/Forbidden 风险知识。
- 修正结果 3：`auto_send_candidate=true` 时强制 `auto_reply_allowed=true`，并排除 blocked/High/Forbidden 风险等级。

### 第二轮评审：兼容性、范围控制和可审计性

- 结论：第二轮未发现新增实质阻塞问题；当前实现只覆盖 P5-E3-S4，没有执行 embedding worker、RAG 测试 API、知识质量统计或 EMAIL_REPLY Agent。
- 发现项 1：P5-E3-S4 需要保留原 `/knowledge/search` 兼容性，避免破坏已有第一阶段/第五阶段知识库测试。
- 修正结果 1：新增专用接口而非改造通用接口；通用搜索仍保留原 search mode 和 fallback 行为。
- 发现项 2：召回结果如果只返回 item，不便于 EMAIL_REPLY 后续记录知识命中和过滤上下文。
- 修正结果 2：专用结果返回 `knowledge_item_id`、`version`、`similarity_score` 和 `filter_conditions`。
- 发现项 3：测试使用真实 PostgreSQL + pgvector，若维度不匹配会在 fixture 阶段失败，不能证明接口行为。
- 修正结果 3：测试 embedding 使用 1536 维向量，与真实库列定义一致。
