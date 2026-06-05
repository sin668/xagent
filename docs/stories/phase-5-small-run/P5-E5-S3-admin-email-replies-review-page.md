# Story P5-E5-S3：apps/admin 邮件回复审核台页面

状态：已完成
Sprint：Sprint 5  
优先级：P0  
Epic：P5-E5（apps/admin 后台管理页面）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望根据原型实现邮件回复审核台，展示待回复邮件、AI 草稿、知识命中、硬拦截和人工确认动作，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 根据原型实现邮件回复审核台，展示待回复邮件、AI 草稿、知识命中、硬拦截和人工确认动作。

**建议文件：**

- apps/admin/src/**/*email*
- prototypes/mvp-mobile-agent/pages/admin-email-replies.html

**验收标准：**

- 可查看客户上下文、来信、最近触达历史和 AI 建议。
- 可编辑最终正文、确认发送、标记已发送、拒绝、阻断或转合规。
- 发送前必须调用后端检查，不由前端直接判断。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E5-S3：apps/admin 邮件回复审核台页面。
目标：根据原型实现邮件回复审核台，展示待回复邮件、AI 草稿、知识命中、硬拦截和人工确认动作。
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

- 新增 `apps/admin/tests/emailReplyReview.test.mjs`，覆盖邮件回复审核台视图、审核队列筛选、真实 API 拉取、编辑最终正文、发送前检查和人工动作入口。
- 红灯命令：`export PATH=/Users/linhuanbin/.reflex/.nvm/versions/node/v22.22.0/bin:$PATH && node --test apps/admin/tests/emailReplyReview.test.mjs`
- 红灯结果：失败，原因是 `apps/admin/src/services/emailReplyReview.js` 不存在，测试正确捕获本 Story 缺失的服务层契约。

### 绿灯实现

- 新增 `apps/admin/src/services/emailReplyReview.js`：
  - `buildEmailReplyReviewView` 汇总待回复邮件、自动发送候选、人工确认、硬拦截，并规范化客户上下文、来信、AI 建议、最终正文、知识命中和风险判断。
  - `buildEmailReplyDraftsQuery` 映射审核台筛选到 `/email-reply/drafts` 查询参数。
  - `fetchEmailReplyReview` 接入真实 `/email-reply/drafts` API。
  - `updateEmailReplyFinalBody`、`requestEmailSendCheck`、`triggerEmailReplyReviewAction` 分别接入编辑最终正文、后端发送前检查、确认发送/标记已发送/拒绝/阻断/转合规。
  - 人工发送动作请求体显式携带 `send_check_required: true`，避免前端自行判断发送准入。
- 更新 `apps/admin/src/App.vue`：
  - 新增侧边栏 `邮件审核` 入口。
  - 新增邮件自动回复审核台页面，展示待审核队列、当前回复草稿、客户上下文、来信、AI 建议、知识命中、硬拦截和人工动作入口。
  - 页面使用真实 API 结果构建视图，不使用 seed 静态数据。
- 更新 `apps/admin/src/styles/admin.css` 与 `apps/admin/package.json`：
  - 新增邮件审核台布局、草稿编辑预览、知识/风险卡片和动作入口样式。
  - 将 `emailReplyReview.js` 加入 `check:syntax`。

## 验证记录

- `export PATH=/Users/linhuanbin/.reflex/.nvm/versions/node/v22.22.0/bin:$PATH && node --test apps/admin/tests/emailReplyReview.test.mjs`：通过，5 个测试全部通过。
- `export PATH=/Users/linhuanbin/.reflex/.nvm/versions/node/v22.22.0/bin:$PATH && npm --prefix apps/admin test`：通过，37 个测试全部通过。
- `export PATH=/Users/linhuanbin/.reflex/.nvm/versions/node/v22.22.0/bin:$PATH && npm --prefix apps/admin run check:syntax`：通过。
- `export PATH=/Users/linhuanbin/.reflex/.nvm/versions/node/v22.22.0/bin:$PATH && npm --prefix apps/admin run build`：通过。

## 第一轮独立多维度评审

### 结论

通过。当前实现满足本 Story 的核心验收标准：后台邮件回复审核台可查看客户上下文、来信、最近触达历史、AI 建议、知识命中和硬拦截，并提供编辑最终正文、确认发送、标记已发送、拒绝、阻断和转合规入口。

### 发现项

- 产品维度：审核台以风险优先队列和当前草稿详情为主，符合原型对“待人工确认列表 + 草稿审核”的结构要求。
- 技术维度：服务层接入 `/email-reply/drafts` 与 `/internal/email-reply/auto-send-check` 等真实 API 路径，未使用 seed 静态数据。
- 风控维度：发送前检查由后端 API 执行，人工发送动作显式携带 `send_check_required: true`，前端不自行判断自动发送准入。
- 测试维度：测试覆盖普通审核角色、只读角色、筛选 URL、最终正文编辑、发送前检查和人工动作请求体。

### 修正结果

- 发现项：硬拦截统计最初把“含硬拦截原因但 route 为人工确认”的草稿也计入硬拦截，口径偏宽。
- 修正结果：硬拦截统计改为只统计后端 `route = block` 的草稿，人工确认草稿仍在风险原因中展示硬拦截原因。

## 第二轮独立多维度评审

### 结论

通过。独立复核后未发现新增实质阻塞问题，可以收口本 Story。

### 发现项

- 数据一致性维度：页面字段均来自邮件回复草稿 API；缺失字段显示 `Unknown`、空正文或空列表，不编造客户信息和邮件内容。
- 权限维度：`viewer` 角色只读，编辑、发送、阻断和转合规入口禁用；运营/客服/销售/合规角色按审核台入口展示。
- 审计维度：AI 建议回复和最终发送正文分开展示，符合第五阶段“AI 建议和最终发送内容必须分开保存并可审计”的规则。
- 构建维度：admin 单测、语法检查和生产构建均已通过。

### 修正结果

第二轮未发现新增实质阻塞问题，无需修正。
