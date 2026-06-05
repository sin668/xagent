# Story P5-E1-S2：新增待回复邮件线程与消息模型

状态：未开始  
Sprint：Sprint 1  
优先级：P0  
Epic：P5-E1（数据底座）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望新增 `email_threads`、`email_messages` 数据模型，支持手动/API 导入待回复邮件，并预留邮箱同步来源字段，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 新增 `email_threads`、`email_messages` 数据模型，支持手动/API 导入待回复邮件，并预留邮箱同步来源字段。

**建议文件：**

- apps/api/app/models/*email*
- apps/api/alembic/versions/*
- apps/api/tests/*email*

**验收标准：**

- 支持 inbound/outbound、线程状态、消息状态、source_type 和 external_message_id。
- 可关联 `customers`，无客户时必须明确处理策略。
- migration contract tests 通过。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E1-S2：新增待回复邮件线程与消息模型。
目标：新增 `email_threads`、`email_messages` 数据模型，支持手动/API 导入待回复邮件，并预留邮箱同步来源字段。
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
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_thread_message_model.py -q
```

结果：失败，测试收集阶段报错：

```text
ImportError: cannot import name 'EmailMessageDirection' from 'app.models.enums'
```

失败原因与当前 Story 缺口一致：尚未定义邮件线程/消息枚举、模型和 migration。

绿灯：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_thread_message_model.py -q
```

结果：`3 passed in 0.38s`。

### 实现摘要

- 新增邮件线程/消息枚举：
  - `EmailThreadStatus`
  - `EmailMessageDirection`
  - `EmailMessageStatus`
  - `EmailMessageSourceType`
- 新增模型：
  - `apps/api/app/models/email_thread.py`
  - `apps/api/app/models/email_message.py`
- 在 `Customer` 上新增 `email_threads`、`email_messages` 关系。
- 在 `app.models.__init__` 注册新模型和枚举，确保 Alembic metadata 和业务导入可识别。
- 新增 migration：`apps/api/alembic/versions/20260605_0030_create_email_threads_messages.py`。
- 支持无客户邮件导入策略：`email_threads.customer_id`、`email_messages.customer_id` 均允许为空；若客户后续识别，可由后续 Story/API 更新关联。
- 未实现邮件导入 API、邮箱同步、EMAIL_REPLY Agent 或邮件发送逻辑；这些属于后续 Story。

### 真实 PostgreSQL migration 验证

当前真实数据库：

```text
postgresql+asyncpg://postgres:***@8.129.17.71:5432/xagent
```

升级、回滚和再升级：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m alembic current
/opt/miniconda3/envs/booking-room/bin/python -m alembic upgrade head
/opt/miniconda3/envs/booking-room/bin/python -m alembic current
/opt/miniconda3/envs/booking-room/bin/python -m alembic downgrade 20260605_0029
/opt/miniconda3/envs/booking-room/bin/python -m alembic current
/opt/miniconda3/envs/booking-room/bin/python -m alembic upgrade head
/opt/miniconda3/envs/booking-room/bin/python -m alembic current
```

结果：

```text
20260605_0029
Running upgrade 20260605_0029 -> 20260605_0030
20260605_0030 (head)
Running downgrade 20260605_0030 -> 20260605_0029
20260605_0029
Running upgrade 20260605_0029 -> 20260605_0030
20260605_0030 (head)
```

数据库 introspection 结果：

```text
email_threads_columns= ['id', 'customer_id', 'subject', 'status', 'channel_account', 'last_message_at', 'created_at', 'updated_at']
email_messages_columns= ['id', 'thread_id', 'customer_id', 'direction', 'from_email', 'to_emails', 'cc_emails', 'subject', 'body_text', 'body_html', 'language', 'status', 'source_type', 'external_message_id', 'created_at', 'updated_at']
email_enums= [('emailmessagedirection', ['inbound', 'outbound']), ('emailmessagesourcetype', ['manual', 'api_import', 'mailbox_sync']), ('emailmessagestatus', ['received', 'pending_reply', 'drafted', 'sent', 'failed', 'archived']), ('emailthreadstatus', ['open', 'waiting_reply', 'replied', 'archived', 'blocked'])]
foreign_keys= [('email_messages', 'email_messages_customer_id_fkey'), ('email_messages', 'email_messages_thread_id_fkey'), ('email_threads', 'email_threads_customer_id_fkey')]
```

### 验证命令

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_prompt_template_governance.py tests/test_phase5_email_thread_message_model.py tests/test_llm_prompt_template_model.py tests/test_llm_prompt_templates.py tests/test_llm_prompt_templates_api.py -q
```

结果：`21 passed in 4.62s`。

## 两轮独立评审记录

### 第一轮评审：需求、数据模型、migration 与回归范围

结论：

- 通过。当前实现只覆盖 P5-E1-S2，未实现邮件导入 API、邮箱同步、AI 回复草稿、邮件发送或 EMAIL_REPLY Agent。
- 通过。`email_threads` 支持客户关联、主题、线程状态、渠道账号、最近邮件时间和时间戳。
- 通过。`email_messages` 支持 inbound/outbound、消息状态、source_type、external_message_id、正文、HTML、语言、收发件人和线程关联。
- 通过。无客户邮件导入策略明确为 `customer_id nullable`，后续识别客户后可补关联。
- 通过。migration 已在真实 PostgreSQL 上完成升级、回滚和再升级验证。

发现项：

- 新测试文件位于 `apps/api/tests/`，仓库 `.gitignore` 当前全局忽略 `tests/`，提交时需要使用 `git add -f` 纳入。

修正结果：

- 保留测试文件并在提交时强制纳入版本控制。

### 第二轮评审：架构边界、风控和可执行性

结论：

- 通过。`apps/api` 仍是邮件线程/消息数据权威，未让 `apps/agents` 写业务 core 表。
- 通过。本 Story 仅新增数据底座，不新增自动发送、自动触达或社媒动作。
- 通过。DNC/D/E、硬拦截、自动发送准入仍由后续服务层 Story 实现，本 Story 未绕过这些边界。
- 通过。模型字段支持后续手动/API 导入与邮箱同步预留，但未提前引入同步实现。
- 通过。相关 Prompt 与邮件模型测试通过：`21 passed in 4.62s`。

发现项：

- 未发现新增实质阻塞问题。

修正结果：

- 无需修正。
