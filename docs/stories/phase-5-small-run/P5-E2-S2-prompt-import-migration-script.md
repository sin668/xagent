# Story P5-E2-S2：Prompt 入库迁移脚本

状态：未开始  
Sprint：Sprint 2  
优先级：P0  
Epic：P5-E2（Prompt 入库治理）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望创建幂等脚本，将文件 Prompt 写入 `llm_prompt_templates`，文件保留为基线，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 创建幂等脚本，将文件 Prompt 写入 `llm_prompt_templates`，文件保留为基线。

**建议文件：**

- scripts/*prompt*
- apps/api/app/services/*prompt*
- apps/api/tests/*prompt_import*

**验收标准：**

- 同一 `source_file_path + source_file_hash + version` 不重复写入。
- 文件 hash 变化且已有 active 默认版本时创建草稿，不覆盖线上版本。
- 脚本可在 macOS 本地直接执行并输出迁移报告。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E2-S2：Prompt 入库迁移脚本。
目标：创建幂等脚本，将文件 Prompt 写入 `llm_prompt_templates`，文件保留为基线。
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
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_prompt_import_service.py -q
```

结果：失败，失败原因为当前 Story 缺失入库服务：

```text
ModuleNotFoundError: No module named 'app.services.prompt_import'
```

绿灯：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_prompt_import_service.py -q
```

结果：`4 passed in 4.98s`。

相关回归：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_prompt_import_service.py tests/test_phase5_prompt_file_parser.py tests/test_phase5_prompt_template_governance.py tests/test_llm_prompt_template_model.py tests/test_llm_prompt_templates.py tests/test_llm_prompt_templates_api.py -q
```

结果：`26 passed, 1 warning in 7.46s`。

说明：warning 为既有知识库双路由兼容造成的 FastAPI duplicate operation ID warning，与本 Story 的 Prompt 入库脚本无直接关系。

### 实现摘要

- 新增 `app.services.prompt_import.PromptImportService`。
- 新增 `scripts/poc/import_prompts.py`，可在 macOS 本地直接执行。
- 入库规则：
  - 先通过 `PromptFileParserService` 扫描和解析 `prompts/*.md`。
  - 以 `source_file_path + source_file_hash + version` 判断幂等，已存在则 `skipped_existing`。
  - 文件 hash 变化且已有 active 默认版本时，创建 `DRAFT`，不覆盖线上 `ACTIVE` 默认版本。
  - 解析结果 `validation_status` 和 `validation_errors_json` 原样写入，不编造 schema。
  - 支持 `dry_run=True` 只输出计划，不写数据库。
- 脚本参数：
  - `--prompt-dir`
  - `--provider`
  - `--model`
  - `--batch-id`
  - `--dry-run`
- 脚本输出中文标题 `迁移报告` 和 JSON 明细。
- 本 Story 未实现 Prompt 编辑、发布、回滚 API；这些属于后续 Story。

### 真实 PostgreSQL / 脚本验证

真实数据库：

```text
postgresql+asyncpg://postgres:***@8.129.17.71:5432/xagent
```

dry-run 验证：

```bash
/opt/miniconda3/envs/booking-room/bin/python scripts/poc/import_prompts.py --dry-run --batch-id phase5-story-p5-e2-s2-verify
```

结果：脚本输出 `迁移报告`，扫描 2 个真实 Prompt 文件。由于当前真实库中已有同 `source_file_path + source_file_hash + version` 的记录，报告为 `skipped_existing`，未写入数据。

临时 Prompt 真实写库与幂等验证：

```bash
/opt/miniconda3/envs/booking-room/bin/python scripts/poc/import_prompts.py --prompt-dir "$tmpdir/prompts" --batch-id phase5-story-p5-e2-s2-script-verify
/opt/miniconda3/envs/booking-room/bin/python scripts/poc/import_prompts.py --prompt-dir "$tmpdir/prompts" --batch-id phase5-story-p5-e2-s2-script-verify
```

结果：

```text
第一次：created_count = 2, skipped_count = 0
第二次：created_count = 0, skipped_count = 2
```

验证后清理：

```text
cleaned=2
leftover_test_prompt_rows=0
```

说明：为避免污染真实库和既有 API 测试假设，测试用例和脚本真实写库验证均使用独立 `migration_batch_id`，验证后清理测试批次数据。

## 两轮独立评审记录

### 第一轮评审：需求覆盖、幂等性、真实库验证和回归范围

结论：

- 通过。当前实现只覆盖 P5-E2-S2，未实现 Prompt 编辑、发布、回滚或后台页面。
- 通过。同一 `source_file_path + source_file_hash + version` 不重复写入。
- 通过。文件 hash 变化且已有 active 默认版本时创建草稿，并通过 `parent_template_id` 关联线上版本，不覆盖 active 默认版本。
- 通过。脚本可在 macOS 本地通过 Python 直接执行，并输出中文 `迁移报告`。
- 通过。真实 PostgreSQL 上验证了 dry-run、真实写入和二次幂等跳过。

发现项：

- 初版测试使用真实 `prompts/lead-extraction.md` 写入真实库，污染了既有 Prompt API 测试的假设。
- `prompts/lead-extraction.md` 和 `prompts/lead-grading.md` 当前未内嵌 JSON schema，因此导入时会保留 `validation_failed`。
- 新增测试文件位于 `apps/api/tests/`，仓库 `.gitignore` 会忽略 `tests/`，提交时需要使用 `git add -f` 纳入。

修正结果：

- 将会写库的测试改为使用 `tmp_path` 临时 Prompt 文件。
- 为每个测试 batch 增加 finally 清理，并清理真实库残留 `phase5-test-*` 数据。
- 保留 `validation_failed`，不编造 schema，后续 schema 补齐交给 Prompt 校验/治理 Story。

### 第二轮评审：架构边界、风控和可执行性

结论：

- 通过。`apps/api` 仍是业务数据权威，脚本复用 `PromptImportService` 写入 `llm_prompt_templates`。
- 通过。本 Story 未新增任何 LLM 调用、自动触达、自动发送或社交平台动作。
- 通过。`apps/agents` 未直接写业务 core 表。
- 通过。脚本只导入本地 Prompt 基线文件，文件本身继续保留为基线来源。
- 通过。Prompt 相关测试 `26 passed`，未发现新增阻塞回归。

发现项：

- 未发现新增实质阻塞问题。

修正结果：

- 无需修正。
