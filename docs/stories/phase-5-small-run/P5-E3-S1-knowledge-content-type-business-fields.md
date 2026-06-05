# Story P5-E3-S1：知识库内容类型与业务属性扩展

状态：已完成
Sprint：Sprint 3  
优先级：P0  
Epic：P5-E3（Q&A/邮件回复知识库）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望扩展知识条目 metadata，支持 content_type、business_scene、language、risk_level、auto_reply_allowed、market、tone，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 扩展知识条目 metadata，支持 content_type、business_scene、language、risk_level、auto_reply_allowed、market、tone。

**建议文件：**

- apps/api/app/models/knowledge.py
- apps/api/app/schemas/*knowledge*
- apps/api/tests/*knowledge*

**验收标准：**

- 支持 qa_entry、email_reply_template、compliance_phrase、vehicle_product_note、process_sop。
- 检索过滤可读取新增属性。
- 未发布或 blocked 内容不得进入自动回复候选。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E3-S1：知识库内容类型与业务属性扩展。
目标：扩展知识条目 metadata，支持 content_type、business_scene、language、risk_level、auto_reply_allowed、market、tone。
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

- 新增 `apps/api/tests/test_phase5_knowledge_business_fields.py`。
- 覆盖知识条目新增业务字段、content_type 枚举校验、检索过滤读取新增属性、blocked/未允许自动回复内容不得进入自动回复候选。
- 首次运行：`/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_knowledge_business_fields.py -q`
- 红灯结果：4 个失败。
  - 创建知识条目后响应未展开 `content_type/business_scene/risk_level/auto_reply_allowed/market/tone`。
  - 未知 `content_type=random_note` 未被拒绝。
  - `KnowledgeService.create_item` 不接受新增业务字段。
  - `KnowledgeService.SUPPORTED_CONTENT_TYPES` 和 `KnowledgeSearchService.BLOCKED_RISK_LEVELS` 未定义。

### 实现摘要

- 在 `KnowledgeItemCreate`、`KnowledgeItemResponse` 和 `KnowledgeSearchRequest` 中显式支持：
  - `content_type`
  - `business_scene`
  - `language`
  - `risk_level`
  - `auto_reply_allowed`
  - `market`
  - `tone`
- `content_type` 支持并校验：
  - `qa_entry`
  - `email_reply_template`
  - `compliance_phrase`
  - `vehicle_product_note`
  - `process_sop`
- 使用现有 `knowledge_items.metadata_json` 承载第五阶段业务属性，不新增表结构迁移。
- `KnowledgeService.create_item` 支持新增业务字段，并统一规范化写入 `metadata_json`。
- `KnowledgeSearchService` 支持按新增业务属性过滤，并在 `auto_reply_only=true` 时排除：
  - 未 active/approved 的知识条目。
  - `risk_level` 为 `blocked`、`Forbidden`、`High` 的条目。
  - `auto_reply_allowed` 不为 `true` 的条目。
- 修复 phase-one 知识导入在 worktree 中找不到 `docs/poc/*.md` 的回归问题：优先读取真实交付文档，缺失时回退到仓库内对应 Story 文档。

### 真实 PostgreSQL / API 验证

- 当前 Story 单测：
  - `/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_knowledge_business_fields.py -q`
  - 结果：`4 passed`。
- 知识库相关回归：
  - `/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_knowledge_business_fields.py tests/test_knowledge_schema.py tests/test_knowledge_search_api.py tests/test_phase_one_knowledge_import.py tests/test_phase5_knowledge_usage_quality_model.py -q`
  - 结果：`24 passed, 14 warnings`。
  - 已知 warning：知识库模型仍有 `datetime.utcnow()` 的 Python 3.12 deprecation warning，非本 Story 行为阻塞。
- 测试数据残留检查：
  - 真实 PostgreSQL 中 `phase5_knowledge_business_%` collection 数量：`0`。
  - 真实 PostgreSQL 中 `phase5_knowledge_business_%` item 数量：`0`。

## 两轮独立多维度评审

### 第一轮评审：数据字段、检索过滤、自动回复风险

- 结论：本 Story 的新增知识业务属性已可通过 API 创建、响应展示和检索过滤读取；自动回复候选过滤符合第五阶段风险边界。
- 发现项 1：新增字段如果只放在请求体里但响应不展开，后台页面无法直接展示和筛选。
- 修正结果 1：`serialize_item` 从 `metadata_json` 展开新增字段，并在 `KnowledgeItemResponse` 中显式返回。
- 发现项 2：未知 `content_type` 会被旧 schema 忽略，导致知识类型不可控。
- 修正结果 2：在 Pydantic schema 和 `KnowledgeService.build_business_metadata` 中双层校验支持的 content_type。
- 发现项 3：自动回复候选不能只看 active/approved，还必须排除 blocked、高风险和 manual-only 内容。
- 修正结果 3：`KnowledgeSearchService.item_matches_filters` 加入 `BLOCKED_RISK_LEVELS` 和 `auto_reply_only` 过滤。

### 第二轮评审：范围控制、兼容性、回归风险

- 结论：第二轮未发现新增实质阻塞问题；当前实现只覆盖 P5-E3-S1，没有进入知识库 CRUD 审核发布、embedding worker 或 EMAIL_REPLY Agent。
- 发现项 1：为每个新增字段单独加数据库列会扩大 migration 风险，而 Story 明确是扩展 metadata。
- 修正结果 1：沿用 `metadata_json` 承载业务属性，避免新增表结构迁移，同时通过 schema/service 保证字段结构化。
- 发现项 2：phase-one 知识导入回归依赖主工作区未纳入 worktree 的 `docs/poc/*.md`，导致测试不稳定。
- 修正结果 2：导入服务新增交付文档 fallback：优先 `docs/poc`，缺失时读取对应的仓库内 Story 文档。
- 发现项 3：新增测试使用真实 PostgreSQL，如果 fixture 只清 item 不清 collection，可能留下级联数据。
- 修正结果 3：fixture 删除以 `phase5_knowledge_business_%` 命名的 collection，通过级联清理 item，并用真实库查询确认残留为 0。
