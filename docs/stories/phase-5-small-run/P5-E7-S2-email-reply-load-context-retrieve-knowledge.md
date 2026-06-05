# Story P5-E7-S2：EMAIL_REPLY load_context 与 retrieve_knowledge 节点

状态：已完成
Sprint：Sprint 7  
优先级：P0  
Epic：P5-E7（EMAIL_REPLY Agent）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望实现 Agent 通过 `apps/api` 内部接口加载邮件上下文和检索知识，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 实现 Agent 通过 `apps/api` 内部接口加载邮件上下文和检索知识。

**建议文件：**

- apps/agents/app/**/*email*
- apps/agents/tests/*email*
- apps/api/app/routers/internal*

**验收标准：**

- 节点只通过 HTTP 内部接口读取业务上下文。
- 知识检索传入语言、场景、内容类型和自动发送过滤条件。
- 内部接口鉴权失败时任务失败并记录原因。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E7-S2：EMAIL_REPLY load_context 与 retrieve_knowledge 节点。
目标：实现 Agent 通过 `apps/api` 内部接口加载邮件上下文和检索知识。
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

- 新增 Agent 测试文件：`apps/agents/tests/test_email_reply_graph_context_knowledge.py`。
- 新增 API 测试文件：`apps/api/tests/test_phase5_internal_email_reply_api.py`。
- 红灯命令：
  - `cd apps/agents && /opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_email_reply_graph_context_knowledge.py -q`
  - `cd apps/api && /opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_internal_email_reply_api.py -q`
- 红灯结果：
  - Agent 侧失败原因符合预期：`ModuleNotFoundError: No module named 'app.graphs.email_reply'`。
  - API 侧失败原因符合预期：`/internal/email-reply/context` 与 `/internal/email-reply/knowledge` 尚不存在，返回 `404`。

### TDD 绿灯

- 新增 Agent 文件：
  - `apps/agents/app/adapters/email_reply_api.py`
  - `apps/agents/app/graphs/email_reply.py`
- 新增 API 文件：
  - `apps/api/app/api/internal_email_reply.py`
- 更新 API 入口：
  - `apps/api/app/main.py`
- 实现内容：
  - `EmailReplyGraphRunner.load_context` 通过 `apps/api` 内部 HTTP 接口加载邮件上下文。
  - `EmailReplyGraphRunner.retrieve_knowledge` 通过 `apps/api` 内部 HTTP 接口检索知识。
  - 知识检索传入 `language`、`channel`、`content_types`、`business_scene`、`auto_send_candidate`、`market`、`tone`、`limit`。
  - API 内部接口使用 `X-Agents-Api-Key` 鉴权，鉴权失败返回 `401`。
  - Agent 侧失败时记录 `last_error`，不写业务 core 表。
- 绿灯命令：
  - `cd apps/agents && /opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_email_reply_graph_context_knowledge.py tests/test_email_reply_schema.py -q`
  - `cd apps/api && /opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_internal_email_reply_api.py tests/test_phase5_email_reply_context_builder.py tests/test_phase5_knowledge_retrieval_filter_api.py -q`
- 绿灯结果：
  - Agent：`7 passed in 0.18s`
  - API：`7 passed, 40 warnings in 7.26s`

### 验证记录

- 格式验证命令：
  - `git diff --check`
- 格式验证结果：
  - 通过，无尾随空格或 patch 格式问题。
- 警告说明：
  - API 回归警告为既有 `datetime.utcnow()` 废弃提示，来源于知识库服务和测试数据时间字段，不属于本 Story 新增阻塞。

## 两轮独立多维度评审

### 第一轮评审：Agent/API 边界与鉴权

- 结论：
  - 通过。EMAIL_REPLY Agent 节点只通过 `apps/api` 内部 HTTP 接口读取业务上下文和知识，不直接访问或写入业务 core 表。
- 发现项：
  - 上下文接口 `/internal/email-reply/context` 和知识接口 `/internal/email-reply/knowledge` 均受 `X-Agents-Api-Key` 保护。
  - Agent adapter 明确调用 internal 路径，避免误用公开知识检索接口。
  - 鉴权失败时 Agent graph 抛出错误并记录 `last_error.failed_node`，不继续执行后续节点。
- 修正结果：
  - 已将知识检索 adapter 从公开 `/knowledge/retrieval-filter` 修正为 `/internal/email-reply/knowledge`；无实质阻塞问题。

### 第二轮评审：知识过滤与审计完整性

- 结论：
  - 通过。知识检索节点传递语言、场景、内容类型和自动发送过滤条件，满足 Story 验收。
- 发现项：
  - Agent 输出使用 `email-reply-v1` schema，`audit.writes_core_tables=False`，并记录 executed nodes。
  - API 内部上下文复用 `EmailReplyContextBuilder`，包含客户、来信、最近触达、意向车型、来源风险和审计摘要。
  - API 内部知识接口复用 `KnowledgeSearchService.retrieve_for_email_reply(...)`，与后台 RAG 召回过滤口径一致。
- 修正结果：
  - 未发现新增实质阻塞问题。
