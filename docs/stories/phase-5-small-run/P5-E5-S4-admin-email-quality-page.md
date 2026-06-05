# Story P5-E5-S4：apps/admin 邮件质量指标页面

状态：已完成
Sprint：Sprint 5
优先级：P1
Epic：P5-E5（apps/admin 后台管理页面）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望根据原型实现第五阶段质量指标页面，展示 Prompt、embedding、Agent、风险和业务指标，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 根据原型实现第五阶段质量指标页面，展示 Prompt、embedding、Agent、风险和业务指标。

**建议文件：**

- apps/admin/src/**/*quality*
- apps/admin/src/**/*dashboard*
- prototypes/mvp-mobile-agent/pages/admin-email-quality.html

**验收标准：**

- 展示 Prompt 覆盖率、embedding ready、AI 生成成功率、人工采纳率、自动发送成功率、退信率。
- 展示 DNC/D/E 阻断和风险事件。
- 指标来自真实 API。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E5-S4：apps/admin 邮件质量指标页面。
目标：根据原型实现第五阶段质量指标页面，展示 Prompt、embedding、Agent、风险和业务指标。
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

## TDD 执行记录

### 红灯

- 新增测试：`apps/admin/tests/emailQualityDashboard.test.mjs`。
- 红灯命令：`npm --prefix apps/admin test`。
- 红灯结果：测试首次运行失败，原因是 `apps/admin/src/services/emailQualityDashboard.js` 模块不存在，证明测试覆盖的是本 Story 新增能力。

### 绿灯

- 新增 `apps/admin/src/services/emailQualityDashboard.js`，聚合真实 API 返回的 Prompt、embedding、AI 审计、邮件草稿和风险事件数据。
- 更新 `apps/admin/src/App.vue`，新增「质量指标」导航和第五阶段 Go/No-Go 质量看板。
- 更新 `apps/admin/src/styles/admin.css`，补齐质量指标卡片、硬风险门禁、业务指标和流程节点样式。
- 更新 `apps/admin/package.json`，将 `emailQualityDashboard.js` 纳入语法检查。

## 验收记录

- `npm --prefix apps/admin test`：40 项测试通过。
- `npm --prefix apps/admin run check:syntax`：通过。
- `npm --prefix apps/admin run build`：通过。

## 两轮独立多维度评审

### 第一轮评审

- 结论：功能范围符合 P5-E5-S4，页面已展示 Prompt 覆盖率、embedding ready、AI 生成成功率、人工采纳率、自动发送成功率、退信率、DNC/D/E 阻断和风险事件。
- 发现项：人工采纳率和发送成功率不能只依赖草稿 `status` 字段，否则会把 `status=sent` 但 `send_attempts=bounced` 的草稿误判为成功。
- 修正结果：服务层按真实 `send_attempts` 计算发送成功、退信和人工采纳率；测试用例覆盖了「草稿状态为 sent 但发送尝试退信」场景，当前口径保持正确。

### 第二轮评审

- 结论：以真实 API 契约为边界，`fetchEmailQualityDashboard` 调用 `/llm-prompt-templates`、`/knowledge/embeddings/metrics`、`/sync/audit-dashboard`、`/email-reply/drafts?limit=500`、`/dashboard/risk-events`，未引入 seed 静态验收。
- 发现项：硬风险门禁需要优先于普通质量不足；存在未关闭风险事件时应直接显示「暂停」，而不是仅显示「重跑 PoC」。
- 修正结果：Go/No-Go 逻辑已将未关闭风险事件作为硬门禁；有风险事件时显示「暂停」，无硬风险但质量不足时显示「重跑 PoC」，两轮复核未发现新的实质阻塞问题。
