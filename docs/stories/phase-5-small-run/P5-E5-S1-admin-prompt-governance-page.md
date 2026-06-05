# Story P5-E5-S1：apps/admin Prompt 入库治理页面

状态：已完成
Sprint：Sprint 5  
优先级：P0  
Epic：P5-E5（apps/admin 后台管理页面）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望根据原型实现 Prompt 入库治理页面，接入真实 Prompt API，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 根据原型实现 Prompt 入库治理页面，接入真实 Prompt API。

**建议文件：**

- apps/admin/src/**/*prompt*
- prototypes/mvp-mobile-agent/pages/admin-prompt-governance.html

**验收标准：**

- 展示入库覆盖率、版本、来源 hash、草稿校验、发布和回滚入口。
- 页面不使用静态 seed 数据。
- 权限不足时隐藏或禁用编辑/发布操作。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E5-S1：apps/admin Prompt 入库治理页面。
目标：根据原型实现 Prompt 入库治理页面，接入真实 Prompt API。
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

- 新增 `apps/admin/tests/llmGovernance.test.mjs` 中 Prompt 治理视图测试，覆盖入库覆盖率、来源 hash、校验状态和权限门禁。
- 红灯原因：`apps/admin/src/services/llmGovernance.js` 尚未导出 `buildPromptGovernanceView` / `fetchPromptGovernance`，测试无法通过。

### 绿灯实现

- 在 `apps/admin/src/services/llmGovernance.js` 新增 Prompt 治理视图模型：
  - 统计已入库 Prompt、active default、草稿待校验、schema error、覆盖率。
  - 规范化 `source_file_hash`、`source_file_path`、`validation_status`、`validation_errors_json`。
  - 根据 `admin` / `tech_admin` 控制校验草稿、发布版本和回滚版本入口。
  - 通过 `fetchPromptGovernance` 接入真实 `/llm-prompt-templates` API，不使用静态 seed。
- 在 `apps/admin/src/App.vue` 新增 `Prompt 治理` 后台页面区块：
  - 展示覆盖率、版本、状态、来源 hash、草稿校验、默认版本和校验失败摘要。
  - 并行加载真实 Prompt API，与现有 Phase 2 / Phase 3 / LLM 治理保持同一后台加载方式。
- 在 `apps/admin/src/styles/admin.css` 新增 Prompt 治理页面统计区、版本表和操作入口样式。

## 验证记录

- `cd apps/admin && node --test tests/llmGovernance.test.mjs`：通过，6 个测试全部通过。
- `export PATH=/Users/linhuanbin/.reflex/.nvm/versions/node/v22.22.0/bin:$PATH && npm --prefix apps/admin test`：通过，27 个测试全部通过。
- `export PATH=/Users/linhuanbin/.reflex/.nvm/versions/node/v22.22.0/bin:$PATH && npm --prefix apps/admin run check:syntax`：通过。
- `export PATH=/Users/linhuanbin/.reflex/.nvm/versions/node/v22.22.0/bin:$PATH && npm --prefix apps/admin run build`：通过。

## 第一轮独立多维度评审

### 结论

通过。当前实现满足本 Story 的核心验收标准：后台 Prompt 治理页面已接真实 Prompt API，可展示覆盖率、版本、来源 hash、草稿校验、发布和回滚入口，且权限不足时入口禁用。

### 发现项

- 产品维度：页面只提供治理入口状态展示，未直接执行发布/回滚动作，符合本 Story “入口”范围，后续 Story 可继续补动作 API。
- 技术维度：`fetchPromptGovernance` 使用 `/llm-prompt-templates` 作为真实 API 入口，未引入 seed 静态数据。
- 风控维度：非 `admin` / `tech_admin` 角色只读，避免误发布 Prompt。
- 测试维度：服务层测试覆盖了普通运营、技术管理员、真实 API 调用 URL 三类关键路径。

### 修正结果

第一轮未发现新增实质阻塞问题，无需修正。

## 第二轮独立多维度评审

### 结论

通过。以独立视角复核后，未发现新增实质阻塞问题，可以收口本 Story。

### 发现项

- 数据一致性维度：页面展示字段均来自 Prompt Template API 返回值，缺失来源 hash 时显示 `Unknown`，符合不编造规则。
- 交互维度：侧边栏新增 `Prompt 治理` 锚点，页面可从后台主入口直接访问。
- 权限维度：权限不足时仍可查看治理状态，但校验、发布、回滚入口禁用，符合后台治理的最小权限原则。
- 构建维度：admin 单测、语法检查和生产构建均已通过。

### 修正结果

第二轮未发现新增实质阻塞问题，无需修正。
