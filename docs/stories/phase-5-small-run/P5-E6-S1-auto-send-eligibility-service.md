# Story P5-E6-S1：自动发送准入规则服务

状态：已完成
Sprint：Sprint 6  
优先级：P0  
Epic：P5-E6（自动回复规则与审计）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望实现白名单客户、固定 FAQ、首次邮件触达和低风险场景的自动发送准入判断，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 实现白名单客户、固定 FAQ、首次邮件触达和低风险场景的自动发送准入判断。

**建议文件：**

- apps/api/app/services/*email_reply*
- apps/api/tests/*auto_send*

**验收标准：**

- 准入结果保存准入原因和规则版本。
- 不满足准入只进入人工确认，不报错中断。
- 准入服务可被 Agent 内部接口和发送 API 复用。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E6-S1：自动发送准入规则服务。
目标：实现白名单客户、固定 FAQ、首次邮件触达和低风险场景的自动发送准入判断。
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

- 新增测试文件：`apps/api/tests/test_phase5_auto_send_eligibility_service.py`。
- 红灯命令：
  - `cd apps/api && /opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_auto_send_eligibility_service.py -q`
- 红灯结果：
  - 失败原因符合预期：`ModuleNotFoundError: No module named 'app.services.email_reply_auto_send'`，说明自动发送准入服务尚未实现。
- 环境说明：
  - `conda activate booking-room` 在当前 shell 未初始化；
  - 后续使用 `/opt/miniconda3/envs/booking-room/bin/python` 显式执行，确保运行在 `booking-room` 环境。

### TDD 绿灯

- 新增服务文件：`apps/api/app/services/email_reply_auto_send.py`。
- 实现内容：
  - `AUTO_SEND_ELIGIBILITY_RULE_VERSION = "phase5-auto-send-eligibility-v1"`。
  - `EmailReplyAutoSendEligibilityInput` 输入契约。
  - `EmailReplyAutoSendEligibilityDecision` 输出契约和 `to_decision_json()`。
  - `EmailReplyAutoSendEligibilityService.evaluate(...)` 自动发送准入判断。
  - `EmailReplyAutoSendEligibilityService.apply_to_draft(...)` 将准入结果回写到 `EmailReplyDraft`。
- 绿灯命令：
  - `cd apps/api && /opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_auto_send_eligibility_service.py -q`
- 绿灯结果：
  - `4 passed in 0.29s`

### 验证记录

- 回归验证命令：
  - `cd apps/api && /opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_auto_send_eligibility_service.py tests/test_phase5_email_reply_draft_model.py tests/test_phase5_knowledge_retrieval_filter_api.py -q`
- 回归验证结果：
  - `9 passed, 34 warnings in 5.34s`
- 警告说明：
  - 警告均为既有 `datetime.utcnow()` 废弃提示，来源于知识库服务和 SQLAlchemy 默认时间字段，不属于本 Story 新增阻塞。

## 两轮独立多维度评审

### 第一轮评审：业务规则与风控边界

- 结论：
  - 通过。服务仅生成自动发送候选准入判断，不发送邮件、不调用 LLM、不新增 Agent 路由，符合本 Story 非目标。
- 发现项：
  - 已覆盖白名单客户、固定 FAQ、首次触达、低风险、知识允许自动回复、知识 embedding ready、回复语言可信七个准入条件。
  - 未满足任一条件时返回 `hold_for_manual_review`，保存原因和规则版本，不抛异常中断。
  - 中高风险、blocked、Forbidden 均进入人工确认，符合风控边界。
- 修正结果：
  - 未发现需要修正的实质阻塞问题。

### 第二轮评审：工程契约与可复用性

- 结论：
  - 通过。准入服务为纯服务层模块，可被 Agent 内部接口和发送 API 复用；草稿回写只修改准入字段，不改变草稿生命周期状态。
- 发现项：
  - `auto_send_decision_json` 包含 `rule_version`、`route`、`auto_send_allowed`、`reasons`、`manual_review_required`、`manual_review_reason`，满足审计可追踪。
  - 测试覆盖准入通过、准入失败降级人工确认、风险等级阻断、草稿回写。
  - 新增服务不触碰 PostgreSQL migration，因为相关字段已在 `email_reply_drafts` 模型和迁移中存在。
- 修正结果：
  - 测试中显式设置临时 `EmailReplyDraft.status=EmailReplyDraftStatus.DRAFTED`，避免误把 SQLAlchemy 未 flush 默认值当作服务缺陷；无新增实质阻塞问题。
