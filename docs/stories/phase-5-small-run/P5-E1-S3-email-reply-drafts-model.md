# Story P5-E1-S3：新增 AI 邮件回复草稿模型

状态：未开始  
Sprint：Sprint 1  
优先级：P0  
Epic：P5-E1（数据底座）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望新增 `email_reply_drafts`，分离 AI 建议回复与最终发送内容，保存知识命中和自动发送判断，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 新增 `email_reply_drafts`，分离 AI 建议回复与最终发送内容，保存知识命中和自动发送判断。

**建议文件：**

- apps/api/app/models/*email*
- apps/api/alembic/versions/*
- apps/api/tests/*email_reply*

**验收标准：**

- 保存 prompt_template_id/version、model、AI 建议、最终内容、knowledge_hits_json、auto_send_decision_json。
- 支持 drafted、pending_review、approved、sent、rejected、blocked、failed 状态。
- AI 建议与 final 内容不能互相覆盖。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E1-S3：新增 AI 邮件回复草稿模型。
目标：新增 `email_reply_drafts`，分离 AI 建议回复与最终发送内容，保存知识命中和自动发送判断。
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
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_reply_draft_model.py -q
```

结果：失败，失败原因为当前 Story 缺失能力：

```text
ImportError: cannot import name 'EmailReplyDraftStatus' from 'app.models.enums'
```

绿灯：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_reply_draft_model.py -q
```

结果：`3 passed in 0.31s`。

相关回归：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_reply_draft_model.py tests/test_phase5_email_thread_message_model.py tests/test_phase5_prompt_template_governance.py -q
```

结果：`9 passed in 0.31s`。

### 实现摘要

- 新增 `EmailReplyDraftStatus` 枚举，支持：
  - `drafted`
  - `pending_review`
  - `approved`
  - `sent`
  - `rejected`
  - `blocked`
  - `failed`
- 新增模型 `EmailReplyDraft`，落表 `email_reply_drafts`。
- 字段覆盖：
  - 邮件上下文：`thread_id`、`message_id`、`customer_id`
  - Agent 与 Prompt 审计：`agent_service_run_id`、`agent_task_run_id`、`prompt_template_id`、`prompt_version`、`model`
  - 语言识别：`detected_language`、`reply_language`、`language_confidence`
  - AI 建议回复：`ai_suggested_subject`、`ai_suggested_body`
  - 人工最终内容：`final_subject`、`final_body`
  - 知识命中与自动发送判断：`knowledge_hits_json`、`auto_send_allowed`、`auto_send_decision_json`
  - 人工复核：`manual_review_required`、`manual_review_reason`、`reviewed_by`、`reviewed_at`
  - 发送审计：`sent_record_id`
- 更新 ORM 关系：
  - `Customer.email_reply_drafts`
  - `EmailThread.reply_drafts`
  - `EmailMessage.reply_drafts`
- 新增 migration：`apps/api/alembic/versions/20260605_0031_create_email_reply_drafts.py`。
- 未实现邮件草稿 API、自动发送准入、EMAIL_REPLY Agent 或邮件发送器；这些属于后续 Story。

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
20260605_0030
Running upgrade 20260605_0030 -> 20260605_0031, Create email reply drafts.
20260605_0031 (head)
```

回滚与再升级：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m alembic downgrade 20260605_0030
/opt/miniconda3/envs/booking-room/bin/python -m alembic current
/opt/miniconda3/envs/booking-room/bin/python -m alembic upgrade head
/opt/miniconda3/envs/booking-room/bin/python -m alembic current
```

结果：

```text
Running downgrade 20260605_0031 -> 20260605_0030, Create email reply drafts.
20260605_0030
Running upgrade 20260605_0030 -> 20260605_0031, Create email reply drafts.
20260605_0031 (head)
```

数据库 introspection 结果：

```text
columns= 27
['id', 'thread_id', 'message_id', 'customer_id', 'agent_service_run_id', 'agent_task_run_id', 'prompt_template_id', 'prompt_version', 'model', 'detected_language', 'reply_language', 'language_confidence', 'ai_suggested_subject', 'ai_suggested_body', 'final_subject', 'final_body', 'knowledge_hits_json', 'auto_send_allowed', 'auto_send_decision_json', 'manual_review_required', 'manual_review_reason', 'status', 'reviewed_by', 'reviewed_at', 'sent_record_id', 'created_at', 'updated_at']
enum_values= ['drafted', 'pending_review', 'approved', 'sent', 'rejected', 'blocked', 'failed']
foreign_keys= [('email_reply_drafts_agent_task_run_id_fkey', 'agent_task_runs'), ('email_reply_drafts_customer_id_fkey', 'customers'), ('email_reply_drafts_message_id_fkey', 'email_messages'), ('email_reply_drafts_prompt_template_id_fkey', 'llm_prompt_templates'), ('email_reply_drafts_sent_record_id_fkey', 'outreach_records'), ('email_reply_drafts_thread_id_fkey', 'email_threads')]
```

## 两轮独立评审记录

### 第一轮评审：需求覆盖、数据模型、migration 与回归范围

结论：

- 通过。当前实现只覆盖 P5-E1-S3，未实现后续草稿 API、自动发送规则、EMAIL_REPLY Agent 或发送器。
- 通过。`email_reply_drafts` 已分离保存 AI 建议回复与最终发送内容，避免互相覆盖。
- 通过。已保存 `prompt_template_id`、`prompt_version`、`model`、`knowledge_hits_json`、`auto_send_decision_json` 等审计字段。
- 通过。状态枚举覆盖 `drafted`、`pending_review`、`approved`、`sent`、`rejected`、`blocked`、`failed`。
- 通过。migration 已在真实 PostgreSQL 上完成升级、回滚和再升级验证。

发现项：

- 新增测试文件位于 `apps/api/tests/`，仓库 `.gitignore` 会忽略 `tests/`，提交时需要使用 `git add -f` 纳入。
- 当前 Story 只建数据底座，不提供业务 API；页面和 Agent 暂不能直接使用该表。

修正结果：

- 保留新增测试文件，提交时强制纳入版本控制。
- API 与 Agent 使用能力留给后续 Story，不混入当前 Story。

### 第二轮评审：架构边界、风控和可执行性

结论：

- 通过。`apps/api` 仍是业务数据权威，本 Story 未让 `apps/agents` 直接写业务 core 表。
- 通过。本 Story 未新增任何自动触达、自动发送、邮箱发送或社交平台动作。
- 通过。自动发送判断仅以 JSON 和布尔字段存档，不代表可绕过后续硬拦截服务。
- 通过。`customer_id`、`agent_task_run_id`、`prompt_template_id`、`sent_record_id` 均允许 `SET NULL`，兼容邮件先导入、客户后识别、记录可追溯的运行路径。
- 通过。未发现与 P5-E1-S1/P5-E1-S2 的回归冲突，相关测试 `9 passed`。

发现项：

- 未发现新增实质阻塞问题。

修正结果：

- 无需修正。
