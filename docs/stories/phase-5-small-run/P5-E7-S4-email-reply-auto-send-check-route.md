# Story P5-E7-S4：EMAIL_REPLY auto_send_check 与 route_decision 节点

状态：已完成
Sprint：Sprint 7  
优先级：P0  
Epic：P5-E7（EMAIL_REPLY Agent）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望实现 Agent 调用 `apps/api` 自动发送检查，并路由到 auto_send、hold_for_manual_review 或 block，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 实现 Agent 调用 `apps/api` 自动发送检查，并路由到 auto_send、hold_for_manual_review 或 block。

**建议文件：**

- apps/agents/app/**/*email*
- apps/agents/tests/*route*
- apps/api/app/routers/internal*

**验收标准：**

- Agent 不自行判断最终发送，只使用 `apps/api` 检查结果。
- blocked/hold/auto_send 路由均记录原因。
- dry_run 不触发真实发送。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E7-S4：EMAIL_REPLY auto_send_check 与 route_decision 节点。
目标：实现 Agent 调用 `apps/api` 自动发送检查，并路由到 auto_send、hold_for_manual_review 或 block。
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

新增 Agent 测试文件：

- `apps/agents/tests/test_email_reply_auto_send_route.py`

新增 API 契约测试：

- `apps/api/tests/test_phase5_internal_email_reply_api.py`

红灯命令：

```bash
cd apps/agents
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_email_reply_auto_send_route.py -q
```

红灯结果：

```text
3 failed
Right contains 2 more items, first extra item: 'auto_send_check'
```

红灯命令：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_internal_email_reply_api.py -q
```

红灯结果：

```text
2 failed, 3 passed
POST /internal/email-reply/auto-send-check 返回 404 Not Found
```

结论：

- Agent 图还没有 `auto_send_check` 与 `route_decision` 节点。
- `apps/api` 内部邮件回复接口还没有自动发送检查端点，因此红灯有效。

### 最小实现

实现内容：

- `apps/agents/app/adapters/email_reply_api.py` 新增 `auto_send_check`，调用 `POST /internal/email-reply/auto-send-check`。
- `apps/agents/app/graphs/email_reply.py` 将 EMAIL_REPLY 节点序列扩展为 `load_context -> retrieve_knowledge -> draft_reply -> schema_validation -> auto_send_check -> route_decision`。
- Agent 的 `auto_send_check` 节点只把已校验输出、上下文、知识命中、options、dry_run 发送给 `apps/api`，不自行做最终发送判断。
- Agent 的 `route_decision` 节点只使用 `apps/api` 返回的决策，支持 `auto_send`、`hold_for_manual_review`、`block` 三条路由，并把原因、block_reasons、dry_run、send_triggered 写入 audit。
- `apps/api/app/api/internal_email_reply.py` 新增 `/internal/email-reply/auto-send-check`，复用 `EmailReplyHardBlockService` 与 `EmailReplyAutoSendEligibilityService` 生成后端权威决策。
- 端点强制校验 `X-Agents-Api-Key`，`dry_run=true` 时只返回决策，不触发真实发送。
- 更新 P5-E7-S2/P5-E7-S3 旧测试替身，使其支持新增 API client 方法并同步完整节点序列。

### 绿灯与回归验证

Agent Story 测试：

```bash
cd apps/agents
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_email_reply_auto_send_route.py -q
```

结果：

```text
3 passed in 0.22s
```

API 内部端点测试：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_internal_email_reply_api.py -q
```

结果：

```text
5 passed, 6 warnings in 4.87s
```

P5-E7 Agent 回归：

```bash
cd apps/agents
/opt/miniconda3/envs/booking-room/bin/python -m pytest \
  tests/test_email_reply_auto_send_route.py \
  tests/test_email_reply_draft_schema_validation.py \
  tests/test_email_reply_graph_context_knowledge.py \
  tests/test_email_reply_schema.py -q
```

结果：

```text
14 passed in 0.25s
```

API 规则与内部接口回归：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest \
  tests/test_phase5_internal_email_reply_api.py \
  tests/test_phase5_auto_send_eligibility_service.py \
  tests/test_phase5_email_reply_hard_block_service.py -q
```

结果：

```text
13 passed, 6 warnings in 4.75s
```

格式检查：

```bash
git diff --check
```

结果：

```text
通过，无输出。
```

说明：

- API 测试中的 `datetime.utcnow()` DeprecationWarning 为既有警告，不属于本 Story 新增阻塞。

## 两轮独立多维度评审

### 第一轮评审：需求覆盖、架构边界与测试

结论：通过。

发现项：

- 已覆盖本 Story 三项验收：Agent 不自行判断最终发送；`auto_send`、`hold_for_manual_review`、`block` 均记录原因；`dry_run` 不触发真实发送。
- `apps/agents` 只调用 `apps/api` 内部接口并根据返回决策路由，没有直接写业务 core 表，也没有调用邮件发送服务商。
- `apps/api` 内部端点复用既有自动发送准入与硬拦截规则，保持后端业务权威。
- Agent 与 API 均有红绿灯测试，旧 P5-E7 回归测试已同步新增节点序列。

修正结果：

- 第一轮发现旧测试替身缺少 `auto_send_check` 方法，导致 P5-E7 回归失败；已为旧 Fake API client 补默认人工确认决策，并更新节点断言。

### 第二轮评审：风险、可观测性与后续衔接

结论：通过。

发现项：

- `route_decision`、`route_reasons`、`manual_review_reason`、`block_reasons`、`dry_run`、`send_triggered` 均写入 audit，可供后续 HTTP API、后台审核台和指标服务追踪。
- `dry_run` 默认 true，当前 Story 不触发真实发送，符合“发送通道在 P5-E8 实现”的阶段边界。
- DNC/D/E、敏感主题、语言不确定、缺少知识证据、知识召回不足和高风险渠道仍由 `apps/api` 硬拦截规则处理。
- 当前 Story 未提前实现 `/agent-runs/email-reply` HTTP API 或 `apps/api` Agent client 集成，保持 P5-E7-S5/P5-E7-S6 边界。

修正结果：

- 未发现新增实质阻塞问题，无需继续修正。
