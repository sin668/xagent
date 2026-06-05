# Story P5-E8-S3：人工确认发送 API

状态：已完成
Sprint：Sprint 8  
优先级：P0  
Epic：P5-E8（邮件发送通道）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望实现运营/销售人工确认发送、编辑后发送和标记已发送 API，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 实现运营/销售人工确认发送、编辑后发送和标记已发送 API。

**建议文件：**

- apps/api/app/routers/*email*
- apps/api/app/services/*email_sender*
- apps/api/tests/*manual_send*

**验收标准：**

- 发送前再次执行准入和硬拦截。
- 保存 final_subject/final_body、reviewed_by、sent_at。
- 发送结果写入 email_send_attempts 和 outreach_records。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E8-S3：人工确认发送 API。
目标：实现运营/销售人工确认发送、编辑后发送和标记已发送 API。
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

### TDD 红灯

新增测试：

- `apps/api/tests/test_phase5_email_manual_send_api.py`

红灯命令：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_manual_send_api.py -q
```

红灯结果：

- 两个测试失败符合预期。
- 人工确认发送成功路径请求 `POST /email-replies/{reply_id}/confirm-send` 返回 404，而期望 200。
- hard block 草稿发送前阻断路径返回 404，而期望 400。
- 证明当前 `confirm-send` 仍为占位实现，尚未实现人工确认发送、发送前检查、发送结果落库和阻断逻辑。

### 最小实现

实现内容：

- 扩展 `EmailReplyActionRequest`，支持 `final_subject`、`final_body`。
- 更新 `POST /email-replies/{reply_id}/confirm-send`：
  - 非 UUID `reply_id` 返回 404，避免前端 slug 场景返回 422。
  - 要求 `manual_confirmed=true`。
  - 从真实 PostgreSQL 查询 `EmailReplyDraft`，并加载 `customer`、`message`、`thread`。
  - 使用 `EmailReplyAuditService.apply_human_edit(...)` 保存 `final_subject`、`final_body`、`reviewed_by`、`reviewed_at`。
  - 发送前重新调用 `EmailSendPreviewService.build_preview(...)`。
  - `blocked` 预览结果直接返回 400，禁止发送。
  - 通过统一 `EmailSender.from_settings(settings).send(...)` 发送，不直接绑定邮件服务商 SDK。
  - 成功发送后写入 `outreach_records`、`email_send_attempts`，并新增 outbound `email_messages`。
  - 成功发送后更新 `email_reply_drafts.status=sent`、`sent_record_id` 和 `manual_send_trace`。
  - 发送失败时写入失败 `email_send_attempts` 信息，并把草稿状态置为 `failed`。

### 绿灯与回归验证

命令一：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_manual_send_api.py -q
```

结果：`2 passed, 5 warnings in 6.12s`。

命令二：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_manual_send_api.py tests/test_phase5_email_send_preview_service.py tests/test_email_replies_api.py tests/test_phase5_email_sender_adapter.py tests/test_phase5_email_reply_audit_service.py tests/test_phase5_auto_send_eligibility_service.py tests/test_phase5_email_reply_hard_block_service.py -q
```

结果：`25 passed, 8 warnings in 8.83s`。

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

### 第一轮评审：需求覆盖、真实数据落库、TDD

结论：通过。

发现项：

- 已覆盖“发送前再次执行准入和硬拦截”：`confirm-send` 在发送前重新调用 P5-E8-S2 的 `EmailSendPreviewService.build_preview(...)`。
- 已覆盖“保存 final_subject/final_body、reviewed_by、sent_at”：人工确认请求保存最终主题/正文和审核人；发送时间写入 `email_send_attempts.sent_at` 与 `outreach_records.sent_at`。
- 已覆盖“发送结果写入 email_send_attempts 和 outreach_records”：测试通过真实 PostgreSQL 查询验证发送尝试、触达记录和草稿状态。
- 测试覆盖真实 API、真实 PostgreSQL seed，不依赖 seed 静态页面。

修正结果：

- 初始实现前 `confirm-send` 仅返回 404；已补齐人工确认发送闭环并通过红绿验证。

### 第二轮评审：架构边界、合规风控、后续衔接

结论：通过。

发现项：

- 发送动作只在人工确认 API 中发生，未进入 P5-E8-S4 的白名单低风险自动发送范围。
- 发送通过 `EmailSender` 适配层完成，业务代码未直接绑定 SMTP/SendGrid/Mailgun/企业邮箱 SDK。
- hard block / D/E 级客户在发送前被阻断，测试确认不产生 `email_send_attempts`。
- AI 建议回复与最终发送内容保持分离，最终内容和发送 trace 写入草稿审计字段。

修正结果：

- 未发现新增实质阻塞问题，无需继续修正。

残留风险：

- 当前失败发送路径只覆盖服务层行为，尚未新增专门的 provider 失败 API 测试；后续 P5-E8-S5 会继续扩展失败重试、退信记录与触达历史联动。
- 当前人工确认发送 API 直接在路由中组织事务逻辑，后续如发送流程继续扩展，可在 P5-E8-S5 或质量收口阶段抽取为专门 service，避免路由继续变胖。
