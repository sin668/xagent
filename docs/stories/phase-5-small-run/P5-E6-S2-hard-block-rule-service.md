# Story P5-E6-S2：硬拦截规则服务

状态：已完成
Sprint：Sprint 6  
优先级：P0  
Epic：P5-E6（自动回复规则与审计）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望实现投诉、DNC、价格/付款/合同/税务/法律/交付/制裁/语言/知识证据等硬拦截规则，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 实现投诉、DNC、价格/付款/合同/税务/法律/交付/制裁/语言/知识证据等硬拦截规则。

**建议文件：**

- apps/api/app/services/*risk*
- apps/api/app/services/*email_reply*
- apps/api/tests/*hard_block*

**验收标准：**

- 任一硬拦截命中必须转人工或 blocked。
- 拦截原因结构化保存。
- 硬拦截优先级高于自动发送准入。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E6-S2：硬拦截规则服务。
目标：实现投诉、DNC、价格/付款/合同/税务/法律/交付/制裁/语言/知识证据等硬拦截规则。
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

- 新增测试文件：`apps/api/tests/test_phase5_email_reply_hard_block_service.py`。
- 红灯命令：
  - `cd apps/api && /opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_reply_hard_block_service.py -q`
- 红灯结果：
  - 失败原因符合预期：`ModuleNotFoundError: No module named 'app.services.email_reply_hard_block'`，说明硬拦截规则服务尚未实现。

### TDD 绿灯

- 新增服务文件：`apps/api/app/services/email_reply_hard_block.py`。
- 实现内容：
  - `EMAIL_REPLY_HARD_BLOCK_RULE_VERSION = "phase5-email-reply-hard-block-v1"`。
  - `EmailReplyHardBlockInput` 输入契约。
  - `EmailReplyHardBlockDecision` 输出契约和 `to_decision_json()`。
  - `EmailReplyHardBlockService.evaluate(...)` 硬拦截判断。
  - `EmailReplyHardBlockService.enforce_priority(...)` 保证硬拦截优先级高于自动发送准入。
  - `EmailReplyHardBlockService.apply_to_draft(...)` 将拦截结果结构化回写到 `EmailReplyDraft`。
- 绿灯命令：
  - `cd apps/api && /opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_reply_hard_block_service.py -q`
- 绿灯结果：
  - `4 passed in 0.28s`

### 验证记录

- 回归验证命令：
  - `cd apps/api && /opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_reply_hard_block_service.py tests/test_phase5_auto_send_eligibility_service.py tests/test_phase5_email_reply_draft_model.py -q`
- 回归验证结果：
  - `11 passed in 0.45s`
- 格式验证命令：
  - `git diff --check`
- 格式验证结果：
  - 通过，无尾随空格或 patch 格式问题。

## 两轮独立多维度评审

### 第一轮评审：硬拦截业务规则与优先级

- 结论：
  - 通过。服务覆盖投诉/DNC、D/E 级、价格/付款/合同/发票/税务/法律/交付/制裁、语言不确定、缺同语言知识、缺知识证据、知识召回不足和 High/Forbidden 渠道风险。
- 发现项：
  - 任一硬拦截命中后 `auto_send_allowed` 固定为 `False`。
  - `enforce_priority(...)` 会在自动发送准入已允许的情况下仍以硬拦截结果为准，满足“硬拦截优先级高于自动发送准入”。
  - High 风险渠道进入人工复核，Forbidden、DNC、D/E、投诉和敏感主题进入 blocked。
- 修正结果：
  - 未发现需要修正的实质阻塞问题。

### 第二轮评审：工程契约、审计与边界

- 结论：
  - 通过。硬拦截服务为纯服务层模块，可被 Agent 内部接口、发送前检查 API 和发送 API 复用；不发送邮件、不调用 LLM、不新增路由。
- 发现项：
  - `auto_send_decision_json` 保存 `hard_block_rule_version`、`route`、`hard_blocked`、`block_reasons`、`manual_review_required`、`manual_review_reason`，满足结构化审计。
  - `apply_to_draft(...)` 命中 blocked 时将草稿状态置为 `BLOCKED`；仅 High 风险人工复核时置为 `PENDING_REVIEW`。
  - 新增服务不触碰 PostgreSQL migration，因为复用 `email_reply_drafts` 已有审计字段。
- 修正结果：
  - 未发现新增实质阻塞问题。
