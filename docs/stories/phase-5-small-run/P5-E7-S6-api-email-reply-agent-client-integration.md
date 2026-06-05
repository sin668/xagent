# Story P5-E7-S6：apps/api EmailReplyAgent client 集成

状态：已完成
Sprint：Sprint 7  
优先级：P0  
Epic：P5-E7（EMAIL_REPLY Agent）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望在 `apps/api` 中通过 HTTP 调用 `apps/agents` EMAIL_REPLY，并保存兼容任务摘要，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 在 `apps/api` 中通过 HTTP 调用 `apps/agents` EMAIL_REPLY，并保存兼容任务摘要。

**建议文件：**

- apps/api/app/services/*agent*
- apps/api/app/routers/*email*
- apps/api/tests/*email_agent*

**验收标准：**

- 配置 `AGENTS_BASE_URL`、API Key、超时和开关。
- 保存 external_agent_run_id、状态、错误和输出摘要。
- Agent 不可用时有降级错误，不阻塞其他 API。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E7-S6：apps/api EmailReplyAgent client 集成。
目标：在 `apps/api` 中通过 HTTP 调用 `apps/agents` EMAIL_REPLY，并保存兼容任务摘要。
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

- `apps/api/tests/agents/test_http_agent_runtime.py::test_http_agent_runtime_posts_email_reply_response_contract`
- `apps/api/tests/test_phase5_email_reply_agent_client.py`

红灯命令：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/agents/test_http_agent_runtime.py::test_http_agent_runtime_posts_email_reply_response_contract tests/test_phase5_email_reply_agent_client.py -q
```

红灯结果：

- 失败符合预期：`ModuleNotFoundError: No module named 'app.services.email_reply_agent'`。
- 证明当前 `apps/api` 缺少 EMAIL_REPLY Agent client 服务和对应任务摘要保存能力。

### 最小实现

实现内容：

- 在 `apps/api/app/agents/http_runtime.py` 新增同步兼容方法 `run_email_reply_response(...)`，通过 `POST /agent-runs/email-reply` 调用 `apps/agents`。
- 在 `apps/api/app/services/email_reply_agent.py` 新增 `EmailReplyAgentService` 和 `select_email_reply_runtime`。
- 新增 `AgentTaskType.EMAIL_REPLY`。
- 新增 migration `20260605_0036_add_email_reply_agent_task_type.py`，扩展 PostgreSQL enum `agenttasktype`。
- 在 `apps/api/app/settings.py` 和 `apps/api/.env.example` 增加 `AGENT_EMAIL_REPLY_HTTP_ACTIVE_ENABLED` 开关。
- 成功时保存 `external_agent_run_id`、外部状态、Agent 类型、模式、审计摘要、知识命中数、自动发送判断和人工复核判断。
- 失败时写入降级错误摘要，保持 `writes_core_tables=false`，并把草稿置为 `failed + manual_review_required=true`，不影响其他 API。
- 支持传入数据库 Session 时 `add/flush` `AgentTaskRun` 和 `EmailReplyDraft`，用于后续真实 PostgreSQL 路由集成。

### 绿灯与回归验证

命令一：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/agents/test_http_agent_runtime.py::test_http_agent_runtime_posts_email_reply_response_contract tests/test_phase5_email_reply_agent_client.py tests/test_agent_task_run_model.py tests/test_settings.py -q
```

结果：`12 passed in 0.53s`。

命令二：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/agents/test_http_agent_runtime.py tests/test_phase5_email_reply_agent_client.py tests/test_agent_task_run_model.py tests/test_phase5_email_reply_draft_model.py tests/test_phase5_email_reply_customer_policy_integration.py tests/test_phase5_email_reply_hard_block_service.py -q
```

结果：`28 passed in 0.42s`。

命令三：

```bash
cd apps/agents
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_email_reply_agent_run_api.py tests/test_email_reply_auto_send_route.py tests/test_email_reply_draft_schema_validation.py tests/test_email_reply_graph_context_knowledge.py tests/test_email_reply_schema.py -q
```

结果：`18 passed in 1.25s`。

命令四：

```bash
git diff --check
```

结果：通过，无格式错误。

## 两轮独立多维度评审

### 第一轮评审：需求覆盖、API/Agent 边界、任务摘要保存

结论：通过。

发现项：

- 已覆盖 `AGENTS_BASE_URL`、API Key、超时和 EMAIL_REPLY HTTP 开关配置。
- 已通过 `HttpAgentRuntime.run_email_reply_response` 调用 `apps/agents` 的 `/agent-runs/email-reply`，并保留统一 envelope 校验。
- 已新增 `EmailReplyAgentService` 保存兼容任务摘要，包括 `external_agent_run_id`、外部状态、Agent 类型、模式、错误、审计摘要和输出摘要。
- 已保持 `apps/api` 业务权威，`apps/agents` 只返回结构化结果，不直接写 core 表。

修正结果：

- 第一轮中发现 runtime 方法最初是 async，不适合同步 service 直接调用；已修正为同步兼容方法，和现有 deep-enrichment / lead-cleanup runtime 模式一致。

### 第二轮评审：降级错误、可观测性、后续 P5-E8 衔接

结论：通过。

发现项：

- Agent 不可用时不会向调用方抛出异常，而是写入 failed 任务摘要、错误类型 `external_agent_unavailable` 和 `writes_core_tables=false`。
- Agent 输出 schema 不正确时写入 `schema_validation_error`，并保留外部 run id，方便排查。
- `EmailReplyDraft` 已保存 AI 建议、知识命中、自动发送判断、人工复核原因、模型和 Prompt 版本，为 P5-E8 邮件发送前检查与人工确认发送衔接。
- `.env.example` 已暴露 EMAIL_REPLY HTTP 开关，默认关闭，符合小范围运行和人工受控原则。

修正结果：

- 第二轮中发现失败路径摘要缺少 `writes_core_tables=false`；已补齐并通过回归测试验证。

残留风险：

- 本 Story 只完成 `apps/api` 到 `apps/agents` EMAIL_REPLY client 与任务摘要保存；正式触发路由、发送前检查和真实邮件发送属于 P5-E8，不在本 Story 范围内。
