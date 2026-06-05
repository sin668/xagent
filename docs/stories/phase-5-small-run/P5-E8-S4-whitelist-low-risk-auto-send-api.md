# Story P5-E8-S4：白名单低风险自动发送 API

状态：已完成
Sprint：Sprint 8  
优先级：P0  
Epic：P5-E8（邮件发送通道）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望实现白名单、固定 FAQ、首次触达、低风险场景的受控自动发送入口，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 实现白名单、固定 FAQ、首次触达、低风险场景的受控自动发送入口。

**建议文件：**

- apps/api/app/services/*email_reply*
- apps/api/app/routers/internal*
- apps/api/tests/*auto_send*

**验收标准：**

- 只允许后端准入和硬拦截均通过后发送。
- 自动发送必须记录规则版本、准入原因和知识证据。
- 任何不确定原因均转人工。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E8-S4：白名单低风险自动发送 API。
目标：实现白名单、固定 FAQ、首次触达、低风险场景的受控自动发送入口。
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

执行日期：2026-06-06

### TDD 红灯

新增测试：

- `apps/api/tests/test_phase5_email_auto_send_api.py`

红灯命令：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_auto_send_api.py -q
```

红灯结果：

- 两个测试失败符合预期。
- 白名单低风险自动发送路径请求 `POST /email-replies/{reply_id}/auto-send` 返回 404，而期望 200。
- 不确定或人工复核草稿路径返回 404，而期望 400。
- 证明当前尚未实现白名单低风险自动发送入口。

### 最小实现

实现内容：

- 新增 `POST /email-replies/{reply_id}/auto-send`。
- 自动发送前从真实 PostgreSQL 查询 `EmailReplyDraft` 并加载 `customer`、`message`、`thread`。
- 新增 `_assert_auto_send_eligible(...)`，强制校验：
  - `auto_send_allowed=true`
  - `manual_review_required=false`
  - route 为 `auto_send_candidate`
  - 准入原因包含白名单客户、固定 FAQ、首次触达、低风险、知识允许自动回复、embedding ready、回复语言可信。
  - 知识命中存在，且每条命中为低风险、允许自动回复、embedding ready。
- 自动发送前复用 `EmailSendPreviewService.build_preview(...)`。
- `blocked` 或 `manual_review` 均返回 400，不创建发送尝试。
- 发送通过 `EmailSender` 适配层完成。
- 成功发送后写入 `email_send_attempts`、`outreach_records`、outbound `email_messages`，并更新 `email_reply_drafts.status=sent`、`sent_record_id`、`final_subject`、`final_body`。
- 自动发送 trace 写入 `auto_send_decision_json.auto_send_trace`，包含规则原因和知识证据。
- 发送失败时记录失败状态、错误码和错误消息，不静默吞错。

### 绿灯与回归验证

命令一：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_auto_send_api.py -q
```

结果：`2 passed, 5 warnings in 5.09s`。

命令二：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_auto_send_api.py tests/test_phase5_email_manual_send_api.py tests/test_phase5_email_send_preview_service.py tests/test_email_replies_api.py tests/test_phase5_email_sender_adapter.py tests/test_phase5_auto_send_eligibility_service.py tests/test_phase5_email_reply_hard_block_service.py -q
```

结果：`24 passed, 13 warnings in 13.96s`。

命令三：

```bash
git diff --check
```

结果：通过，无格式错误。

已知 warning：

- SQLAlchemy `datetime.utcnow()` deprecation warning 来自既有模型默认值。
- FastAPI OpenAPI duplicate operation id warning 来自既有 `knowledge.py` 路由。
- 两项均非本 Story 新增阻塞。

## 两轮独立多维度评审

### 第一轮评审：准入覆盖、真实 API/数据库、TDD

结论：通过。

发现项：

- 已覆盖“只允许后端准入和硬拦截均通过后发送”：自动发送前同时检查准入证据、知识证据和 P5-E8-S2 预览结果。
- 已覆盖“自动发送必须记录规则版本、准入原因和知识证据”：`auto_send_decision_json.auto_send_trace` 记录 `eligibility_reasons` 和 `knowledge_evidence`。
- 已覆盖“任何不确定原因均转人工”：准入证据缺失、知识未 ready、非低风险、manual_review 或 blocked 均返回 400，不创建发送尝试。
- 测试使用真实 PostgreSQL seed `Customer`、`EmailThread`、`EmailMessage`、`EmailReplyDraft` 并查询 `EmailSendAttempt` 验证落库。

修正结果：

- 初始红灯显示自动发送路由不存在；已补齐入口和受控发送链路并完成绿灯验证。

### 第二轮评审：架构边界、合规风控、后续衔接

结论：通过。

发现项：

- 自动发送仍由 `apps/api` 控制，`apps/agents` 不直接写业务 core 表。
- 发送通过 `EmailSender` 适配层完成，未绕过 P5-E8-S1/P5-E8-S3 的发送链路。
- 自动发送入口没有进入 P5-E8-S5 的失败重试和退信处理范围。
- DNC/D/E、hard block、知识不足和频控继续由 P5-E8-S2 预览检查拦截。

修正结果：

- 未发现新增实质阻塞问题，无需继续修正。

残留风险：

- 当前自动发送准入依赖草稿中的 `auto_send_decision_json` 和 `knowledge_hits_json` 证据；后续如由 Agent 直接触发，应继续确保 Agent 不能绕过 `apps/api` 的检查入口。
- 失败重试、退信和触达历史联动留给 P5-E8-S5 完成。
