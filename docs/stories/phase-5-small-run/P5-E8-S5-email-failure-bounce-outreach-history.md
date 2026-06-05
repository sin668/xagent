# Story P5-E8-S5：失败重试、退信记录与触达历史联动

状态：已完成
Sprint：Sprint 8  
优先级：P1  
Epic：P5-E8（邮件发送通道）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望将发送失败、重试、退信和客户回复状态写入触达历史与质量指标，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 将发送失败、重试、退信和客户回复状态写入触达历史与质量指标。

**建议文件：**

- apps/api/app/services/*email_sender*
- apps/api/app/services/*outreach*
- apps/api/tests/*bounce*

**验收标准：**

- 失败可重试且记录 attempt_count。
- 退信状态可进入客户触达历史。
- 质量指标可统计发送失败率和退信率。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E8-S5：失败重试、退信记录与触达历史联动。
目标：将发送失败、重试、退信和客户回复状态写入触达历史与质量指标。
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

## 本次执行记录（2026-06-06）

### TDD 红灯

先新增 `apps/api/tests/test_phase5_email_failure_bounce_api.py`，覆盖两个行为：

- 失败发送尝试调用 `/email-send-attempts/{attempt_id}/retry` 后进入 `retry_pending`，`attempt_count` 递增，并同步触达历史为待重试。
- 失败发送尝试调用 `/email-send-attempts/{attempt_id}/bounce` 后进入 `bounced`，同步触达历史为坏联系方式，并可由 `/dashboard/email-delivery-quality` 统计退信率。

红灯命令：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_failure_bounce_api.py -q
```

红灯结果：

- 2 个测试失败。
- 两个 POST 接口均返回 404，确认失败原因是本 Story 目标接口尚未实现。

### 最小实现

本次新增和更新：

- 新增 `apps/api/app/api/email_send_attempts.py`，提供 `/email-send-attempts/{attempt_id}/retry` 和 `/email-send-attempts/{attempt_id}/bounce`。
- 新增 `apps/api/app/schemas/email_send_attempts.py`，定义发送尝试动作请求和响应结构。
- 更新 `apps/api/app/main.py` 注册发送尝试路由。
- 更新 `apps/api/app/services/dashboard.py`，新增 `email_delivery_quality_metrics()` 统计发送总数、失败数、重试待处理数、退信数、失败率和退信率。
- 更新 `apps/api/app/api/dashboard.py` 和 `apps/api/app/schemas/dashboard.py`，新增 `/dashboard/email-delivery-quality`。

### 绿灯与回归验证

定向绿灯命令：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_failure_bounce_api.py -q
```

定向绿灯结果：

- `2 passed, 6 warnings`

邮件发送链路回归命令：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest \
  tests/test_phase5_email_failure_bounce_api.py \
  tests/test_phase5_email_auto_send_api.py \
  tests/test_phase5_email_manual_send_api.py \
  tests/test_phase5_email_send_preview_service.py \
  tests/test_email_replies_api.py \
  tests/test_phase5_email_sender_adapter.py \
  tests/test_phase5_email_send_attempt_model.py -q
```

回归结果：

- `21 passed, 19 warnings`
- warnings 为既有 `datetime.utcnow()` deprecation 与既有 OpenAPI duplicate operation id 警告，不影响本 Story 验收。

### 第一轮独立多维度评审

结论：通过。

发现项：

- TDD 顺序有效：先新增失败测试并确认接口 404，再实现接口和指标服务，最后定向测试变绿。
- retry 行为满足验收：失败或退信发送尝试可进入 `retry_pending`，`attempt_count` 递增，并清空错误与退信信息。
- bounce 行为满足验收：退信状态写入 `email_send_attempts`，并同步 `outreach_records.status = bad_contact`、退信摘要和下一步动作。
- 质量指标满足当前 Story 范围：可统计发送总数、失败数、重试待处理数、退信数、失败率和退信率。

修正结果：

- 未发现新增实质阻塞问题，无需追加修正。

### 第二轮独立多维度评审

结论：通过。

发现项：

- 本次实现没有绕过 P5-E8-S2/P5-E8-S3/P5-E8-S4 已建立的发送前检查、人工确认发送和白名单自动发送边界。
- `apps/api` 继续作为业务数据权威；本 Story 没有让 `apps/agents` 直接写业务 core 表。
- 新增接口只处理发送尝试状态联动，没有扩大到 P5-E9 的完整 Prompt、知识、embedding 或 Go/No-Go 指标收口。
- 新增测试使用真实 FastAPI app、真实数据库 session 和业务模型，不依赖 seed 静态页面。

修正结果：

- 未发现新增实质阻塞问题，当前 Story 可标记为已完成。

### 残留风险

- `/dashboard/email-delivery-quality` 是 P5-E8-S5 的轻量投递质量指标；后续 P5-E9-S2 仍需补齐邮件回复采纳率、编辑幅度、退信率等更完整质量口径。
- 当前 retry 只把发送尝试和触达历史置为待重试，实际重新发送调度由后续发送任务或人工动作承接。
