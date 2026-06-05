# Story P5-E6-S4：AI 建议与最终发送分离审计

状态：已完成
Sprint：Sprint 6  
优先级：P0  
Epic：P5-E6（自动回复规则与审计）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望保存 AI 建议、人工编辑后最终内容、编辑人、发送结果、Prompt 版本和知识命中，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 保存 AI 建议、人工编辑后最终内容、编辑人、发送结果、Prompt 版本和知识命中。

**建议文件：**

- apps/api/app/services/*email_reply*
- apps/api/app/models/*audit*
- apps/api/tests/*audit*

**验收标准：**

- AI 建议正文不可被 final 正文覆盖。
- 人工编辑差异可统计。
- 每次发送均可追溯 prompt、model、knowledge_hits 和操作人。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E6-S4：AI 建议与最终发送分离审计。
目标：保存 AI 建议、人工编辑后最终内容、编辑人、发送结果、Prompt 版本和知识命中。
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

- 新增测试文件：`apps/api/tests/test_phase5_email_reply_audit_service.py`。
- 红灯命令：
  - `cd apps/api && /opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_reply_audit_service.py -q`
- 红灯结果：
  - 失败原因符合预期：`ModuleNotFoundError: No module named 'app.services.email_reply_audit'`，说明邮件回复审计服务尚未实现。

### TDD 绿灯

- 新增服务文件：`apps/api/app/services/email_reply_audit.py`。
- 实现内容：
  - `EmailReplyAuditService.apply_human_edit(...)` 保存人工最终主题/正文、编辑人、编辑时间和编辑差异，不覆盖 AI 建议字段。
  - `EmailReplyAuditService.calculate_edit_metrics(...)` 统计主题/正文是否变化、长度差异和正文相似度。
  - `EmailReplyAuditService.build_send_trace(...)` 构建发送追踪，包含 prompt、model、knowledge hits、AI 建议、最终正文、操作人和发送尝试快照。
- 绿灯命令：
  - `cd apps/api && /opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_reply_audit_service.py -q`
- 绿灯结果：
  - `3 passed in 0.31s`

### 验证记录

- 回归验证命令：
  - `cd apps/api && /opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_reply_audit_service.py tests/test_phase5_email_reply_draft_model.py tests/test_phase5_email_send_attempt_model.py tests/test_phase5_email_reply_hard_block_service.py tests/test_phase5_auto_send_eligibility_service.py -q`
- 回归验证结果：
  - `17 passed in 0.44s`
- 格式验证命令：
  - `git diff --check`
- 格式验证结果：
  - 通过，无尾随空格或 patch 格式问题。

## 两轮独立多维度评审

### 第一轮评审：审计边界与业务完整性

- 结论：
  - 通过。AI 建议主题/正文和人工最终主题/正文分开保存，人工编辑不会覆盖 AI 原始建议。
- 发现项：
  - 审计摘要包含编辑人、编辑时间、编辑差异指标和 `ai_content_preserved`。
  - 发送追踪包含 prompt version、model、knowledge hits、AI 建议、最终正文、操作人和发送尝试快照。
  - 服务只构建审计与更新草稿字段，不发送邮件、不新增发送 API。
- 修正结果：
  - 未发现需要修正的实质阻塞问题。

### 第二轮评审：工程契约与后续复用

- 结论：
  - 通过。审计服务为纯服务层模块，可被邮件审核 API、发送前检查 API、人工确认发送 API 和 EMAIL_REPLY Agent 回写流程复用。
- 发现项：
  - `calculate_edit_metrics(...)` 对空值做归一化，避免最终正文为空时统计异常。
  - `build_send_trace(...)` 对 `EmailSendAttemptStatus` 做枚举值序列化，适合写入 JSON 审计字段。
  - 新增服务复用 `email_reply_drafts` 与 `email_send_attempts` 已有字段，不需要新增 migration。
- 修正结果：
  - 未发现新增实质阻塞问题。
