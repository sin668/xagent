# Story P5-E3-S2：Q&A 与邮件回复模板 CRUD API

状态：已完成
Sprint：Sprint 3  
优先级：P0  
Epic：P5-E3（Q&A/邮件回复知识库）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望提供 Q&A、邮件回复模板、合规话术、车型说明和流程 SOP 的创建、编辑、列表、详情 API，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 提供 Q&A、邮件回复模板、合规话术、车型说明和流程 SOP 的创建、编辑、列表、详情 API。

**建议文件：**

- apps/api/app/routers/*knowledge*
- apps/api/app/schemas/*knowledge*
- apps/api/tests/*knowledge_crud*

**验收标准：**

- 后台可按内容类型、语言、场景、风险等级、状态过滤。
- 草稿内容不得进入召回。
- 编辑已发布内容必须生成新版本或回到草稿流程。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E3-S2：Q&A 与邮件回复模板 CRUD API。
目标：提供 Q&A、邮件回复模板、合规话术、车型说明和流程 SOP 的创建、编辑、列表、详情 API。
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

- 新增 `apps/api/tests/test_phase5_knowledge_crud_api.py`。
- 覆盖后台知识库列表过滤、详情、草稿更新、已发布内容编辑生成新草稿版本、草稿不得进入自动回复召回。
- 首次运行：`/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_knowledge_crud_api.py -q`
- 红灯结果：3 个失败、1 个通过。
  - 列表接口未接入 `content_type/language/business_scene/risk_level/status/review_status/auto_reply_allowed/market/tone` 过滤。
  - `GET /knowledge/items/{item_id}` 返回 404，详情 API 未实现。
  - `PATCH /knowledge/items/{item_id}` 返回 404，编辑 API 未实现。
  - 草稿不进入自动回复召回已由 P5-E3-S1 的 production RAG 规则覆盖。

### 实现摘要

- 新增 `KnowledgeItemUpdate` schema，支持后台编辑标题、正文、语言、渠道、状态、审核状态、版本、metadata 和第五阶段业务字段。
- `GET /knowledge/items` 增加后台过滤参数：
  - `content_type`
  - `language`
  - `business_scene`
  - `risk_level`
  - `status`
  - `review_status`
  - `auto_reply_allowed`
  - `market`
  - `tone`
- 新增 `GET /knowledge/items/{item_id}` 详情 API。
- 新增 `PATCH /knowledge/items/{item_id}` 编辑 API。
- `KnowledgeService.update_item` 支持：
  - draft/pending 等未发布内容原地编辑。
  - active/approved 已发布内容编辑时生成新的 draft 版本，不覆盖原发布版本。
- 新 draft 版本在 `metadata_json` 中记录：
  - `parent_item_id`
  - `change_reason`

### 真实 PostgreSQL / API 验证

- 当前 Story 单测：
  - `/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_knowledge_crud_api.py -q`
  - 结果：`4 passed`。
- 知识库相关回归：
  - `/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_knowledge_crud_api.py tests/test_phase5_knowledge_business_fields.py tests/test_knowledge_schema.py tests/test_knowledge_search_api.py tests/test_phase_one_knowledge_import.py tests/test_phase5_knowledge_usage_quality_model.py -q`
  - 结果：`28 passed, 37 warnings`。
  - 已知 warning：知识库模型仍有 `datetime.utcnow()` 的 Python 3.12 deprecation warning，非本 Story 行为阻塞。
- 测试数据残留检查：
  - 真实 PostgreSQL 中 `phase5_knowledge_crud_%` collection 数量：`0`。
  - 真实 PostgreSQL 中 `phase5_knowledge_crud_%` item 数量：`0`。

## 两轮独立多维度评审

### 第一轮评审：CRUD 行为、过滤能力、版本边界

- 结论：本 Story 的创建、列表、详情、编辑和已发布内容版本化编辑能力已具备，满足后台知识库管理的基础 API 需求。
- 发现项 1：原 `GET /knowledge/items` 只支持 `production_rag_only` 和 `limit`，无法按后台需要的内容类型、语言、场景、风险和状态过滤。
- 修正结果 1：扩展列表 query 参数，并在 `KnowledgeService.list_items` 中统一应用数据库状态过滤和 metadata 业务字段过滤。
- 发现项 2：原系统没有知识条目详情 API，后台无法进入单条 Q&A/模板/SOP 编辑页。
- 修正结果 2：新增 `GET /knowledge/items/{item_id}`，不存在返回 404。
- 发现项 3：已发布 active/approved 内容如果被直接编辑，会破坏历史和审核链路。
- 修正结果 3：已发布内容 PATCH 时生成新的 draft 版本，原 active/approved 内容保持不变。

### 第二轮评审：风险边界、回归兼容、数据清理

- 结论：第二轮未发现新增实质阻塞问题；当前实现只覆盖 P5-E3-S2，没有执行审核发布、embedding worker 或 EMAIL_REPLY Agent。
- 发现项 1：草稿内容不得进入召回是本 Story 关键边界，不能因为新增 CRUD 而被绕过。
- 修正结果 1：保持 `KnowledgeSearchService` 的 production RAG 规则，只返回 active/approved 且通过风险过滤的条目；新增测试确认 draft 不进入自动回复召回。
- 发现项 2：字段过滤如果只在 API 层做，service 复用时可能返回未过滤数据。
- 修正结果 2：过滤逻辑放在 `KnowledgeService.list_items`，API 只负责参数传递。
- 发现项 3：真实 PostgreSQL 测试中，已发布编辑会额外生成 draft，如果 fixture 只删除 collection 外层不级联可能残留。
- 修正结果 3：测试 fixture 删除 `phase5_knowledge_crud_%` collection，并依赖模型 cascade 清理 item；真实库残留查询为 0。
