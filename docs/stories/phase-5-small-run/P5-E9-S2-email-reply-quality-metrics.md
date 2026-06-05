# Story P5-E9-S2：邮件回复采纳率、编辑幅度与退信率指标

状态：已完成
Sprint：Sprint 9  
优先级：P1  
Epic：P5-E9（质量指标与端到端验收）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望实现 AI 回复生成成功率、人工采纳率、编辑幅度、自动发送成功率、退信率和客户回复率统计，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 实现 AI 回复生成成功率、人工采纳率、编辑幅度、自动发送成功率、退信率和客户回复率统计。

**建议文件：**

- apps/api/app/services/*metrics*
- apps/api/app/routers/*metrics*
- apps/api/tests/*email_metrics*

**验收标准：**

- 人工采纳率和编辑幅度基于 AI 建议与 final 内容比较。
- 退信率和发送失败率来自 email_send_attempts。
- 指标支持按时间、语言、场景过滤。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E9-S2：邮件回复采纳率、编辑幅度与退信率指标。
目标：实现 AI 回复生成成功率、人工采纳率、编辑幅度、自动发送成功率、退信率和客户回复率统计。
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

执行日期：2026-06-06
执行方式：按 `superpowers:test-driven-development`、`superpowers:systematic-debugging` 和 `superpowers:verification-before-completion` 推进。

### TDD 红灯

- 新增 `apps/api/tests/test_phase5_email_reply_quality_metrics_api.py`，构造真实 PostgreSQL 数据：`email_reply_drafts`、`email_send_attempts`、`email_threads`、`email_messages` 和 `outreach_records`。
- 红灯命令：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_reply_quality_metrics_api.py -q
```

- 红灯结果：`1 failed`，失败原因是 `/dashboard/email-reply-quality` 返回 `404 Not Found`，证明指标 API 尚未实现。

### 实现内容

- 新增 `GET /dashboard/email-reply-quality`，支持 `date_from`、`date_to`、`language`、`business_scene` 过滤。
- 新增 `EmailReplyQualityResponse` 和 `EmailReplyQualityFilters` schema。
- 在 `DashboardService.email_reply_quality_metrics()` 中统计：
  - AI 生成成功数、失败数和成功率。
  - 人工复核数、人工采纳数和人工采纳率。
  - 平均编辑幅度，基于 AI 建议正文与 final 正文相似度计算。
  - 自动发送候选数、自动发送成功数和成功率。
  - 发送尝试数、成功、失败、退信、发送失败率和退信率。
  - 客户回复数和客户回复率。
- 管理后台邮件质量页服务 `apps/admin/src/services/emailQualityDashboard.js` 已优先读取 `/dashboard/email-reply-quality` 的后端权威指标，旧草稿聚合仅作为本地兜底与 DNC/D/E 阻断展示来源。

### 调试归因

- 首轮绿灯测试曾失败在 `manual_adopted_count`：预期 `1`，实际 `0`。
- 根因：最初将主题行改动也纳入“未采纳”判断；测试数据中正文完全一致但主题从 `AI subject` 变为 `Final subject`。
- 修正：人工采纳率按“回复正文未编辑”判断；主题微调不视为正文未采纳。编辑幅度仍保留正文相似度口径。

### 验证结果

目标测试：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_reply_quality_metrics_api.py -q
```

结果：`1 passed`。

后端相关回归：

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_phase5_email_reply_quality_metrics_api.py tests/test_phase5_email_failure_bounce_api.py tests/test_phase5_email_manual_send_api.py tests/test_phase5_email_auto_send_api.py tests/test_phase5_email_reply_audit_service.py tests/test_phase5_prompt_knowledge_embedding_metrics_api.py -q
```

结果：`11 passed`。

后台真实指标接口接入测试：

```bash
export PATH=/Users/linhuanbin/.reflex/.nvm/versions/node/v22.22.0/bin:$PATH
npm --prefix apps/admin test -- tests/emailQualityDashboard.test.mjs
```

结果：`43 passed`。

后台语法检查：

```bash
export PATH=/Users/linhuanbin/.reflex/.nvm/versions/node/v22.22.0/bin:$PATH
npm --prefix apps/admin run check:syntax
```

结果：通过。

## 两轮独立多维度评审

### 第一轮评审

结论：通过。

发现项：

- 需求覆盖：已覆盖 AI 回复生成成功率、人工采纳率、编辑幅度、自动发送成功率、退信率、发送失败率和客户回复率。
- 数据来源：退信率和发送失败率来自 `email_send_attempts`；客户回复基于同一 `email_thread` 中发送后出现的 inbound 邮件。
- 过滤能力：API 支持时间、语言和业务场景过滤；业务场景来自草稿 `auto_send_decision_json.business_scene`。
- 架构边界：统计由 `apps/api` 提供，`apps/admin` 只读取指标，不自行写业务表。
- 测试覆盖：目标测试和相关后端回归均通过。

修正结果：

- 已修正 SQLAlchemy 预加载写法，使用 `EmailReplyDraft.thread -> EmailThread.messages`。
- 已修正人工采纳率口径，主题微调不影响正文采纳判断。

### 第二轮评审

结论：通过。

发现项：

- 回归风险：本 Story 未改动 EMAIL_REPLY Agent 流程、发送接口或自动发送准入规则。
- 可观测性：指标响应包含 filter 回显和各项分子分母，便于后台和后续 Go/No-Go 报告复用。
- 前端联调：admin 质量页服务已调用 `/dashboard/email-reply-quality`，测试明确断言请求真实指标 API。
- 文档回写：Story 已记录 TDD、调试归因、验证命令、两轮评审和残留风险。
- 未发现新增实质阻塞问题。

修正结果：

- 无需继续修正。

## 残留风险

- 当前指标 API 采用一次性读取匹配草稿再在内存中过滤，适合小范围运行；后续数据量扩大后，P5-E9-S3/P5-E9-S4 或生产化阶段应改为 SQL 聚合和分页。
- “AI 生成成功”暂以 `final_body` 存在为成功口径；若后续需要区分“AI 已生成但尚未 final”与“生成失败”，应在草稿或 Agent run 中补充更细状态。
