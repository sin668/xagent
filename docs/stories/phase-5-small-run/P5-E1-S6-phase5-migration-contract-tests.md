# Story P5-E1-S6：第五阶段数据 migration contract tests

状态：未开始  
Sprint：Sprint 1  
优先级：P0  
Epic：P5-E1（数据底座）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望为第五阶段新增/扩展表建立 PostgreSQL migration contract tests，确保真实数据库可迁移，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 为第五阶段新增/扩展表建立 PostgreSQL migration contract tests，确保真实数据库可迁移。

**建议文件：**

- apps/api/tests/*migration*
- apps/api/alembic/versions/*

**验收标准：**

- 在真实 PostgreSQL 测试库执行 upgrade 后能查询新增表和字段。
- 枚举扩展不破坏历史数据。
- 执行 downgrade 或等价回滚策略有文档说明。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E1-S6：第五阶段数据 migration contract tests。
目标：为第五阶段新增/扩展表建立 PostgreSQL migration contract tests，确保真实数据库可迁移。
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
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_migration_contracts.py -q
```

结果：失败，失败原因为当前 Story 缺失 contract manifest：

```text
ModuleNotFoundError: No module named 'app.migration_contracts'
```

绿灯：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_migration_contracts.py -q
```

结果：`3 passed in 0.92s`。

相关回归：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_migration_contracts.py tests/test_phase5_knowledge_usage_quality_model.py tests/test_phase5_email_send_attempt_model.py tests/test_phase5_email_reply_draft_model.py tests/test_phase5_email_thread_message_model.py tests/test_phase5_prompt_template_governance.py -q
```

结果：`19 passed in 1.36s`。

### 实现摘要

- 新增 `app.migration_contracts.phase5`，集中声明第五阶段数据底座 migration contract。
- contract 覆盖：
  - `20260605_0029_extend_llm_prompt_templates_governance.py`
  - `20260605_0030_create_email_threads_messages.py`
  - `20260605_0031_create_email_reply_drafts.py`
  - `20260605_0032_create_email_send_attempts.py`
  - `20260605_0033_create_knowledge_usage_quality.py`
- 新增 `PHASE5_ROLLBACK_STRATEGY`，明确等价回滚策略为：
  - `20260605_0033 -> 20260605_0032 -> 20260605_0031 -> 20260605_0030 -> 20260605_0029 -> 20260605_0028`
  - 回滚前必须确认新增表中无需要保留的业务数据，或先完成数据备份和迁移归档。
- 新增 `tests/test_phase5_migration_contracts.py`，检查：
  - contract manifest 覆盖预期 revision。
  - migration 文件声明正确 revision、down_revision、upgrade、downgrade。
  - 真实 PostgreSQL 当前 revision 为第五阶段最新 head。
  - 真实 PostgreSQL 中新增/扩展表字段和枚举值符合 contract。
- 本 Story 未新增业务表字段、API、Agent 或页面。

### 真实 PostgreSQL 验证

当前真实数据库：

```text
postgresql+asyncpg://postgres:***@8.129.17.71:5432/xagent
```

当前版本：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m alembic current
```

结果：

```text
20260605_0033 (head)
```

contract 测试已在真实 PostgreSQL 上查询 `alembic_version`、`information_schema.columns` 和 `pg_enum`，确认第五阶段新增表字段和枚举值已落库。

## 两轮独立评审记录

### 第一轮评审：需求覆盖、测试强度、migration 与真实库验证

结论：

- 通过。当前实现只覆盖 P5-E1-S6，未实现任何新业务表、API、Agent 或页面。
- 通过。contract 覆盖第五阶段 P5-E1-S1 到 P5-E1-S5 的新增/扩展 migration。
- 通过。真实 PostgreSQL contract 测试会查询当前 head、表字段和枚举值，不只是静态读取 migration 文件。
- 通过。migration 文件均要求存在 `upgrade()` 和 `downgrade()`，并校验 revision/down_revision。
- 通过。回滚策略已在 manifest 中明确记录。

发现项：

- 新增测试文件位于 `apps/api/tests/`，仓库 `.gitignore` 会忽略 `tests/`，提交时需要使用 `git add -f` 纳入。
- contract 测试依赖真实 PostgreSQL 当前已升级到 `20260605_0033 (head)`，如果后续环境切换为未迁移测试库，需先执行 migration。

修正结果：

- 保留新增测试文件，提交时强制纳入版本控制。
- 在执行记录中明确真实库当前版本和测试依赖。

### 第二轮评审：架构边界、风控和可执行性

结论：

- 通过。`apps/api` 仍是业务数据权威，本 Story 未让 `apps/agents` 直接写业务 core 表。
- 通过。本 Story 未新增任何自动触达、自动发送、邮箱发送动作或社交平台动作。
- 通过。contract manifest 只描述 migration 可验证契约，不改变运行时业务流程。
- 通过。回滚策略强调回滚前数据备份和归档，不鼓励在有业务数据时盲目 downgrade。
- 通过。未发现与 P5-E1-S1/S2/S3/S4/S5 的回归冲突，相关测试 `19 passed`。

发现项：

- 未发现新增实质阻塞问题。

修正结果：

- 无需修正。
