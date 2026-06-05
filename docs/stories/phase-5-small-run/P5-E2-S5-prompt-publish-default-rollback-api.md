# Story P5-E2-S5：Prompt 发布、默认版本与回滚 API

状态：已完成
Sprint：Sprint 2  
优先级：P0  
Epic：P5-E2（Prompt 入库治理）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望实现 Prompt 发布新版本、切换默认版本和回滚能力，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 实现 Prompt 发布新版本、切换默认版本和回滚能力。

**建议文件：**

- apps/api/app/routers/*prompt*
- apps/api/app/services/*prompt*
- apps/api/tests/*prompt_publish*

**验收标准：**

- 发布草稿生成 active 版本并写审计。
- 同一 task_type/provider/model 只允许一个默认 active。
- 回滚会创建或恢复可审计版本，不丢历史。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E2-S5：Prompt 发布、默认版本与回滚 API。
目标：实现 Prompt 发布新版本、切换默认版本和回滚能力。
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

- 新增 `apps/api/tests/test_phase5_prompt_publish_rollback_api.py`，覆盖发布草稿、拒绝未校验草稿、切换默认版本、回滚生成可审计草稿。
- 首次运行：`/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_prompt_publish_rollback_api.py -q`
- 红灯结果：4 个用例失败，失败原因均为接口未实现导致 404，符合预期红灯。

### 实现摘要

- 在 `apps/api/app/api/llm_prompt_templates.py` 新增：
  - `POST /llm-prompt-templates/drafts/{template_id}/publish`
  - `POST /llm-prompt-templates/{template_id}/set-default`
  - `POST /llm-prompt-templates/{template_id}/rollback`
- 在 `apps/api/app/services/llm_prompt_templates.py` 新增 Prompt 发布、默认切换、回滚草稿生成逻辑。
- 发布草稿要求 `draft` 且 `validation_status=validation_passed`，发布后写入 `published_by`、`published_at`、`change_summary`，并将同 scope 旧默认 active 切为 paused。
- 回滚不覆盖历史版本，而是复制目标历史版本内容生成新的 `draft`，记录 `parent_template_id`、`rollback_from_template_id` 和 `change_summary`。
- 新增 `apps/api/alembic/versions/20260605_0034_scope_llm_prompt_default_by_provider_model.py`，将默认 Prompt 唯一索引从 `task_type` 调整为 `task_type/provider/model`，与本 Story 验收标准一致。
- 同步 `apps/api/app/migration_contracts/phase5.py` 与迁移契约测试，确保真实 PostgreSQL head 和索引结构可被验证。
- 同步 Prompt 默认种子与 Prompt 文件导入逻辑，使默认版本查找按 `task_type/provider/model` 判断。

### 真实 PostgreSQL / API 验证

- 执行真实 PostgreSQL migration：
  - `/opt/miniconda3/envs/booking-room/bin/python -m alembic upgrade head`
  - 结果：真实库从 `20260605_0033` 升级到 `20260605_0034`。
- 当前 Story 单测：
  - `/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_prompt_publish_rollback_api.py -q`
  - 结果：`4 passed`。
- 相关 Prompt 治理回归：
  - `/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_prompt_publish_rollback_api.py tests/test_phase5_prompt_validation_preview_api.py tests/test_phase5_prompt_draft_edit_api.py tests/test_llm_prompt_templates_api.py tests/test_llm_prompt_template_model.py tests/test_phase5_prompt_import_service.py tests/test_phase5_prompt_file_parser.py tests/test_phase5_prompt_template_governance.py tests/test_phase5_migration_contracts.py -q`
  - 结果：`38 passed, 1 warning`。
  - 已知 warning：FastAPI duplicate operation ID 来自知识库兼容路由，非本 Story 阻塞。
- 测试数据残留检查：
  - 查询真实 PostgreSQL 中 `phase5_publish_api_%` 记录数量。
  - 结果：`0`，当前 Story 临时测试数据已清理。

## 两轮独立多维度评审

### 第一轮评审：业务规则、数据库约束、API 行为

- 结论：本 Story 的核心 API 行为已覆盖发布、默认切换、回滚三条主路径；发布审计字段和回滚链路字段可追踪，符合 Prompt 入库治理要求。
- 发现项 1：真实 PostgreSQL 旧唯一索引只限制 `task_type` 一个默认 active，与验收标准 `task_type/provider/model` 不一致。
- 修正结果 1：新增 `20260605_0034` migration，将唯一索引调整为 `task_type/provider/model` scope，并更新迁移契约和真实库 head。
- 发现项 2：切换默认版本时，SQLAlchemy flush 顺序可能先设置新默认 active，再落库旧默认 paused，触发唯一索引冲突。
- 修正结果 2：在清理旧默认 active 后显式 `flush()`，保证数据库先看到旧默认退出，再设置新默认。
- 发现项 3：旧回归测试直接插入同 scope 默认 active，与真实库已有默认版本冲突。
- 修正结果 3：将该测试 fixture 的 provider/model 调整为独立 scope，保留“active 模板不可编辑”的行为验证。

### 第二轮评审：权限边界、历史保留、回归风险

- 结论：第二轮未发现新增实质阻塞问题；当前实现没有绕过 `apps/api` 业务权威，没有删除历史版本，未扩展到下一个 Story。
- 发现项 1：发布与切换默认接口需要沿用草稿编辑权限边界，否则运营外角色可能绕过 Prompt 治理。
- 修正结果 1：服务层统一调用 `ensure_draft_editor`，仅允许 `admin` 和 `tech_admin` 执行发布、默认切换和回滚。
- 发现项 2：回滚如果直接覆盖 active 历史，会丢失审计链路。
- 修正结果 2：回滚采用新建 draft 的方式保留历史，写入 `parent_template_id` 和 `rollback_from_template_id`。
- 发现项 3：迁移契约需要覆盖新索引，否则真实库未升级时 API 单测可能表现为数据库异常。
- 修正结果 3：迁移契约新增 `indexes` 校验，并在真实 PostgreSQL 上验证当前 head 为 `20260605_0034`。
