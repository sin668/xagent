# Story P5-E2-S1：Prompt 文件解析与 hash 计算服务

状态：已完成
Sprint：Sprint 2
优先级：P0
Epic：P5-E2（Prompt 入库治理）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望实现 `prompts/*.md` 文件解析、任务类型推断、内容 hash 计算和分段提取，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 实现 `prompts/*.md` 文件解析、任务类型推断、内容 hash 计算和分段提取。

**建议文件：**

- apps/api/app/services/*prompt*
- apps/api/tests/*prompt*
- prompts/*.md

**验收标准：**

- 可扫描全部 `prompts/*.md`。
- 同一文件内容得到稳定 hash。
- 无法解析 schema 的 Prompt 标记 validation_failed，不编造 schema。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E2-S1：Prompt 文件解析与 hash 计算服务。
目标：实现 `prompts/*.md` 文件解析、任务类型推断、内容 hash 计算和分段提取。
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
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_prompt_file_parser.py -q
```

结果：失败，失败原因为当前 Story 缺失解析服务：

```text
ModuleNotFoundError: No module named 'app.services.prompt_file_parser'
```

绿灯：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_prompt_file_parser.py -q
```

结果：`4 passed in 0.32s`。

相关回归：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_prompt_file_parser.py tests/test_phase5_prompt_template_governance.py tests/test_llm_prompt_template_model.py tests/test_llm_prompt_templates.py tests/test_llm_prompt_templates_api.py -q
```

结果：`22 passed, 1 warning in 5.53s`。

说明：warning 为既有知识库双路由兼容造成的 FastAPI duplicate operation ID warning，与本 Story 的 Prompt 文件解析服务无直接关系。

### 实现摘要

- 新增 `app.services.prompt_file_parser.PromptFileParserService`。
- 支持扫描 `prompts/*.md`。
- 支持解析：
  - Prompt 标题作为 `name`
  - `System Prompt` fenced code block
  - `User Prompt Template` fenced code block
  - 可选 `Output JSON Schema` fenced code block
- 支持任务类型推断：
  - `prompts/lead-extraction.md` -> `LEAD_EXTRACTION`
  - `prompts/lead-grading.md` -> `LEAD_GRADING`
  - `email-reply*` 文件名可推断为 `EMAIL_REPLY_*`
- 使用 SHA-256 计算稳定 `source_file_hash`。
- 当 Prompt 文件未内嵌可解析 JSON schema 时：
  - `output_schema_json = {}`
  - `validation_status = "validation_failed"`
  - `validation_errors_json.output_schema_json = "Prompt 文件未内嵌可解析 JSON schema，不得编造 schema。"`
- 未执行 Prompt 入库，不写 `llm_prompt_templates`；入库属于后续 P5-E2-S2。

### 本地解析验证

命令：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python - <<'PY'
from pathlib import Path
from app.services.prompt_file_parser import PromptFileParserService
root = Path('../..').resolve()
for item in PromptFileParserService.scan_prompt_directory(root / 'prompts', repo_root=root):
    print(item.source_file_path, item.task_type.value, item.source_file_hash, item.validation_status, item.validation_errors_json)
PY
```

结果：

```text
prompts/lead-extraction.md LEAD_EXTRACTION a1867fff4b5fdef5a350bcb454bf722e563daac261c1a0740121c5be64dd42f6 validation_failed {'output_schema_json': 'Prompt 文件未内嵌可解析 JSON schema，不得编造 schema。'}
prompts/lead-grading.md LEAD_GRADING f5dd07fcae122e3d1f037b3c5ef7c21a86e8eef7bafe73c4528e1767cc68247c validation_failed {'output_schema_json': 'Prompt 文件未内嵌可解析 JSON schema，不得编造 schema。'}
```

## 两轮独立评审记录

### 第一轮评审：需求覆盖、解析可靠性和回归范围

结论：

- 通过。当前实现只覆盖 P5-E2-S1，未执行 Prompt 入库、发布、回滚、API 或 Agent 改造。
- 通过。可扫描全部 `prompts/*.md`，当前识别到 `lead-extraction.md` 和 `lead-grading.md`。
- 通过。同一文件内容计算稳定 SHA-256 hash。
- 通过。可提取 System Prompt 和 User Prompt Template。
- 通过。无法解析 JSON schema 时标记 `validation_failed`，未编造 schema。

发现项：

- 真实现有两个 Prompt 文件未内嵌 JSON schema，因此解析结果按规则标记 `validation_failed`。
- 扩展回归中存在 FastAPI duplicate operation ID warning，来源于前序 Story 为兼容旧契约保留的知识库双路由声明。

修正结果：

- 保留 `validation_failed`，将 schema 入库/补齐留给后续 Prompt 入库和校验 Story。
- duplicate operation ID warning 不在当前 Story 中修复，记录为后续 API 契约整理观察项。

### 第二轮评审：架构边界、风控和可执行性

结论：

- 通过。`apps/api` 仍是业务数据权威，本 Story 未写业务 core 表。
- 通过。本 Story 未新增任何 LLM 调用、自动触达、自动发送或社交平台动作。
- 通过。解析服务只从本地 `prompts/*.md` 读取公开项目文件，不访问外部网络。
- 通过。解析失败时保守输出校验失败，不生成虚假 schema。
- 通过。Prompt 相关测试 `22 passed`，未发现与现有 Prompt 模板模型/API 的回归冲突。

发现项：

- 未发现新增实质阻塞问题。

修正结果：

- 无需修正。

## 2026-06-05 复核收口记录

本次复核未新增业务代码。当前工作树中 `PromptFileParserService` 和 `tests/test_phase5_prompt_file_parser.py` 已存在，并已由历史提交 `c4300814 feat: add prompt file parser service` 纳入当前分支。

复核命令：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_prompt_file_parser.py tests/test_phase5_prompt_template_governance.py tests/test_llm_prompt_template_model.py tests/test_llm_prompt_templates.py tests/test_llm_prompt_templates_api.py -q
```

复核结果：

```text
23 passed, 1 warning in 4.85s
```

警告说明：

- warning 为既有知识库双路由兼容造成的 FastAPI duplicate operation ID warning，位于 `apps/api/app/api/knowledge.py`，不影响 Prompt 文件解析服务验收，本 Story 不扩范围修复。

两轮复核结论：

- 第一轮：parser 可扫描全部 `prompts/*.md`，可推断任务类型、提取 System/User 分段、计算稳定 SHA-256 hash；未内嵌可解析 JSON schema 时按规则标记 `validation_failed`，未发现需要新增实现的缺口。
- 第二轮：本 Story 只读取本地 Prompt 文件并产出解析结果，不写业务表、不调用 LLM、不执行自动触达或自动发送；架构边界保持 `apps/api` 业务数据权威，未发现新的实质阻塞问题。
