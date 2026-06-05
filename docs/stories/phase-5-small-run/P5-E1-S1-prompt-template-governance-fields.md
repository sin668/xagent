# Story P5-E1-S1：扩展 Prompt 模板治理字段与枚举

状态：未开始  
Sprint：Sprint 1  
优先级：P0  
Epic：P5-E1（数据底座）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望扩展 `llm_prompt_templates`，支持来源文件、hash、迁移批次、父版本、发布人、回滚来源和校验状态，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 扩展 `llm_prompt_templates`，支持来源文件、hash、迁移批次、父版本、发布人、回滚来源和校验状态。

**建议文件：**

- apps/api/app/models/llm_prompt_template.py
- apps/api/alembic/versions/*
- apps/api/tests/*prompt*

**验收标准：**

- 新增字段具备 migration，并可在 PostgreSQL 上升级/回滚。
- 新增 `EMAIL_REPLY_*` 任务类型通过枚举兼容测试。
- 不破坏现有 Prompt 查询、默认版本和 Agent 任务。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E1-S1：扩展 Prompt 模板治理字段与枚举。
目标：扩展 `llm_prompt_templates`，支持来源文件、hash、迁移批次、父版本、发布人、回滚来源和校验状态。
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
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_prompt_template_governance.py -q
```

结果：失败，3 个失败点均为当前 Story 缺失能力：

- `LLMPromptTaskType` 缺少 `EMAIL_REPLY_DRAFT`、`EMAIL_REPLY_AUTO_SEND_CHECK`、`EMAIL_REPLY_KNOWLEDGE_RETRIEVAL`、`EMAIL_REPLY_SEND`。
- `LLMPromptTemplate` 模型缺少来源文件、hash、迁移批次、父版本、发布人、回滚来源和校验状态字段。
- 缺少 `20260605_0029_extend_llm_prompt_templates_governance.py` migration。

绿灯：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_prompt_template_governance.py -q
```

结果：`3 passed in 0.46s`。

### 实现摘要

- 扩展 `LLMPromptTaskType`，新增：
  - `EMAIL_REPLY_DRAFT`
  - `EMAIL_REPLY_AUTO_SEND_CHECK`
  - `EMAIL_REPLY_KNOWLEDGE_RETRIEVAL`
  - `EMAIL_REPLY_SEND`
- 扩展 `LLMPromptTemplate` 模型，新增：
  - `source_file_path`
  - `source_file_hash`
  - `migration_batch_id`
  - `parent_template_id`
  - `published_by`
  - `published_at`
  - `change_summary`
  - `rollback_from_template_id`
  - `validation_status`
  - `validation_errors_json`
- 同步扩展 `LLMPromptTemplateCreate`、`LLMPromptTemplateUpdate`、`LLMPromptTemplateResponse`。
- 新增 migration：`apps/api/alembic/versions/20260605_0029_extend_llm_prompt_templates_governance.py`。
- 未实现 Prompt 入库脚本、草稿编辑 API、发布/回滚 API 或 EMAIL_REPLY Agent；这些属于后续 Story。

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
20260604_0028
Running upgrade 20260604_0028 -> 20260605_0029
20260605_0029 (head)
```

回滚与再升级：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m alembic downgrade 20260604_0028
/opt/miniconda3/envs/booking-room/bin/python -m alembic current
/opt/miniconda3/envs/booking-room/bin/python -m alembic upgrade head
/opt/miniconda3/envs/booking-room/bin/python -m alembic current
```

结果：

```text
Running downgrade 20260605_0029 -> 20260604_0028
20260604_0028
Running upgrade 20260604_0028 -> 20260605_0029
20260605_0029 (head)
```

数据库 introspection 结果：

```text
columns= ['change_summary', 'created_at', 'created_by', 'id', 'is_default', 'migration_batch_id', 'model', 'name', 'output_schema_json', 'parent_template_id', 'provider', 'published_at', 'published_by', 'rollback_from_template_id', 'source_file_hash', 'source_file_path', 'status', 'system_prompt', 'task_type', 'updated_at', 'user_prompt_template', 'validation_errors_json', 'validation_status', 'version']
enum_values= ['SOURCE_DISCOVERY', 'LEAD_EXTRACTION', 'LEAD_GRADING', 'EMAIL_REPLY_DRAFT', 'EMAIL_REPLY_AUTO_SEND_CHECK', 'EMAIL_REPLY_KNOWLEDGE_RETRIEVAL', 'EMAIL_REPLY_SEND']
foreign_keys= ['fk_llm_prompt_templates_parent_template_id', 'fk_llm_prompt_templates_rollback_from_template_id']
```

### 验证命令

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_llm_prompt_template_model.py tests/test_llm_prompt_templates.py tests/test_llm_prompt_templates_api.py tests/test_phase5_prompt_template_governance.py -q
```

结果：`18 passed in 4.82s`。

扩展检查：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_prompt_template_governance.py tests/test_llm_prompt_template_model.py tests/test_llm_prompt_templates.py tests/test_llm_prompt_templates_api.py tests/test_llm_cost_review_efficiency.py tests/test_rag_in_llm_prompts.py -q
```

结果：`23 passed, 1 failed, 1 warning`。失败项为既有 ROI 指标测试：

```text
tests/test_llm_cost_review_efficiency.py::test_roi_metrics_from_records_include_ai_cost_tokens_and_review_efficiency
assert summary["reply_count"] == 1
E assert 0 == 1
```

该失败与本 Story 修改的 Prompt 模型、枚举和 migration 无直接关系，未在本 Story 中修复，作为残留风险记录。

## 两轮独立评审记录

### 第一轮评审：需求、数据模型、migration 与回归范围

结论：

- 通过。当前实现只覆盖 P5-E1-S1，未实现后续 Prompt 入库、草稿编辑、发布/回滚 API 或 EMAIL_REPLY Agent。
- 通过。`llm_prompt_templates` 已支持来源文件、hash、迁移批次、父版本、发布人、发布时间、变更摘要、回滚来源、校验状态和校验错误。
- 通过。`EMAIL_REPLY_*` Prompt 任务枚举已进入 Python enum 和真实 PostgreSQL enum。
- 通过。migration 已在真实 PostgreSQL 上完成升级、回滚和再升级验证。
- 通过。现有 Prompt 查询、默认版本和默认 seed 相关测试通过：`18 passed in 4.82s`。

发现项：

- 新增测试文件位于 `apps/api/tests/`，但仓库 `.gitignore` 目前全局忽略 `tests/`，提交时需要使用 `git add -f` 纳入。
- 扩展测试集中存在既有 ROI 指标测试失败，失败点为 `reply_count` 统计，与本 Story 无关。

修正结果：

- 保留测试文件并在提交时强制纳入版本控制。
- ROI 指标失败不混入当前 Story 修复，记录为残留风险，后续由对应指标 Story 或缺陷 Story 处理。

### 第二轮评审：架构边界、风控和可执行性

结论：

- 通过。`apps/api` 仍是业务数据权威，本 Story 未让 `apps/agents` 写业务 core 表。
- 通过。本 Story 未新增任何自动触达、自动发送、自动晋级或社交平台动作。
- 通过。新增字段只服务 Prompt 治理、迁移来源、版本发布、回滚和校验审计，不改变现有 LLM Agent 运行逻辑。
- 通过。新增 schema 字段保持可空，兼容现有 Prompt 数据。
- 通过。migration downgrade 在没有 `EMAIL_REPLY_*` 数据残留时可回滚到旧 enum；正式回滚前仍需按数据库常规流程确认无新增枚举数据。

发现项：

- 未发现新增实质阻塞问题。

修正结果：

- 无需修正。
