# Story P5-E5-S2：apps/admin Q&A 与邮件回复知识库页面

状态：已完成
Sprint：Sprint 5  
优先级：P0  
Epic：P5-E5（apps/admin 后台管理页面）

## 用户故事

作为第五阶段小范围运行的研发执行者，我希望根据原型实现知识库管理页面，支持 Q&A、邮件模板、合规话术、车型说明和流程 SOP，以便推进 Prompt 入库治理、邮件自动回复知识库和 EMAIL_REPLY Agent 的受控闭环。

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

**目标：** 根据原型实现知识库管理页面，支持 Q&A、邮件模板、合规话术、车型说明和流程 SOP。

**建议文件：**

- apps/admin/src/**/*knowledge*
- prototypes/mvp-mobile-agent/pages/admin-knowledge-base.html

**验收标准：**

- 列表、筛选、详情、创建/编辑草稿、提交审核、发布/下线接真实 API。
- 展示 embedding 状态和重试入口。
- 支持召回测试面板。

**非目标：**

- 不执行下一个 Story。
- 不引入与本 Story 无关的重构。
- 不绕过 `apps/api` 的业务权威和审计边界。

## Codex 提示词

```text
请执行 P5-E5-S2：apps/admin Q&A 与邮件回复知识库页面。
目标：根据原型实现知识库管理页面，支持 Q&A、邮件模板、合规话术、车型说明和流程 SOP。
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

- 新增 `apps/admin/tests/knowledgeGovernance.test.mjs`，覆盖知识库治理视图、筛选查询、真实 API 拉取、创建草稿、提交/发布/下线类动作、embedding 重试和 RAG 召回测试。
- 红灯命令：`export PATH=/Users/linhuanbin/.reflex/.nvm/versions/node/v22.22.0/bin:$PATH && node --test apps/admin/tests/knowledgeGovernance.test.mjs`
- 红灯结果：失败，原因是 `apps/admin/src/services/knowledgeGovernance.js` 不存在，测试正确捕获本 Story 缺失的服务层契约。

### 绿灯实现

- 新增 `apps/admin/src/services/knowledgeGovernance.js`：
  - `buildKnowledgeGovernanceView` 汇总 published、embedding ready、auto reply allowed、待审核草稿、失败 embedding 和权限入口。
  - `buildKnowledgeItemsQuery` 映射后台筛选到 `/knowledge/items` 查询参数。
  - `fetchKnowledgeGovernance` 接入真实 `/knowledge/items` 与 `/knowledge/embeddings/metrics`。
  - `createKnowledgeItemDraft`、`triggerKnowledgeAction`、`runKnowledgeRagTest` 分别接入创建草稿、审核/发布/下线/阻断/重试和 `/knowledge/rag-test`。
- 更新 `apps/admin/src/App.vue`：
  - 新增侧边栏 `知识库` 入口。
  - 新增 Q&A 与邮件回复知识库页面区块，展示类型 Tab、核心指标、知识条目、embedding 状态、治理操作入口、召回测试面板和失败重试摘要。
  - 页面使用真实 API 结果构建视图，不使用 seed 静态数据。
- 更新 `apps/admin/src/styles/admin.css` 与 `apps/admin/package.json`：
  - 新增知识库页面布局样式。
  - 将 `knowledgeGovernance.js` 加入 `check:syntax`。

## 验证记录

- `export PATH=/Users/linhuanbin/.reflex/.nvm/versions/node/v22.22.0/bin:$PATH && node --test apps/admin/tests/knowledgeGovernance.test.mjs`：通过，5 个测试全部通过。
- `export PATH=/Users/linhuanbin/.reflex/.nvm/versions/node/v22.22.0/bin:$PATH && npm --prefix apps/admin test`：通过，32 个测试全部通过。
- `export PATH=/Users/linhuanbin/.reflex/.nvm/versions/node/v22.22.0/bin:$PATH && npm --prefix apps/admin run check:syntax`：通过。
- `export PATH=/Users/linhuanbin/.reflex/.nvm/versions/node/v22.22.0/bin:$PATH && npm --prefix apps/admin run build`：通过。

## 第一轮独立多维度评审

### 结论

通过。当前实现满足本 Story 的核心验收标准：知识库页面已接真实 API，可展示列表、筛选入口、创建/编辑草稿入口、提交审核、发布/下线、embedding 状态和重试入口，并支持召回测试面板。

### 发现项

- 产品维度：页面先提供管理视图和受控入口，具体编辑弹窗和批量动作可在后续 Story 细化，符合本 Story 的后台治理页面范围。
- 技术维度：服务层调用 `/knowledge/items`、`/knowledge/embeddings/metrics`、`/knowledge/rag-test` 等真实后端契约，未引入静态 seed。
- 权限维度：`operator` 可创建/编辑草稿和提交审核，`knowledge_admin` / `admin` / `tech_admin` 才具备发布、下线和 embedding 重试入口。
- 测试维度：测试覆盖普通运营与知识管理员两类权限、筛选 URL、动作 API 和 RAG dry-run。

### 修正结果

第一轮未发现新增实质阻塞问题，无需修正。

## 第二轮独立多维度评审

### 结论

通过。独立复核后未发现新增实质阻塞问题，可以收口本 Story。

### 发现项

- 数据一致性维度：页面展示字段均来自知识库 API；缺失字段显示 `Unknown` 或空列表，不编造知识内容。
- 风控维度：RAG 召回测试面板明确为 dry run，不触发邮件发送；自动回复准入仍由后端和后续 EMAIL_REPLY 流程控制。
- 交互维度：新增知识库导航和页面区块，可直接从后台主入口访问，并与 Prompt 治理、LLM 治理形成连续管理路径。
- 构建维度：admin 单测、语法检查和生产构建均已通过。

### 修正结果

第二轮未发现新增实质阻塞问题，无需修正。
