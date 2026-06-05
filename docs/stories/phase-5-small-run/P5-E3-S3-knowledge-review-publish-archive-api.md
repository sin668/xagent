# Story P5-E3-S3：知识库审核发布与下线 API

状态：已完成
Sprint：Sprint 3  
优先级：P0  
Epic：P5-E3（Q&A/邮件回复知识库）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望实现知识条目 draft -> in_review -> published -> pending_embedding -> active_for_retrieval 以及 archived/blocked，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 实现知识条目 draft -> in_review -> published -> pending_embedding -> active_for_retrieval 以及 archived/blocked。

**建议文件：**

- apps/api/app/services/*knowledge*
- apps/api/app/routers/*knowledge*
- apps/api/tests/*knowledge_review*

**验收标准：**

- 发布后自动进入 pending_embedding。
- blocked/archived 内容不参与召回。
- 审核、发布、下线均写审计。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E3-S3：知识库审核发布与下线 API。
目标：实现知识条目 draft -> in_review -> published -> pending_embedding -> active_for_retrieval 以及 archived/blocked。
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

- 新增 `apps/api/tests/test_phase5_knowledge_review_publish_archive_api.py`。
- 覆盖知识条目提交审核、发布后进入 pending_embedding、激活召回、下线/阻断排除召回、审核审计记录和未授权发布拒绝。
- 首次运行：`/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_knowledge_review_publish_archive_api.py -q`
- 红灯结果：3 个失败。
  - `/knowledge/items/{item_id}/submit-review` 返回 404。
  - `/knowledge/items/{item_id}/publish`、`activate-retrieval`、`archive`、`block` 未实现。
  - `/knowledge/items/{item_id}/review-logs` 未实现。

### 实现摘要

- 新增 `KnowledgeReviewActionRequest`、`KnowledgeReviewLogResponse`、`KnowledgeReviewLogListResponse`。
- 在 `KnowledgeService` 中新增知识审核状态机：
  - `submit_review`：`workflow_state=in_review`。
  - `publish_item`：`workflow_state=pending_embedding`，保持不进入召回。
  - `activate_retrieval`：`workflow_state=active_for_retrieval`，设置 `status=active`、`review_status=approved`。
  - `archive_item`：`workflow_state=archived`，设置 `status=deprecated`，并禁止自动回复。
  - `block_item`：`workflow_state=blocked`，设置 `status=disabled`、`review_status=rejected`、`risk_level=blocked`、`auto_reply_allowed=false`。
- 新增审核动作 API：
  - `POST /knowledge/items/{item_id}/submit-review`
  - `POST /knowledge/items/{item_id}/publish`
  - `POST /knowledge/items/{item_id}/activate-retrieval`
  - `POST /knowledge/items/{item_id}/archive`
  - `POST /knowledge/items/{item_id}/block`
  - `GET /knowledge/items/{item_id}/review-logs`
- 审核、发布、激活、下线、阻断均写入 `review_logs`，`agent_name=knowledge_governance`。
- 权限边界：
  - operator/admin/knowledge_admin/tech_admin 可提交审核。
  - knowledge_admin/admin/tech_admin 可发布。
  - tech_admin/knowledge_admin/admin 可激活召回。
  - knowledge_admin/admin/tech_admin 可下线。
  - compliance/knowledge_admin/admin/tech_admin 可阻断。

### 真实 PostgreSQL / API 验证

- 当前 Story 单测：
  - `/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_knowledge_review_publish_archive_api.py -q`
  - 结果：`3 passed`。
- 知识库相关回归：
  - `/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_knowledge_review_publish_archive_api.py tests/test_phase5_knowledge_crud_api.py tests/test_phase5_knowledge_business_fields.py tests/test_knowledge_schema.py tests/test_knowledge_search_api.py tests/test_phase_one_knowledge_import.py tests/test_phase5_knowledge_usage_quality_model.py -q`
  - 结果：`31 passed, 81 warnings`。
  - 已知 warning：知识库模型和 `review_logs.created_at` 仍使用 `datetime.utcnow()`，触发 Python 3.12 deprecation warning，非本 Story 行为阻塞。
- 测试数据残留检查：
  - 真实 PostgreSQL 中 `phase5_knowledge_review_%` collection 数量：`0`。
  - 真实 PostgreSQL 中 `phase5_knowledge_review_%` item 数量：`0`。
  - 真实 PostgreSQL 中当前 Story 相关 `knowledge_governance` 审计残留数量：`0`。

## 两轮独立多维度评审

### 第一轮评审：状态流、召回边界、审计

- 结论：P5-E3-S3 的审核发布状态流已建立，发布后不会直接进入召回，只有显式激活后才成为可召回知识。
- 发现项 1：如果发布直接设置 active/approved，会绕过 pending_embedding 阶段。
- 修正结果 1：`publish_item` 仅设置 `workflow_state=pending_embedding`，保持 `status=draft`、`review_status=approved`，因此不会被生产召回选中。
- 发现项 2：blocked/archived 内容如果只写 metadata，不改 status/review_status，仍可能被旧搜索逻辑召回。
- 修正结果 2：archive 设置 `status=deprecated`，block 设置 `status=disabled`、`review_status=rejected`，并关闭自动回复。
- 发现项 3：审核动作需要可追溯，不能只改知识条目字段。
- 修正结果 3：所有审核动作写入 `review_logs`，并提供 `/review-logs` 查询 API。

### 第二轮评审：权限、兼容性、范围控制

- 结论：第二轮未发现新增实质阻塞问题；当前实现只覆盖 P5-E3-S3，没有执行 embedding worker、召回测试 API 或 EMAIL_REPLY Agent。
- 发现项 1：发布权限不能开放给 sales_manager，否则后台可能绕过知识审核职责边界。
- 修正结果 1：`publish_item` 仅允许 knowledge_admin/admin/tech_admin，测试覆盖 sales_manager 发布返回 403。
- 发现项 2：pending_embedding 与 active_for_retrieval 使用 metadata 表达，如果搜索层不看 status，可能误入召回。
- 修正结果 2：保持搜索生产候选仍以 `status=active`、`review_status=approved` 为硬门槛，pending_embedding 不满足门槛。
- 发现项 3：真实 PostgreSQL 测试会产生多条 review_logs，清理不完整会污染后续用例。
- 修正结果 3：fixture 同时清理测试 collection/item 和对应 `knowledge_governance` 审计；真实库残留检查为 0。
