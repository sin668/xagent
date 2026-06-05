# Story P5-E2-S6：Prompt 治理审计与权限边界

状态：已完成
Sprint：Sprint 2  
优先级：P1  
Epic：P5-E2（Prompt 入库治理）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望完善 Prompt 查看、编辑、发布、Schema 编辑和回滚的角色权限与审计记录，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 完善 Prompt 查看、编辑、发布、Schema 编辑和回滚的角色权限与审计记录。

**建议文件：**

- apps/api/app/services/*audit*
- apps/api/app/routers/*prompt*
- apps/api/tests/*permission*

**验收标准：**

- operator/sales_manager 不能编辑或发布 Prompt。
- tech_admin 才能编辑 Schema。
- 发布、回滚、默认版本切换均写入审计。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E2-S6：Prompt 治理审计与权限边界。
目标：完善 Prompt 查看、编辑、发布、Schema 编辑和回滚的角色权限与审计记录。
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

- 新增 `apps/api/tests/test_phase5_prompt_governance_permissions_audit_api.py`。
- 覆盖 operator/sales_manager 禁止编辑或发布 Prompt、仅 tech_admin 可编辑 `output_schema_json`、发布/默认版本切换/回滚审计可查询。
- 首次运行：`/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_prompt_governance_permissions_audit_api.py -q`
- 红灯结果：2 个失败、1 个通过。
  - admin 编辑 `output_schema_json` 返回 200，未满足“tech_admin 才能编辑 Schema”。
  - `/llm-prompt-templates/{template_id}/audit-logs` 返回 404，审计查询 API 未实现。
  - operator/sales_manager 禁止编辑或发布已由既有权限规则覆盖，通过。

### 实现摘要

- 在 `LLMPromptTemplateService` 中新增 `SCHEMA_EDITOR_ROLES={"tech_admin"}` 和 `ensure_schema_editor`。
- 编辑草稿时，如果 payload 包含非空 `output_schema_json`，必须由 `tech_admin` 执行；`admin/operator/sales_manager` 均不能编辑 Schema。
- 复用现有 `review_logs` 表作为 Prompt 治理审计载体，`agent_name="llm_prompt_governance"`。
- 发布、默认版本切换、回滚成功后写入 `ReviewLog`：
  - `prompt_publish`
  - `prompt_set_default`
  - `prompt_rollback`
- 新增 `GET /llm-prompt-templates/{template_id}/audit-logs`，返回指定 Prompt template 的治理审计记录。
- 新增审计响应 schema：`LLMPromptTemplateAuditLogResponse` 与 `LLMPromptTemplateAuditLogListResponse`。

### 真实 PostgreSQL / API 验证

- 当前 Story 单测：
  - `/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_prompt_governance_permissions_audit_api.py -q`
  - 结果：`3 passed`。
- Prompt 治理相关回归：
  - `/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_prompt_governance_permissions_audit_api.py tests/test_phase5_prompt_publish_rollback_api.py tests/test_phase5_prompt_validation_preview_api.py tests/test_phase5_prompt_draft_edit_api.py tests/test_llm_prompt_templates_api.py tests/test_llm_prompt_template_model.py tests/test_phase5_prompt_import_service.py tests/test_phase5_prompt_file_parser.py tests/test_phase5_prompt_template_governance.py tests/test_phase5_migration_contracts.py -q`
  - 结果：`41 passed, 9 warnings`。
  - 已知 warning：
    - `review_logs.created_at` 使用 `datetime.utcnow()` 触发 Python 3.12 deprecation warning，非本 Story 行为阻塞。
    - FastAPI duplicate operation ID 来自知识库兼容路由，非本 Story 引入。
- 测试数据残留检查：
  - 真实 PostgreSQL 中 `phase5_governance_api_%` Prompt 记录数量：`0`。
  - 真实 PostgreSQL 中当前 Story 相关 `llm_prompt_governance` 审计残留数量：`0`。

## 两轮独立多维度评审

### 第一轮评审：权限、审计、API 行为

- 结论：本 Story 的三个验收点均已覆盖并通过真实 API/真实 PostgreSQL 测试。
- 发现项 1：既有 `admin` 可编辑草稿，同时也能编辑 `output_schema_json`，不符合“tech_admin 才能编辑 Schema”。
- 修正结果 1：服务层对 `output_schema_json` 做字段级权限校验，只有 `tech_admin` 可改 Schema；operator/sales_manager 仍被禁止编辑或发布。
- 发现项 2：发布、默认版本切换、回滚虽然写入模板字段，但没有可查询的独立治理审计记录。
- 修正结果 2：复用 `review_logs` 写入 `prompt_publish`、`prompt_set_default`、`prompt_rollback`，并新增审计查询 API。
- 发现项 3：审计查询如果不校验 template 是否存在，可能让后台误读空日志为无操作历史。
- 修正结果 3：`GET /llm-prompt-templates/{template_id}/audit-logs` 先校验 Prompt template 存在，不存在返回 404。

### 第二轮评审：范围控制、历史保留、回归风险

- 结论：第二轮未发现新增实质阻塞问题；当前实现只覆盖 P5-E2-S6，没有进入知识库、embedding、后台页面或 EMAIL_REPLY Agent。
- 发现项 1：审计应记录动作结果，但不应覆盖或删除 Prompt 历史版本。
- 修正结果 1：审计只新增 `ReviewLog`，不改变 P5-E2-S5 的发布、默认切换和回滚历史保留语义。
- 发现项 2：字段级权限若只放在 API 层，后续服务复用可能绕过 Schema 权限。
- 修正结果 2：权限校验放在 `LLMPromptTemplateService.update_draft` 内，API 和后续调用方都走统一服务边界。
- 发现项 3：新增测试可能在真实 PostgreSQL 留下 Prompt 或审计测试数据。
- 修正结果 3：测试 fixture 同时清理 `LLMPromptTemplate` 和 `ReviewLog`，并用真实库查询确认残留为 0。
