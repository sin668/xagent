# Story P5-E7-S3：EMAIL_REPLY draft_reply 与 schema validation 节点

状态：已完成
Sprint：Sprint 7  
优先级：P0  
Epic：P5-E7（EMAIL_REPLY Agent）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望实现 LLM 回复草稿生成和结构化 schema 校验，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 实现 LLM 回复草稿生成和结构化 schema 校验。

**建议文件：**

- apps/agents/app/**/*email*
- apps/agents/tests/*draft*

**验收标准：**

- LLM 输出缺字段时按 Unknown/null/空数组处理或失败，不编造。
- 知识命中不足时 `auto_send_allowed=false`。
- schema validation 失败写入节点 trace。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E7-S3：EMAIL_REPLY draft_reply 与 schema validation 节点。
目标：实现 LLM 回复草稿生成和结构化 schema 校验。
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

- `apps/agents/tests/test_email_reply_draft_schema_validation.py`

红灯用例：

- `test_email_reply_draft_reply_normalizes_missing_fields_without_fabrication`
- `test_email_reply_draft_reply_disables_auto_send_when_knowledge_hits_are_missing`
- `test_email_reply_schema_validation_failure_records_node_trace`

红灯结果：

```text
TypeError: EmailReplyGraphRunner.__init__() got an unexpected keyword argument 'llm_drafter'
```

结论：

- 旧实现只支持 `load_context` 与 `retrieve_knowledge`，没有 `draft_reply`、`schema_validation` 节点，也没有可注入的 LLM drafter，因此红灯有效。

### 最小实现

实现内容：

- 将 EMAIL_REPLY 节点序列扩展为 `load_context -> retrieve_knowledge -> draft_reply -> schema_validation`。
- 新增 `raw_draft`、`validated_output` 状态字段。
- 新增 `NullEmailReplyDrafter`，作为无真实 LLM 时的安全默认实现。
- `EmailReplyGraphRunner` 支持注入 `llm_drafter`，便于测试和后续接入真实 LLM。
- 新增 `draft_reply` 节点，保存 LLM 原始输出并写入节点审计。
- 新增 `schema_validation` 节点，使用 `EmailReplyAgentOutput` 校验结构化输出。
- 新增 `_normalize_draft_output`，对缺失字段输出 `Unknown`，对知识不足强制 `auto_send_allowed=false`、`manual_review_required=true`、`next_action=hold_for_manual_review`。
- schema validation 失败时写入 `runner.last_error`，包含 `error_type=schema_validation_error`、`failed_node=schema_validation` 和节点 trace。
- 更新旧回归测试，使其匹配新增完整节点序列。

### 绿灯与回归验证

Story 测试：

```bash
cd apps/agents
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_email_reply_draft_schema_validation.py -q
```

结果：

```text
3 passed in 0.34s
```

P5-E7 相关回归：

```bash
cd apps/agents
/opt/miniconda3/envs/booking-room/bin/python -m pytest \
  tests/test_email_reply_draft_schema_validation.py \
  tests/test_email_reply_graph_context_knowledge.py \
  tests/test_email_reply_schema.py -q
```

结果：

```text
10 passed in 0.37s
```

格式检查：

```bash
git diff --check -- docs/superpowers/plans/2026-06-05-海外车辆采购AI获客系统-第五阶段小范围运行Codex推进计划.md
```

结果：

```text
通过，无输出。
```

## 两轮独立多维度评审

### 第一轮评审：需求覆盖、边界与测试

结论：通过。

发现项：

- 已覆盖本 Story 三项验收：缺失字段归一为 `Unknown` 且不编造；知识命中不足时禁用自动发送；schema validation 失败写入节点 trace。
- 实现范围只在 `apps/agents` 的 EMAIL_REPLY graph 与相关测试内，没有进入 P5-E7-S4 的自动发送检查和路由节点。
- `apps/agents` 仍只做编排、LLM 草稿节点、结构化校验和 trace，不写业务 core 表。
- 回归测试确认 P5-E7-S2 的 `load_context` 与 `retrieve_knowledge` 内部 API 调用仍保留。

修正结果：

- 第一轮发现旧测试仍断言只执行两个节点，与 P5-E7-S3 新节点序列冲突；已将预期更新为四节点序列，并同步校验 audit 中的 `executed_nodes`。

### 第二轮评审：风险、可观测性与后续衔接

结论：通过。

发现项：

- 缺失字段和知识不足均会进入人工复核，不会让 LLM 草稿绕过第五阶段自动发送边界。
- `schema_validation_status`、`draft_reply_generated`、`knowledge_hit_count`、`executed_nodes` 均进入 audit，便于后续后台与指标追踪。
- schema validation 失败保留节点 trace 和错误类型，后续 P5-E7-S5 HTTP API 可据此返回可解释错误。
- 当前 Story 未接真实自动发送检查，这是 P5-E7-S4 的范围，未提前扩展。

修正结果：

- 未发现新增实质阻塞问题，无需继续修正。
