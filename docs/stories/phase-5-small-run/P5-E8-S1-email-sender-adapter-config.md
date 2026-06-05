# Story P5-E8-S1：EmailSender 适配层与配置

状态：已完成
Sprint：Sprint 8  
优先级：P0  
Epic：P5-E8（邮件发送通道）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望实现统一 `EmailSender.send(message)` 适配层，支持 SMTP/SendGrid/Mailgun/企业邮箱扩展配置，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 实现统一 `EmailSender.send(message)` 适配层，支持 SMTP/SendGrid/Mailgun/企业邮箱扩展配置。

**建议文件：**

- apps/api/app/services/*email_sender*
- apps/api/app/core/config.py
- apps/api/tests/*email_sender*

**验收标准：**

- 发送服务商配置来自 `.env`。
- 测试环境可使用 fake provider。
- 业务代码不直接绑定单一服务商 SDK。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E8-S1：EmailSender 适配层与配置。
目标：实现统一 `EmailSender.send(message)` 适配层，支持 SMTP/SendGrid/Mailgun/企业邮箱扩展配置。
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

- `apps/api/tests/test_phase5_email_sender_adapter.py`

红灯命令：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_sender_adapter.py -q
```

红灯结果：

- 失败符合预期：`ModuleNotFoundError: No module named 'app.services.email_sender'`。
- 证明当前缺少统一 `EmailSender.send(message)` 适配层和发送服务商配置。

### 最小实现

实现内容：

- 新增 `apps/api/app/services/email_sender.py`。
- 定义 `EmailMessagePayload`、`EmailSendResult`、`EmailSender`、`EmailProviderAdapter`、`FakeEmailProvider`、`SMTPEmailProvider` 和扩展 provider 占位适配器。
- 支持 `fake` provider，测试环境可稳定返回伪发送结果。
- 支持 `smtp` provider，并允许测试注入 `smtp_factory`，避免业务代码绑定具体 SDK 或真实网络。
- 预留 `sendgrid`、`mailgun`、`enterprise_mail` provider 配置入口，但第五阶段未启用具体 SDK 发送。
- 在 `apps/api/app/settings.py` 增加邮件发送配置字段。
- 在 `apps/api/.env.example` 增加邮件发送配置样例。

### 绿灯与回归验证

命令一：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_sender_adapter.py -q
```

结果：`4 passed in 0.08s`。

命令二：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_sender_adapter.py tests/test_phase5_email_send_attempt_model.py tests/test_settings.py -q
```

结果：`9 passed in 0.53s`。

命令三：

```bash
git diff --check
```

结果：通过，无格式错误。

## 两轮独立多维度评审

### 第一轮评审：需求覆盖、配置来源、业务解耦

结论：通过。

发现项：

- 已实现统一 `EmailSender.send(message)` 入口。
- 发送服务商配置已来自 `Settings` 和 `.env.example`，覆盖 provider、from email、SMTP、SendGrid、Mailgun 和企业邮箱配置。
- 测试环境可使用 `fake` provider，不需要真实邮件通道。
- SMTP 通过 `smtp_factory` 注入，业务代码不直接绑定单一服务商 SDK。

修正结果：

- 初始红灯测试把未知 provider 的错误放在 `send()` 阶段；实现复核后调整为构造阶段即失败，更符合配置错误应尽早暴露的原则。

### 第二轮评审：合规边界、后续 P5-E8 衔接、可运维性

结论：通过。

发现项：

- 本 Story 只提供发送适配层，不执行发送前检查、不写触达记录、不绕过 DNC/D/E 和硬拦截。
- `fake` provider 保证后续 P5-E8-S2/P5-E8-S3 可以先做真实 API 流程联调而不误发邮件。
- SMTP 适配层返回 `provider_message_id`、provider、状态和原始摘要，可用于后续写入 `email_send_attempts`。
- SendGrid、Mailgun、企业邮箱在本 Story 只作为扩展 provider 配置入口，避免提前引入 SDK 和外部依赖。

修正结果：

- 未发现新增实质阻塞问题，无需继续修正。

残留风险：

- 真实 SendGrid/Mailgun/企业邮箱 SDK 发送不在本 Story 范围内；后续若要启用，需要单独 Story 补充 provider 适配器和供应商契约测试。
