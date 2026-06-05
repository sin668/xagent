# Story P5-E3-S5：知识库质量使用记录 API

状态：已完成
Sprint：Sprint 3  
优先级：P1  
Epic：P5-E3（Q&A/邮件回复知识库）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望记录知识召回、采纳、编辑幅度、发送结果和建议下线标记，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 记录知识召回、采纳、编辑幅度、发送结果和建议下线标记。

**建议文件：**

- apps/api/app/routers/*knowledge*
- apps/api/app/services/*knowledge*
- apps/api/tests/*quality*

**验收标准：**

- 邮件回复草稿可写入知识使用记录。
- 支持后台查询单条知识的使用效果。
- 质量记录不影响在线召回性能。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E3-S5：知识库质量使用记录 API。
目标：记录知识召回、采纳、编辑幅度、发送结果和建议下线标记。
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

- 新增 `apps/api/tests/test_phase5_knowledge_quality_usage_api.py`。
- 覆盖真实 PostgreSQL 下的知识使用记录写入和单条知识质量汇总：
  - 邮件回复草稿可写入 `knowledge_usage_records`。
  - 自动补齐 `knowledge_version`。
  - 记录召回查询、相似度、排序、过滤条件、采纳、编辑幅度、退信、客户回复和建议下线标记。
  - 后台可查询单条知识的使用效果汇总。
  - 未知 `email_reply_draft_id` 返回明确 404。
- 首次运行：`/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_knowledge_quality_usage_api.py -q`
- 红灯结果：2 个失败。
  - `/knowledge/items/{item_id}/usage-records` 返回 404。
  - `/knowledge/items/{item_id}/quality-summary` 返回 404。

### 实现摘要

- 新增 schema：
  - `KnowledgeUsageRecordCreate`
  - `KnowledgeUsageRecordResponse`
  - `KnowledgeQualitySummaryResponse`
- 在 `KnowledgeService` 中新增：
  - `create_usage_record`：写入知识使用记录，校验知识条目和邮件回复草稿存在。
  - `quality_summary`：按单条知识实时汇总使用效果。
  - `_rate`：计算采纳率、退信率和客户回复率。
- 新增 API：
  - `POST /knowledge/items/{item_id}/usage-records`
  - `GET /knowledge/items/{item_id}/quality-summary`
- 质量汇总包含：
  - `retrieval_count`
  - `adoption_count`
  - `adoption_rate`
  - `average_edit_distance_ratio`
  - `bounce_count`
  - `bounce_rate`
  - `customer_reply_count`
  - `customer_reply_rate`
  - `suggest_deprecate`
  - `suggest_deprecate_reason`

### 真实 PostgreSQL / API 验证

- 当前 Story 单测：
  - `/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_knowledge_quality_usage_api.py -q`
  - 结果：`2 passed, 12 warnings`。
- 已知 warning：
  - 知识库服务和部分模型仍使用 `datetime.utcnow()`，触发 Python 3.12 deprecation warning，非本 Story 行为阻塞。

## 两轮独立多维度评审

### 第一轮评审：数据写入、邮件草稿关联和汇总口径

- 结论：P5-E3-S5 已提供知识使用记录写入 API，并支持后台查询单条知识使用效果。
- 发现项 1：如果允许任意 `email_reply_draft_id` 写入，会造成知识使用记录与邮件回复草稿断链。
- 修正结果 1：`create_usage_record` 在写入前校验 `EmailReplyDraft` 存在，不存在返回 `email reply draft 不存在。`。
- 发现项 2：调用方不应自行传入 `knowledge_version`，否则会造成记录版本与知识条目版本不一致。
- 修正结果 2：服务层根据当前 `KnowledgeItem.version` 自动写入 `knowledge_version`。
- 发现项 3：后台需要直接看到采纳、退信、客户回复和建议下线汇总，而不是只拿原始列表自行计算。
- 修正结果 3：新增 `/quality-summary` 聚合返回关键质量指标。

### 第二轮评审：性能边界、范围控制和后续扩展

- 结论：第二轮未发现新增实质阻塞问题；当前实现只覆盖 P5-E3-S5，没有执行 P5-E4 的异步 embedding/指标 worker，也没有改动 EMAIL_REPLY Agent。
- 发现项 1：质量记录不应影响在线召回性能。
- 修正结果 1：写入使用记录和查询质量汇总独立于 `/knowledge/retrieval-filter` 和 `/knowledge/search`，不会改变召回路径。
- 发现项 2：P5-E3-S5 只需支持单条知识使用效果查询，不应提前实现全局指标看板。
- 修正结果 2：仅新增单条知识的 `quality-summary`，全局 Prompt/知识/embedding 指标留给 P5-E9。
- 发现项 3：真实 PostgreSQL 测试需要清理知识、邮件线程、邮件消息和回复草稿，避免污染后续 Story。
- 修正结果 3：测试 fixture 按 marker 清理知识集合和邮件线程，依赖 cascade 清理关联消息、草稿和使用记录。
