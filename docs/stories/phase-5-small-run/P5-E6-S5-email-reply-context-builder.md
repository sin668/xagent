# Story P5-E6-S5：自动回复上下文构建服务

状态：已完成
Sprint：Sprint 6  
优先级：P1  
Epic：P5-E6（自动回复规则与审计）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望为 EMAIL_REPLY Agent 构建客户、来信、最近触达、意向车型、等级、DNC、来源风险和知识命中的上下文，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 为 EMAIL_REPLY Agent 构建客户、来信、最近触达、意向车型、等级、DNC、来源风险和知识命中的上下文。

**建议文件：**

- apps/api/app/services/*email_reply*
- apps/api/app/routers/internal*
- apps/api/tests/*context*

**验收标准：**

- 最近触达历史默认取 5 条。
- 缺失字段输出 Unknown/null/空数组。
- 上下文摘要可审计，避免泄露无关敏感数据。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E6-S5：自动回复上下文构建服务。
目标：为 EMAIL_REPLY Agent 构建客户、来信、最近触达、意向车型、等级、DNC、来源风险和知识命中的上下文。
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

- 新增测试文件：`apps/api/tests/test_phase5_email_reply_context_builder.py`。
- 红灯命令：
  - `cd apps/api && /opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_reply_context_builder.py -q`
- 红灯结果：
  - 失败原因符合预期：`ModuleNotFoundError: No module named 'app.services.email_reply_context'`，说明自动回复上下文构建服务尚未实现。

### TDD 绿灯

- 新增服务文件：`apps/api/app/services/email_reply_context.py`。
- 实现内容：
  - 构建客户摘要、来信摘要、最近触达历史、意向车型、来源风险、知识命中和风险决策上下文。
  - 最近触达历史默认截取 5 条，并按 `sent_at/created_at` 倒序。
  - 缺失字符串输出 `Unknown`，缺失对象输出 `null`，缺失列表输出空数组。
  - 输出 `audit_summary`，记录包含区块、数量摘要和敏感数据策略。
- 绿灯命令：
  - `cd apps/api && /opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_reply_context_builder.py -q`
- 绿灯结果：
  - `2 passed in 0.29s`

### 验证记录

- 回归验证命令：
  - `cd apps/api && /opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_reply_context_builder.py tests/test_phase5_email_reply_audit_service.py tests/test_phase5_email_reply_customer_policy_integration.py tests/test_phase5_email_reply_hard_block_service.py tests/test_phase5_auto_send_eligibility_service.py -q`
- 回归验证结果：
  - `16 passed in 0.38s`
- 格式验证命令：
  - `git diff --check`
- 格式验证结果：
  - 通过，无尾随空格或 patch 格式问题。

## 两轮独立多维度评审

### 第一轮评审：上下文完整性与缺失值策略

- 结论：
  - 通过。上下文覆盖客户、来信、最近触达、意向车型、等级、DNC、来源风险、知识命中和风险决策。
- 发现项：
  - 最近触达历史默认只保留 5 条，避免上下文过长。
  - 字符串缺失输出 `Unknown`，对象缺失输出 `null`，列表缺失输出空数组，符合 LLM 不编造约束。
  - 最高来源风险按 `Low/Medium/High/Forbidden` 规则汇总。
- 修正结果：
  - 测试夹具修正为真实枚举 `MANUAL_CUSTOMER_REPLY`；无实质阻塞问题。

### 第二轮评审：审计与敏感数据边界

- 结论：
  - 通过。上下文服务只做必要业务摘要，不包含无关敏感数据，不直接写库、不调用 LLM、不发送邮件。
- 发现项：
  - `audit_summary` 记录 included sections、触达/意向/知识/来源数量和敏感数据策略，便于后续 Agent 运行审计。
  - 该服务可被 EMAIL_REPLY Agent、内部上下文 API 和发送前检查 API 复用。
  - 与自动发送准入、硬拦截、DNC/D/E 集成和审计服务的组合回归已通过。
- 修正结果：
  - 未发现新增实质阻塞问题。
