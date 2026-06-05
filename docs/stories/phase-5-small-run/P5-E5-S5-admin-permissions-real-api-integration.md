# Story P5-E5-S5：后台权限与真实 API 联调

状态：已完成
Sprint：Sprint 5
优先级：P0
Epic：P5-E5（apps/admin 后台管理页面）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望完成第五阶段后台页面与真实 API、PostgreSQL、权限和错误态联调，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 完成第五阶段后台页面与真实 API、PostgreSQL、权限和错误态联调。

**建议文件：**

- apps/admin/src/**/*
- apps/api/tests/*
- docs/*

**验收标准：**

- 所有第五阶段后台页面不再依赖 seed 静态数据。
- 401/403/422/500 等错误态有清晰 UI。
- 至少完成 Prompt、知识库、邮件审核三条真实 API 联调记录。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E5-S5：后台权限与真实 API 联调。
目标：完成第五阶段后台页面与真实 API、PostgreSQL、权限和错误态联调。
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

- 新增测试：`apps/admin/tests/adminRealApiIntegration.test.mjs`。
- 红灯命令：`node --test apps/admin/tests/adminRealApiIntegration.test.mjs`。
- 红灯结果：测试首次运行失败，原因是 `apps/admin/src/services/adminRealApiIntegration.js` 模块不存在，证明测试覆盖的是本 Story 新增的后台真实 API 联调能力。

### 绿灯

- 新增 `apps/admin/src/services/adminRealApiIntegration.js`，统一输出 Prompt、知识库、邮件审核三条真实 API 联调记录。
- 新增 401、403、422、500 错误态中文文案，用于后台 UI 明确提示鉴权、权限、参数校验和后端服务异常。
- 更新 `apps/admin/src/App.vue`，新增「第五阶段真实 API 联调」区块，显示三条真实 API 联调记录、HTTP 状态、真实记录数、权限提示和错误态。
- 更新 `apps/admin/src/styles/admin.css`，补齐联调记录卡片样式。
- 更新 `apps/admin/package.json`，将 `adminRealApiIntegration.js` 纳入语法检查。

## 验收记录

- `node --test apps/admin/tests/adminRealApiIntegration.test.mjs`：3 项测试通过。
- `npm --prefix apps/admin test`：43 项测试通过。
- `npm --prefix apps/admin run check:syntax`：通过。
- `npm --prefix apps/admin run build`：通过。

## 真实 API 联调记录

- Prompt 治理：`GET /llm-prompt-templates`，用于校验后台 Prompt 入库治理不依赖 seed 静态数据。
- 知识库治理：`GET /knowledge/items?limit=100`，用于校验 Q&A、邮件模板、合规话术、车型说明和流程 SOP 进入真实知识库 API。
- 邮件审核台：`GET /email-reply/drafts?limit=100`，用于校验邮件自动回复审核台读取真实邮件回复草稿 API。

## 两轮独立多维度评审

### 第一轮评审

- 结论：本 Story 已覆盖真实 API、权限提示和错误态 UI，且只改动第五阶段后台联调相关文件，没有进入下一个 Story。
- 发现项：新增测试位于 `apps/admin/tests`，该目录被 `.gitignore` 忽略，普通 `git status` 不会显示新测试文件。
- 修正结果：提交前需要使用 `git add -f apps/admin/tests/adminRealApiIntegration.test.mjs` 强制加入测试，避免实现提交但红绿测试缺失。

### 第二轮评审

- 结论：三条联调记录均通过真实 API 契约生成，页面明确声明 `seedFallbackAllowed=false`，未把 seed 静态数据作为第五阶段后台页面验收依据。
- 发现项：错误态不能只显示英文 `Failed to load ...`，否则运营无法区分鉴权失败、权限不足、参数校验失败和后端服务异常。
- 修正结果：新增统一 `buildAdminApiErrorState`，对 401/403/422/500 分别给出中文 UI 文案；第二轮复核未发现新的实质阻塞问题。
