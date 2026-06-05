# Story P5-E1-S5：新增知识质量指标与使用记录模型

状态：已完成
Sprint：Sprint 1
优先级：P1
Epic：P5-E1（数据底座）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望新增或扩展知识使用记录，支持召回次数、采纳率、编辑幅度、退信率、客户回复率和建议下线，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 新增或扩展知识使用记录，支持召回次数、采纳率、编辑幅度、退信率、客户回复率和建议下线。

**建议文件：**

- apps/api/app/models/knowledge.py
- apps/api/app/services/*knowledge*
- apps/api/alembic/versions/*

**验收标准：**

- 可记录每次邮件回复召回的知识条目、版本、相似度和过滤条件。
- 支持按知识条目聚合质量指标。
- 不影响现有 pgvector 查询。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E1-S5：新增知识质量指标与使用记录模型。
目标：新增或扩展知识使用记录，支持召回次数、采纳率、编辑幅度、退信率、客户回复率和建议下线。
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

执行日期：2026-06-05
执行分支：`codex/phase-5-small-run`
执行目录：`.worktrees/phase-5-small-run`
执行方式：按 `docs/superpowers/plans/2026-06-05-海外车辆采购AI获客系统-第五阶段小范围运行Codex推进计划.md` 执行当前 Story。

### TDD 记录

红灯：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_knowledge_usage_quality_model.py -q
```

结果：失败，失败原因为当前 Story 缺失能力：

```text
ImportError: cannot import name 'KnowledgeUsageOutcome' from 'app.models.enums'
```

绿灯：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_knowledge_usage_quality_model.py -q
```

结果：`4 passed in 0.40s`。

相关回归：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_knowledge_usage_quality_model.py tests/test_phase5_email_send_attempt_model.py tests/test_phase5_email_reply_draft_model.py tests/test_phase5_email_thread_message_model.py tests/test_phase5_prompt_template_governance.py tests/test_knowledge_schema.py tests/test_knowledge_search_api.py tests/test_rag_in_llm_prompts.py -q
```

结果：`31 passed, 1 warning in 0.33s`。

说明：warning 为既有 `datetime.utcnow()` deprecation warning，位于 `app/services/llm_lead_grading.py`，与本 Story 无关。

### 实现摘要

- 新增 `KnowledgeUsageOutcome` 枚举，支持：
  - `retrieved`
  - `adopted`
  - `edited`
  - `rejected`
  - `customer_replied`
  - `bounced`
  - `suggest_deprecate`
- 新增 `KnowledgeUsageRecord`，落表 `knowledge_usage_records`，记录每次邮件回复召回的知识条目、版本、相似度、排序、过滤条件和后续使用结果。
- 新增 `KnowledgeQualityMetric`，落表 `knowledge_quality_metrics`，支持按知识条目和版本聚合：
  - 召回次数
  - 采纳次数和采纳率
  - 平均编辑幅度
  - 退信次数和退信率
  - 客户回复次数和回复率
  - 建议下线和原因
- 更新 ORM 关系：
  - `KnowledgeItem.usage_records`
  - `KnowledgeItem.quality_metrics`
  - `EmailReplyDraft.knowledge_usage_records`
- 新增 migration：`apps/api/alembic/versions/20260605_0033_create_knowledge_usage_quality.py`。
- 为兼容既有知识库契约测试，恢复 `/knowledge/items/{item_id}/embedding` 路由声明，同时保留 `/knowledge/items/{item_id:uuid}/embedding`。
- 未实现知识质量聚合服务、后台质量页面 API 或 RAG 检索 API 改造；这些属于后续 Story。

### 真实 PostgreSQL migration 验证

当前真实数据库：

```text
postgresql+asyncpg://postgres:***@8.129.17.71:5432/xagent
```

升级：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m alembic current
/opt/miniconda3/envs/booking-room/bin/python -m alembic upgrade head
/opt/miniconda3/envs/booking-room/bin/python -m alembic current
```

结果：

```text
20260605_0032
Running upgrade 20260605_0032 -> 20260605_0033, Create knowledge usage and quality metrics.
20260605_0033 (head)
```

回滚与再升级：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m alembic downgrade 20260605_0032
/opt/miniconda3/envs/booking-room/bin/python -m alembic current
/opt/miniconda3/envs/booking-room/bin/python -m alembic upgrade head
/opt/miniconda3/envs/booking-room/bin/python -m alembic current
```

结果：

```text
Running downgrade 20260605_0033 -> 20260605_0032, Create knowledge usage and quality metrics.
20260605_0032
Running upgrade 20260605_0032 -> 20260605_0033, Create knowledge usage and quality metrics.
20260605_0033 (head)
```

数据库 introspection 结果：

```text
enum_values= ['retrieved', 'adopted', 'edited', 'rejected', 'customer_replied', 'bounced', 'suggest_deprecate']
knowledge_usage_records_columns= 17 ['id', 'knowledge_item_id', 'knowledge_version', 'email_reply_draft_id', 'retrieval_query', 'similarity_score', 'rank', 'filters_json', 'outcome', 'adopted', 'edit_distance_ratio', 'caused_bounce', 'customer_replied', 'suggest_deprecate', 'suggest_deprecate_reason', 'created_at', 'updated_at']
knowledge_usage_records_foreign_keys= [('knowledge_usage_records_email_reply_draft_id_fkey', 'email_reply_drafts'), ('knowledge_usage_records_knowledge_item_id_fkey', 'knowledge_items')]
knowledge_usage_records_indexes= ['ix_knowledge_usage_records_adopted', 'ix_knowledge_usage_records_caused_bounce', 'ix_knowledge_usage_records_customer_replied', 'ix_knowledge_usage_records_email_reply_draft_id', 'ix_knowledge_usage_records_knowledge_item_id', 'ix_knowledge_usage_records_knowledge_version', 'ix_knowledge_usage_records_outcome', 'ix_knowledge_usage_records_suggest_deprecate', 'knowledge_usage_records_pkey']
knowledge_quality_metrics_columns= 16 ['id', 'knowledge_item_id', 'knowledge_version', 'period_start', 'period_end', 'retrieval_count', 'adoption_count', 'adoption_rate', 'average_edit_distance_ratio', 'bounce_count', 'bounce_rate', 'customer_reply_count', 'customer_reply_rate', 'suggest_deprecate', 'suggest_deprecate_reason', 'calculated_at']
knowledge_quality_metrics_foreign_keys= [('knowledge_quality_metrics_knowledge_item_id_fkey', 'knowledge_items')]
knowledge_quality_metrics_indexes= ['ix_knowledge_quality_metrics_knowledge_item_id', 'ix_knowledge_quality_metrics_knowledge_version', 'ix_knowledge_quality_metrics_period_end', 'ix_knowledge_quality_metrics_period_start', 'ix_knowledge_quality_metrics_suggest_deprecate', 'knowledge_quality_metrics_pkey']
```

## 两轮独立评审记录

### 第一轮评审：需求覆盖、数据模型、migration 与回归范围

结论：

- 通过。当前实现只覆盖 P5-E1-S5，未实现知识质量聚合服务、后台质量 API 或 RAG 检索流程改造。
- 通过。可记录每次邮件回复召回的知识条目、版本、相似度、过滤条件和使用结果。
- 通过。支持按知识条目聚合召回次数、采纳率、编辑幅度、退信率、客户回复率和建议下线。
- 通过。未修改 `knowledge_embeddings.embedding` 的 pgvector 字段和现有 pgvector 查询逻辑。
- 通过。migration 已在真实 PostgreSQL 上完成升级、回滚和再升级验证。

发现项：

- 新增测试文件位于 `apps/api/tests/`，仓库 `.gitignore` 会忽略 `tests/`，提交时需要使用 `git add -f` 纳入。
- 扩展回归中发现既有知识库测试要求 `/knowledge/items/{item_id}/embedding` 路由声明存在，但当前代码只有 typed UUID 路由。

修正结果：

- 保留新增测试文件，提交时强制纳入版本控制。
- 为兼容现有 API 契约，给同一个 `create_embedding` 处理函数增加 `/items/{item_id}/embedding` 路由声明，同时保留 `/items/{item_id:uuid}/embedding`。

### 第二轮评审：架构边界、风控和可执行性

结论：

- 通过。`apps/api` 仍是业务数据权威，本 Story 未让 `apps/agents` 直接写业务 core 表。
- 通过。本 Story 未新增任何自动触达、自动发送、邮箱发送动作或社交平台动作。
- 通过。质量指标只记录召回和后续效果，不改变知识条目的审核、发布或归档规则。
- 通过。新增表通过外键关联 `knowledge_items` 和 `email_reply_drafts`，后续可以支撑 EMAIL_REPLY Agent 的 RAG 证据审计。
- 通过。未发现与 P5-E1-S1/S2/S3/S4 或现有知识库模型的回归冲突，相关测试 `31 passed`。

发现项：

- 未发现新增实质阻塞问题。

修正结果：

- 无需修正。

## 2026-06-05 复核收口记录

本次复核未新增业务代码。当前工作树中 `KnowledgeUsageRecord`、`KnowledgeQualityMetric`、`20260605_0033_create_knowledge_usage_quality.py` migration、phase5 migration contract 和 `tests/test_phase5_knowledge_usage_quality_model.py` 已存在，并已由历史提交 `3bf42711 feat: add knowledge usage quality models` 纳入当前分支。

复核命令：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_knowledge_usage_quality_model.py tests/test_phase5_knowledge_quality_usage_api.py tests/test_phase5_migration_contracts.py tests/test_knowledge_schema.py tests/test_knowledge_search_api.py tests/test_rag_in_llm_prompts.py -q
```

复核结果：

```text
24 passed, 13 warnings in 7.29s
```

警告说明：

- 13 个 warning 均为既有 `datetime.utcnow()` deprecation warning，分布在 `apps/api/app/services/knowledge.py`、SQLAlchemy 默认时间回调和 `apps/api/app/services/llm_lead_grading.py`；不影响本 Story 的知识使用/质量模型验收，本 Story 不扩范围修复。

两轮复核结论：

- 第一轮：知识使用记录已覆盖知识条目、版本、相似度、过滤条件、采纳/编辑/退信/客户回复/建议下线等结果，质量指标已支持按知识条目聚合召回次数、采纳率、编辑幅度、退信率、客户回复率和建议下线；未发现需要新增实现的缺口。
- 第二轮：本 Story 未修改 pgvector embedding 字段和现有检索逻辑，未新增自动发送或 Agent 直写业务表能力；架构边界保持 `apps/api` 业务数据权威，未发现新的实质阻塞问题。
