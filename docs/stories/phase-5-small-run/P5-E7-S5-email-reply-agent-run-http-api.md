# Story P5-E7-S5：新增 `/agent-runs/email-reply` HTTP API

状态：已完成
Sprint：Sprint 7  
优先级：P0  
Epic：P5-E7（EMAIL_REPLY Agent）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望在 `apps/agents` 新增 EMAIL_REPLY Agent Run API，沿用第四阶段鉴权、run 状态和节点 trace，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 在 `apps/agents` 新增 EMAIL_REPLY Agent Run API，沿用第四阶段鉴权、run 状态和节点 trace。

**建议文件：**

- apps/agents/app/main.py
- apps/agents/app/routers/*
- apps/agents/tests/*email_reply_api*

**验收标准：**

- POST `/agent-runs/email-reply` 可创建 run。
- GET `/agent-runs/{id}` 可查询结果。
- 受内部 API Key 保护，`/health` 仍公开。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E7-S5：新增 `/agent-runs/email-reply` HTTP API。
目标：在 `apps/agents` 新增 EMAIL_REPLY Agent Run API，沿用第四阶段鉴权、run 状态和节点 trace。
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

新增测试文件：

- `apps/agents/tests/test_email_reply_agent_run_api.py`

红灯命令：

```bash
cd apps/agents
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_email_reply_agent_run_api.py -q
```

红灯结果：

```text
4 errors
AttributeError: 'module' object at app.api.agent_runs has no attribute 'EmailReplyGraphRunner'
```

结论：

- 当前 `apps/agents/app/api/agent_runs.py` 尚未接入 `EmailReplyGraphRunner`。
- `POST /agent-runs/email-reply` 和 `GET /agent-runs/{id}` 尚未实现，因此红灯有效。

### 最小实现

实现内容：

- `apps/agents/app/schemas/agent_run.py` 将 `email_reply` 纳入 `AgentType`。
- `apps/agents/app/api/agent_runs.py` 新增 `POST /agent-runs/email-reply`，复用 `AgentServiceRunService` 创建、运行、成功/失败落库和统一响应结构。
- `POST /agent-runs/email-reply` 将 HTTP input 中的 `thread_id`、`message_id`、`customer_id`、`draft_id` 转为 UUID 后传入 `EmailReplyGraphState`。
- `apps/agents/app/api/agent_runs.py` 新增 `GET /agent-runs/{run_id}`，可查询已落库 run 结果。
- `GET /agent-runs/{run_id}` 复用内部 API Key 鉴权；`/health` 仍保持公开。
- `email_reply` run 输出复用 EMAIL_REPLY graph 的结构化结果，audit 继续强制 `writes_core_tables=false`。

### 绿灯与回归验证

Story 测试：

```bash
cd apps/agents
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_email_reply_agent_run_api.py -q
```

结果：

```text
4 passed in 0.50s
```

P5-E7 Agent 回归：

```bash
cd apps/agents
/opt/miniconda3/envs/booking-room/bin/python -m pytest \
  tests/test_email_reply_agent_run_api.py \
  tests/test_email_reply_auto_send_route.py \
  tests/test_email_reply_draft_schema_validation.py \
  tests/test_email_reply_graph_context_knowledge.py \
  tests/test_email_reply_schema.py -q
```

结果：

```text
18 passed in 0.60s
```

格式检查：

```bash
git diff --check
```

结果：

```text
通过，无输出。
```

## 两轮独立多维度评审

### 第一轮评审：需求覆盖、鉴权与状态查询

结论：通过。

发现项：

- 已覆盖 `POST /agent-runs/email-reply` 创建并运行 EMAIL_REPLY run。
- 已覆盖 `GET /agent-runs/{id}` 查询 run 结果。
- 已覆盖内部 API Key 鉴权，未带 `X-Agents-Api-Key` 时返回 401。
- 已覆盖 `/health` 公开访问，不受内部 API Key 保护。
- `email_reply` run 使用既有 `AgentServiceRunService` 和 `AgentRunResponse`，没有新增一套状态模型。

修正结果：

- 第一轮发现 HTTP input 的 UUID 字符串直接传入 `EmailReplyGraphState`，已在 API 层显式转换为 UUID，保持 graph 状态类型干净。

### 第二轮评审：架构边界、审计与后续衔接

结论：通过。

发现项：

- `apps/agents` HTTP API 只执行 Agent graph 和记录 run 状态，不写 `customers`、`email_reply_drafts`、`outreach_records` 等业务 core 表。
- audit 继续保留 `writes_core_tables=false` 和完整 executed_nodes，满足节点 trace 与可观测性要求。
- `POST /agent-runs/email-reply` 仍依赖 P5-E7-S4 的 graph 调用 `apps/api` 内部自动发送检查，不在 Agent HTTP 层自行判断发送。
- 当前 Story 没有提前实现 `apps/api` 调用 agents 的 client 集成，保持 P5-E7-S6 边界。

修正结果：

- 未发现新增实质阻塞问题，无需继续修正。
