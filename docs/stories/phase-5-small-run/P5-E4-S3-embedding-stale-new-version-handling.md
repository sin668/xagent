# Story P5-E4-S3：embedding stale 与新版本处理

状态：已完成
Sprint：Sprint 4  
优先级：P1  
Epic：P5-E4（pgvector embedding 异步）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望处理知识内容变更后的向量过期，优先通过新版本和 metadata 标记实现，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 处理知识内容变更后的向量过期，优先通过新版本和 metadata 标记实现。

**建议文件：**

- apps/api/app/services/*knowledge*
- apps/api/app/services/*embedding*
- apps/api/tests/*stale*

**验收标准：**

- 编辑已发布知识不会复用旧向量作为当前版本向量。
- 旧版本历史可查但不作为默认召回。
- metadata_json.embedding_stale 或等价标记可审计。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E4-S3：embedding stale 与新版本处理。
目标：处理知识内容变更后的向量过期，优先通过新版本和 metadata 标记实现。
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

- 新增 `apps/api/tests/test_phase5_embedding_stale_new_version.py`。
- 覆盖知识内容变更后的向量过期处理：
  - 已发布知识带有 `ready` embedding。
  - 编辑已发布知识时生成新草稿版本。
  - 新草稿必须带 `parent_item_id`、`embedding_stale=true`、`stale_reason=new_version_pending_embedding`。
  - 旧版本必须带 `embedding_stale=true`、`stale_reason=new_version_created`、`replacement_item_id`。
  - 默认 `EMAIL_REPLY` 召回过滤不得继续返回旧版本 ready embedding。
- 首次运行：`/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_embedding_stale_new_version.py -q`
- 红灯结果：1 个失败。
  - `KeyError: 'embedding_stale'`，说明当前新草稿和旧版本都没有可审计的 stale metadata。

### 实现摘要

- 修改 `KnowledgeService._create_draft_version_from_published`：
  - 新草稿继承业务 metadata 后增加：
    - `embedding_stale=true`
    - `stale_reason=new_version_pending_embedding`
    - `parent_item_id=<旧版本 id>`
  - 旧版本增加：
    - `embedding_stale=true`
    - `stale_reason=new_version_created`
    - `replacement_item_id=<新草稿 id>`
  - 旧版本仍保留 `active/approved` 历史状态，便于历史查看和审计。
- 修改 `KnowledgeSearchService`：
  - `item_matches_filters` 排除 `metadata_json.embedding_stale=true` 的知识，避免 keyword fallback 或普通生产 RAG 召回旧向量。
  - `retrieve_for_email_reply` 排除 `metadata_json.embedding_stale=true` 的知识，避免 EMAIL_REPLY 自动回复候选复用旧向量。
  - 当同语言 ready embedding 记录存在但全部因 stale/业务规则被排除时，返回 `缺少同语言 embedding_ready 知识，不能自动发送。`，保持自动发送准入可解释。

### 系统化调试记录

- 第一轮实现后，`embedding_stale` metadata 已写入，但测试仍失败：
  - `retrieval.json()["rejection_reason"] == None`
- 根因：
  - `retrieve_for_email_reply` 只在原始 ready embedding 查询为空时返回拒绝原因；如果 ready 记录存在但后续被 stale 或业务过滤排除，最终空结果没有 rejection_reason。
- 修正：
  - 在最终 `results` 为空时返回 `MISSING_LANGUAGE_READY_REASON`。
- 复测：
  - `tests/test_phase5_embedding_stale_new_version.py tests/test_phase5_knowledge_retrieval_filter_api.py` 转绿。

### 真实 PostgreSQL / API 验证

- 当前 Story 与检索过滤回归：
  - `/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_embedding_stale_new_version.py tests/test_phase5_knowledge_retrieval_filter_api.py -q`
  - 结果：`3 passed, 42 warnings`。
- 知识库与 embedding 回归：
  - `git diff --check && cd apps/api && /opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_embedding_stale_new_version.py tests/test_phase5_embedding_async_worker.py tests/test_phase5_embedding_task_status_retry_service.py tests/test_phase5_knowledge_retrieval_filter_api.py tests/test_phase5_knowledge_review_publish_archive_api.py tests/test_phase5_knowledge_crud_api.py tests/test_phase5_knowledge_business_fields.py tests/test_knowledge_schema.py tests/test_knowledge_search_api.py tests/test_phase_one_knowledge_import.py tests/test_phase5_knowledge_usage_quality_model.py -q`
  - 结果：`38 passed, 154 warnings`。
- 已知 warning：
  - 知识库服务仍使用 `datetime.utcnow()`，触发 Python 3.12 deprecation warning，属于既有技术债，非本 Story 行为阻塞。

## 两轮独立多维度评审

### 第一轮评审：需求覆盖、版本边界和召回安全

- 结论：P5-E4-S3 的验收标准已覆盖；编辑已发布知识不会让旧 ready embedding 继续作为当前默认召回候选。
- 发现项 1：新草稿如果没有 stale 标记，后续发布/embedding worker 难以审计“需要重新生成 embedding”的状态。
- 修正结果 1：新草稿增加 `embedding_stale=true` 和 `stale_reason=new_version_pending_embedding`。
- 发现项 2：旧版本如果仅保留 active/approved 状态，默认检索可能继续复用旧向量。
- 修正结果 2：旧版本增加 `embedding_stale=true`、`stale_reason=new_version_created`、`replacement_item_id`，默认召回排除 stale 知识。
- 发现项 3：旧版本历史仍需可查，不能直接删除或下线为不可见状态。
- 修正结果 3：不删除旧 item 和 embedding，不改变旧版本历史可查性，仅通过 metadata 控制默认召回。

### 第二轮评审：回归风险、可解释性和范围控制

- 结论：第二轮未发现新增实质阻塞问题；实现范围保持在 P5-E4-S3，没有执行 RAG 召回测试 API、embedding metrics 或后续 Story。
- 发现项 1：默认召回和 EMAIL_REPLY 检索过滤都需要排除 stale，否则一个通道修好另一个仍有风险。
- 修正结果 1：同时更新 `item_matches_filters` 与 `retrieve_for_email_reply`。
- 发现项 2：有 ready 记录但被 stale 过滤后，API 若不返回拒绝原因，会影响自动发送风险解释。
- 修正结果 2：最终结果为空时返回 `缺少同语言 embedding_ready 知识，不能自动发送。`。
- 发现项 3：新增测试文件受 `.gitignore` 影响，普通 `git status` 不显示。
- 修正结果 3：提交前将使用 `git add -f apps/api/tests/test_phase5_embedding_stale_new_version.py`。
- 发现项 4：metadata 标记方式符合 Story“优先通过新版本和 metadata 标记实现”，无需新增表结构或 migration。
- 修正结果 4：本 Story 未引入 migration，保持实现最小且可审计。
