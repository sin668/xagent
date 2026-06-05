# Story P5-E2-S3：Prompt 草稿创建与编辑 API

状态：未开始  
Sprint：Sprint 2  
优先级：P0  
Epic：P5-E2（Prompt 入库治理）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望提供后台创建 Prompt 草稿、编辑草稿和查看草稿详情 API，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 提供后台创建 Prompt 草稿、编辑草稿和查看草稿详情 API。

**建议文件：**

- apps/api/app/routers/*prompt*
- apps/api/app/schemas/*prompt*
- apps/api/tests/*prompt*

**验收标准：**

- 只能编辑 draft，不允许直接修改 active。
- 返回版本、来源 hash、校验状态和审计摘要。
- 权限边界区分 admin/tech_admin。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E2-S3：Prompt 草稿创建与编辑 API。
目标：提供后台创建 Prompt 草稿、编辑草稿和查看草稿详情 API。
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
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_prompt_draft_edit_api.py -q
```

结果：失败，失败原因为当前 Story 缺失草稿 API：

```text
POST /llm-prompt-templates/drafts 返回 404
```

绿灯：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_prompt_draft_edit_api.py -q
```

结果：`4 passed in 5.34s`。

相关回归：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_prompt_draft_edit_api.py tests/test_llm_prompt_templates_api.py tests/test_llm_prompt_template_model.py tests/test_phase5_prompt_import_service.py tests/test_phase5_prompt_file_parser.py tests/test_phase5_prompt_template_governance.py -q
```

结果：`26 passed, 1 warning in 16.03s`。

说明：warning 为既有知识库双路由兼容造成的 FastAPI duplicate operation ID warning，与本 Story 的 Prompt 草稿 API 无直接关系。

### 实现摘要

- 新增草稿创建请求 `LLMPromptTemplateDraftCreate`。
- 新增草稿编辑请求 `LLMPromptTemplateDraftUpdate`。
- 新增草稿详情响应 `LLMPromptTemplateDraftDetailResponse`，包含 `audit_summary`。
- 新增 `LLMPromptTemplateService.create_draft()`。
- 新增 `LLMPromptTemplateService.update_draft()`。
- 新增权限边界：
  - `admin` 可创建和编辑草稿。
  - `tech_admin` 可创建和编辑草稿。
  - 其他角色返回 403。
- 新增 API：
  - `POST /llm-prompt-templates/drafts`
  - `GET /llm-prompt-templates/drafts/{template_id}`
  - `PATCH /llm-prompt-templates/drafts/{template_id}`
- 草稿创建强制：
  - `status = draft`
  - `is_default = false`
  - `created_by = actor`
- 草稿编辑强制：
  - 只能编辑 `draft`。
  - 尝试编辑 `active` 返回 409。
- 返回字段包含版本、来源 hash、校验状态、变更摘要和审计摘要。
- 未实现发布、默认版本切换、回滚或校验预览；这些属于后续 Story。

### 真实 PostgreSQL / API 验证

测试通过 FastAPI `TestClient` 调用真实 API，并通过 `AsyncSessionLocal` 连接真实 PostgreSQL 创建和清理测试数据。

验证覆盖：

- `admin` 创建草稿成功。
- `tech_admin` 编辑草稿成功。
- `customer_service` 创建草稿返回 403。
- 编辑 `active` Prompt 返回 409。
- 草稿详情返回：
  - `version`
  - `source_file_hash`
  - `validation_status`
  - `audit_summary.created_by`
  - `audit_summary.updated_at`

真实库残留检查：

```text
leftover_phase5_draft_api_rows=0
```

## 两轮独立评审记录

### 第一轮评审：需求覆盖、API 行为、权限和回归范围

结论：

- 通过。当前实现只覆盖 P5-E2-S3，未实现发布、回滚、默认版本切换或校验预览。
- 通过。后台可创建 Prompt 草稿、编辑草稿和查看草稿详情。
- 通过。只能编辑 `draft`，不允许直接修改 `active`。
- 通过。响应包含版本、来源 hash、校验状态和审计摘要。
- 通过。权限边界区分 `admin` / `tech_admin`，其他角色禁止写入。

发现项：

- 原有 `test_prompt_template_api_is_read_only_for_phase_two` 名称仍保留，但第五阶段已新增草稿写接口；该测试只检查基础列表和详情路径仍为 GET，不阻塞当前 Story。
- 新增测试文件位于 `apps/api/tests/`，仓库 `.gitignore` 会忽略 `tests/`，提交时需要使用 `git add -f` 纳入。

修正结果：

- 保留基础列表/详情只读路径不变，同时新增 `/drafts` 专用写接口，避免误开放通用模板写入。
- 提交时强制纳入新增测试文件。

### 第二轮评审：架构边界、风控和可执行性

结论：

- 通过。`apps/api` 仍是业务数据权威，草稿写入由 API service 控制。
- 通过。本 Story 未新增任何 LLM 调用、自动触达、自动发送或社交平台动作。
- 通过。`apps/agents` 未直接写业务 core 表。
- 通过。草稿 API 只操作 `llm_prompt_templates`，不改变线上 active 默认版本。
- 通过。Prompt 相关测试 `26 passed`，未发现新增阻塞回归。

发现项：

- 未发现新增实质阻塞问题。

修正结果：

- 无需修正。
