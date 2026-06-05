# Story P5-E2-S4：Prompt 变量、schema 与测试样例校验 API

状态：已完成
Sprint：Sprint 2
优先级：P0
Epic：P5-E2（Prompt 入库治理）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望提供 Prompt 校验和测试样例预览 API，发布前验证变量、JSON Schema 和风险提示，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 提供 Prompt 校验和测试样例预览 API，发布前验证变量、JSON Schema 和风险提示。

**建议文件：**

- apps/api/app/services/*prompt*
- apps/api/app/routers/*prompt*
- apps/api/tests/*prompt_validation*

**验收标准：**

- 校验必填变量、JSON Schema 可解析、任务类型合法。
- EMAIL_REPLY Prompt 必须包含输出契约和风险边界。
- 校验失败不会发布。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E2-S4：Prompt 变量、schema 与测试样例校验 API。
目标：提供 Prompt 校验和测试样例预览 API，发布前验证变量、JSON Schema 和风险提示。
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
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_prompt_validation_preview_api.py -q
```

结果：失败，失败原因为当前 Story 缺失校验预览 API：

```text
POST /llm-prompt-templates/drafts/{template_id}/validation-preview 返回 404
```

绿灯：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_prompt_validation_preview_api.py -q
```

结果：`4 passed in 6.93s`。

相关回归：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_prompt_validation_preview_api.py tests/test_phase5_prompt_draft_edit_api.py tests/test_llm_prompt_templates_api.py tests/test_llm_prompt_template_model.py tests/test_phase5_prompt_import_service.py tests/test_phase5_prompt_file_parser.py tests/test_phase5_prompt_template_governance.py -q
```

结果：`30 passed, 1 warning in 16.73s`。

说明：warning 为既有知识库双路由兼容造成的 FastAPI duplicate operation ID warning，与本 Story 的 Prompt 校验预览 API 无直接关系。

### 实现摘要

- 新增 `LLMPromptTemplateValidationPreviewRequest`。
- 新增 `LLMPromptTemplateValidationPreviewResponse`。
- 新增 `LLMPromptTemplateService.validate_draft_preview()`。
- 新增 API：
  - `POST /llm-prompt-templates/drafts/{template_id}/validation-preview`
- 校验内容：
  - 从 `user_prompt_template` 提取 `{{variable}}` 必填变量。
  - 校验 `sample_variables` 是否覆盖全部必填变量。
  - 校验 `output_schema_json` 是包含 `type` 的 JSON Schema object。
  - 校验任务类型合法。
  - `EMAIL_REPLY_*` Prompt 必须包含风险边界关键词：`不自动发送`、`不编造`。
- 校验预览会渲染测试样例中的 user prompt，返回 `rendered_user_prompt`。
- 校验结果会回写草稿：
  - 通过：`validation_status = validation_passed`，`validation_errors_json = null`
  - 失败：`validation_status = validation_failed`，`validation_errors_json = errors`
- `would_publish` 固定为 `false`，本 Story 不执行发布。
- 权限边界沿用草稿治理：
  - `admin` / `tech_admin` 可校验。
  - 其他角色返回 403。

### 真实 PostgreSQL / API 验证

测试通过 FastAPI `TestClient` 调用真实 API，并通过 `AsyncSessionLocal` 连接真实 PostgreSQL 创建和清理测试数据。

验证覆盖：

- 合法 EMAIL_REPLY Prompt 校验通过并回写 `validation_passed`。
- 缺少必填变量时校验失败，不发布，草稿仍为 `draft`。
- EMAIL_REPLY Prompt 缺少风险边界时校验失败。
- `customer_service` 角色校验返回 403。

真实库残留检查：

```text
leftover_phase5_validation_api_rows=0
```

## 两轮独立评审记录

### 第一轮评审：需求覆盖、校验逻辑、API 行为和回归范围

结论：

- 通过。当前实现只覆盖 P5-E2-S4，未实现发布、回滚或默认版本切换。
- 通过。校验必填变量、JSON Schema 基本结构和任务类型。
- 通过。EMAIL_REPLY Prompt 必须包含输出契约和风险边界。
- 通过。校验失败不会发布，`would_publish=false`，草稿状态保持 `draft`。
- 通过。校验结果回写 `validation_status` 和 `validation_errors_json`，便于后台展示。

发现项：

- 当前 JSON Schema 校验为基础结构校验，未引入完整 JSON Schema validator；后续可在校验增强 Story 中升级。
- 新增测试文件位于 `apps/api/tests/`，仓库 `.gitignore` 会忽略 `tests/`，提交时需要使用 `git add -f` 纳入。

修正结果：

- 保持本 Story 范围为发布前预览校验，不混入发布逻辑。
- 提交时强制纳入新增测试文件。

### 第二轮评审：架构边界、风控和可执行性

结论：

- 通过。`apps/api` 仍是业务数据权威，校验预览由 API service 控制。
- 通过。本 Story 未新增任何 LLM 调用、自动触达、自动发送或社交平台动作。
- 通过。`apps/agents` 未直接写业务 core 表。
- 通过。EMAIL_REPLY 风险边界校验强化了“不自动发送、不编造”的发布前约束。
- 通过。Prompt 相关测试 `30 passed`，未发现新增阻塞回归。

发现项：

- 未发现新增实质阻塞问题。

修正结果：

- 无需修正。

## 2026-06-05 复核收口记录

本次复核未新增业务代码。当前工作树中 Prompt 校验预览 API 已存在，并已由历史提交 `4f97110a feat: add prompt validation preview api` 纳入当前分支。

复核命令：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_prompt_validation_preview_api.py tests/test_phase5_prompt_draft_edit_api.py tests/test_llm_prompt_templates_api.py tests/test_llm_prompt_template_model.py tests/test_phase5_prompt_import_service.py tests/test_phase5_prompt_file_parser.py tests/test_phase5_prompt_template_governance.py -q
```

复核结果：

```text
31 passed, 1 warning in 13.71s
```

警告说明：

- warning 为既有知识库双路由兼容造成的 FastAPI duplicate operation ID warning，位于 `apps/api/app/api/knowledge.py`，不影响 Prompt 校验预览 API 验收，本 Story 不扩范围修复。

两轮复核结论：

- 第一轮：校验预览 API 已覆盖必填变量、JSON Schema 基础结构、任务类型和 EMAIL_REPLY 风险边界校验；校验失败只回写 `validation_failed`，`would_publish=false`，不会发布。
- 第二轮：本 Story 只校验草稿并渲染测试样例，不调用 LLM、不切默认版本、不执行自动触达或自动发送；架构边界保持 `apps/api` 业务数据权威，未发现新的实质阻塞问题。
