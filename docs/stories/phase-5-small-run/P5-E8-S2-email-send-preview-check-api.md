# Story P5-E8-S2：发送前检查与预览 API

状态：已完成
Sprint：Sprint 8  
优先级：P0  
Epic：P5-E8（邮件发送通道）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望提供邮件发送预览和发送前检查 API，聚合收件人、DNC、等级、准入、硬拦截、知识命中和频控，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 提供邮件发送预览和发送前检查 API，聚合收件人、DNC、等级、准入、硬拦截、知识命中和频控。

**建议文件：**

- apps/api/app/routers/*email*
- apps/api/app/services/*email_reply*
- apps/api/tests/*send_preview*

**验收标准：**

- 预览 API 不发送邮件。
- 返回可发送/需人工/阻断及原因。
- DNC/D/E、硬拦截命中时不能返回可自动发送。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E8-S2：发送前检查与预览 API。
目标：提供邮件发送预览和发送前检查 API，聚合收件人、DNC、等级、准入、硬拦截、知识命中和频控。
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

- `apps/api/tests/test_phase5_email_send_preview_service.py`
- 扩展 `apps/api/tests/test_email_replies_api.py`

红灯命令一：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_send_preview_service.py -q
```

红灯结果：

- 失败符合预期：`ModuleNotFoundError: No module named 'app.services.email_send_preview'`。
- 证明当前缺少发送前检查与预览服务。

红灯命令二：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_email_replies_api.py -q
```

红灯结果：

- OpenAPI 中缺少 `/email-replies/{reply_id}/send-preview`。
- 真实 PostgreSQL 种子草稿调用 `POST /email-replies/{reply_id}/send-preview` 返回 404。
- 证明当前缺少发送前预览 API。

### 最小实现

实现内容：

- 新增 `apps/api/app/services/email_send_preview.py`。
- 新增 `EmailSendPreviewService.build_preview(...)`，聚合收件人、发件人、主题、正文、知识命中、DNC、等级、硬拦截、自动发送准入和频控。
- 新增 `EmailSendPreviewResponse` schema。
- 新增 `POST /email-replies/{reply_id}/send-preview` 路由。
- 路由使用真实 PostgreSQL 查询 `EmailReplyDraft`，加载 `customer` 和 `message` 后生成预览。
- 非 UUID `reply_id` 返回 404，避免 422 影响前端路由兼容。
- 预览响应固定 `send_triggered=false`，不调用 `EmailSender.send(...)`，不写发送记录。

关键规则：

- DNC/勿扰客户阻断为 `blocked`，`hard_blocks` 包含 `customer_do_not_contact`。
- Watch/Invalid（对外 D/E 级）阻断为 `blocked`，`hard_blocks` 包含 `customer_de_grade`。
- `auto_send_decision_json.hard_blocked=true` 优先阻断，透出 `block_reasons[].code`。
- 无知识命中进入 `manual_review`，原因包含 `missing_knowledge_evidence`。
- 频控达到上限进入 `manual_review`，原因包含 `frequency_limit_reached`。
- `auto_send_allowed=false` 或 `manual_review_required=true` 进入 `manual_review`。

### 绿灯与回归验证

命令一：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_send_preview_service.py -q
```

结果：`4 passed in 0.28s`。

命令二：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_send_preview_service.py tests/test_email_replies_api.py -q
```

结果：`8 passed, 3 warnings in 4.17s`。

命令三：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_send_preview_service.py tests/test_email_replies_api.py tests/test_phase5_auto_send_eligibility_service.py tests/test_phase5_email_reply_hard_block_service.py tests/test_phase5_email_sender_adapter.py -q
```

结果：`20 passed, 3 warnings in 4.18s`。

已知 warning：

- FastAPI OpenAPI duplicate operation id warning 来自既有 `knowledge.py` 路由。
- SQLAlchemy `datetime.utcnow()` deprecation warning 来自既有模型默认值。
- 两项均非本 Story 新增阻塞。

## 两轮独立多维度评审

### 第一轮评审：需求覆盖、TDD、真实 API/数据库

结论：通过。

发现项：

- 已覆盖“预览 API 不发送邮件”：响应中固定 `send_triggered=false`，实现未调用 `EmailSender.send(...)`。
- 已覆盖“返回可发送/需人工/阻断及原因”：响应包含 `decision`、`allow_auto_send`、`reasons`、`hard_blocks`、`manual_review_required` 和 `manual_review_reason`。
- 已覆盖 DNC/D/E 和 hard block：DNC、Watch、Invalid、`hard_blocked=true` 均不能返回可自动发送。
- API 测试使用真实 PostgreSQL seed `Customer`、`EmailThread`、`EmailMessage`、`EmailReplyDraft`，不是 seed 静态页面。

修正结果：

- 初始服务层测试断言使用中文“下一步”，与俄文测试正文不一致；已修正为断言俄文 final body 片段，保持测试意图为“预览优先使用最终发送正文”。

### 第二轮评审：架构边界、合规风控、后续 Story 衔接

结论：通过。

发现项：

- `apps/api` 继续作为业务数据权威，发送前检查由 API 服务层完成。
- 本 Story 未让 `apps/agents` 写业务 core 表，也未让前端或 Agent 直接发送邮件。
- 本 Story 只做 P5-E8-S2，不进入 P5-E8-S3 的人工确认发送，也不进入 P5-E8-S4 的自动发送。
- 预览服务为后续人工确认发送和白名单低风险自动发送提供统一检查结果，可复用 DNC/D/E、硬拦截、知识不足和频控判断。

修正结果：

- 未发现新增实质阻塞问题，无需继续修正。

残留风险：

- 当前频控由调用方传入 `recent_send_count`，API 路由暂按默认 0 处理；真实发送频控统计留给后续 P5-E8-S3/P5-E8-S4/P5-E8-S5 结合 `email_send_attempts` 完善。
- 发送预览尚未写入审计事件；P5-E8-S2 的验收重点是预览检查不发送，发送和审计落库在后续发送 Story 中完成。
