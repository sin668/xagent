# Story P5-E4-S4：RAG 召回测试 API

状态：已完成
Sprint：Sprint 4  
优先级：P0  
Epic：P5-E4（pgvector embedding 异步）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望提供后台召回测试 API，用于验证语言、场景、内容类型、风险和 auto_reply_allowed 过滤效果，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 提供后台召回测试 API，用于验证语言、场景、内容类型、风险和 auto_reply_allowed 过滤效果。

**建议文件：**

- apps/api/app/routers/*knowledge*
- apps/api/app/services/*rag*
- apps/api/tests/*rag_test*

**验收标准：**

- 可输入 query、language、business_scene、content_type、auto_send_context。
- 返回召回条目、相似度、过滤条件和未命中原因。
- 自动发送测试不会触发真实发送。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E4-S4：RAG 召回测试 API。
目标：提供后台召回测试 API，用于验证语言、场景、内容类型、风险和 auto_reply_allowed 过滤效果。
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

- 新增 `apps/api/tests/test_phase5_rag_retrieval_test_api.py`。
- 覆盖后台 RAG 召回测试 API：
  - 输入 `query`、`language`、`channel`、`content_type`、`business_scene`、`auto_send_context`、`market`、`limit`。
  - 返回召回条目、相似度、过滤条件、未命中原因。
  - 明确 `dry_run=true`、`triggered_send=false`，保证自动发送测试不会触发真实发送。
  - blocked 风险知识即使有 ready embedding 也不会返回。
- 首次运行：`/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_rag_retrieval_test_api.py -q`
- 红灯结果：2 个失败。
  - `/knowledge/rag-test` 返回 404，说明当前没有后台 RAG 召回测试 API。

### 实现摘要

- 新增 schema：
  - `KnowledgeRagRetrievalTestRequest`
  - `KnowledgeRagRetrievalTestResponse`
- 新增 API：
  - `POST /knowledge/rag-test`
- API 行为：
  - 复用 `KnowledgeSearchService.retrieve_for_email_reply` 的生产过滤逻辑，验证语言、渠道、内容类型、业务场景、auto_send_context、market、tone、stale、risk、auto_reply_allowed。
  - 响应中返回 `filter_conditions`，便于后台管理页面展示本次测试实际应用的过滤条件。
  - 响应中固定 `dry_run=true`、`triggered_send=false`，不调用邮件发送、不创建发送记录、不进入 EMAIL_REPLY 发送闭环。
  - 支持单个 `content_type` 输入，也支持后续扩展的 `content_types` 多类型输入。

### 真实 PostgreSQL / API 验证

- 当前 Story 单测：
  - `/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_rag_retrieval_test_api.py -q`
  - 结果：`2 passed, 16 warnings`。
- 知识库、embedding、检索相关回归：
  - `git diff --check && cd apps/api && /opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_rag_retrieval_test_api.py tests/test_phase5_knowledge_retrieval_filter_api.py tests/test_phase5_embedding_stale_new_version.py tests/test_phase5_embedding_async_worker.py tests/test_phase5_embedding_task_status_retry_service.py tests/test_phase5_knowledge_review_publish_archive_api.py tests/test_phase5_knowledge_crud_api.py tests/test_phase5_knowledge_business_fields.py tests/test_knowledge_schema.py tests/test_knowledge_search_api.py -q`
  - 结果：`31 passed, 170 warnings`。
- 已知 warning：
  - 知识库服务仍使用 `datetime.utcnow()`，触发 Python 3.12 deprecation warning，属于既有技术债，非本 Story 行为阻塞。

## 两轮独立多维度评审

### 第一轮评审：需求覆盖、过滤准确性和发送隔离

- 结论：P5-E4-S4 的验收标准已覆盖；后台可通过 `/knowledge/rag-test` 验证 query、language、business_scene、content_type、auto_send_context 的召回效果。
- 发现项 1：后台测试 API 不能复制一套与生产不一致的过滤逻辑，否则测试通过不代表 EMAIL_REPLY 可用。
- 修正结果 1：直接复用 `KnowledgeSearchService.retrieve_for_email_reply`。
- 发现项 2：自动发送测试必须明确不会触发真实发送，避免后台页面误操作。
- 修正结果 2：响应固定返回 `dry_run=true` 和 `triggered_send=false`，实现中不调用任何邮件发送服务。
- 发现项 3：后台需要展示过滤条件，便于定位未命中是语言、场景、类型还是 auto_reply_allowed 问题。
- 修正结果 3：响应增加 `filter_conditions`。

### 第二轮评审：回归风险、可解释性和范围控制

- 结论：第二轮未发现新增实质阻塞问题；实现范围保持在 P5-E4-S4，没有执行 embedding metrics、邮件回复 Agent 或发送流程 Story。
- 发现项 1：`content_type` 单值输入满足当前原型表单，但后续 EMAIL_REPLY 可能需要多个知识类型。
- 修正结果 1：schema 同时支持 `content_type` 和 `content_types`，当前测试覆盖单值输入。
- 发现项 2：未命中时必须返回原因，否则运营无法判断是知识缺失还是过滤过严。
- 修正结果 2：沿用 `retrieve_for_email_reply` 的 `rejection_reason`。
- 发现项 3：新增测试文件受 `.gitignore` 影响，普通 `git status` 不显示。
- 修正结果 3：提交前将使用 `git add -f apps/api/tests/test_phase5_rag_retrieval_test_api.py`。
- 发现项 4：本 Story 不应引入真实邮件发送、usage 记录或质量统计写入。
- 修正结果 4：API 只读知识和 embedding 数据，不写发送相关表。
