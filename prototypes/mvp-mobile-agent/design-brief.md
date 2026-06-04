# 第一阶段小范围运行原型设计说明

创建日期：2026-05-29
更新日期：2026-06-02

## 0. 第二阶段原型更新说明

本次更新基于：

- `_bmad-output/brainstorming/brainstorming-session-2026-06-02-第二阶段小范围运行-LLM来源发现Agent.md`
- `docs/product/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行方案与产品技术设计.md`

第二阶段原型重点从“线索复核和小范围运行”扩展到“真实 LLM 连接、Source Discovery Agent 自动新增来源、来源候选审核、LEAD_EXTRACTION 自动消费和任务审计治理”。

## 1. 用户体验分析

第一阶段从 PoC 表格验证进入小范围运行，用户不再围绕“手工整理表格”工作，而是围绕“受控 Agent 任务、staging 复核、core 有效线索、风险闸门和团队交付”工作。

核心用户：

- 线索运营：启动渠道计划、查看 Agent 任务、复核 staging 线索、推进有效线索入 core。
- 客服：处理 B 级线索，查看证据、AI 建议和触达草稿，人工触达并记录结果。
- 出口销售：处理 C 级线索，查看客户需求、车源匹配、合规复核状态。
- 管理者：关注每日有效线索数量、渠道产出、风险事件、复核效率和团队承接。
- 合规/风控：维护渠道规则、High 只读边界、勿扰、C 级复核和 AI 审计。

核心交互逻辑：

1. 首页展示今日运行状态，突出候选、staging、core、风险事件。
2. 线索池从“全部线索列表”升级为“staging/core/需二次复核/待触达”的运营队列。
3. 线索详情必须先看到来源证据、风险等级、AI 判断和复核动作，再看到触达。
4. AI 任务中心展示受控任务链路：渠道计划、候选 URL、页面读取、LLM 抽取、分级、入库。
5. 管理后台重点服务配置与治理：渠道计划、风险规则、知识库、审计和指标。

第二阶段新增核心交互逻辑：

1. 来源候选队列成为 Source Discovery Agent 的主要操作台，运营先审核来源，再让来源进入抽取链路。
2. 来源详情页必须同时展示 URL/domain、风险等级、证据摘要、LLM 原始输出摘要和 `agent_task_runs` 审计信息。
3. 审核通过只表示允许自动抽取，不表示允许自动触达。
4. Agent 手动调用页允许运营或管理员发起 `SOURCE_DISCOVERY` 和 `LEAD_EXTRACTION`，但必须走同一套任务审计。
5. 管理后台新增 LLM Provider、Prompt/schema、任务运行、成本、失败和风险治理视图。

客户域新增核心交互逻辑：

1. 客户页面只展示从 `staging_leads` 完成补全并晋级后的 `customers`，不展示原始未完善线索。
2. 客户卡片必须同时展示客户基础信息、联系方式、来源复核状态、意向车型和下一步动作。
3. 客户详情页承接线索详情页的证据链，重点展示补全后的客户档案、联系方式、经营信号、意向车型和触达历史。
4. 跟进记录页服务客服和销售的日常工作，记录人工触达、客户反馈、下一步动作和勿扰/合规状态。
5. 客户触达仍然是人工确认模式，系统可以生成草稿和记录历史，但不得自动发送私信、邮件或社媒消息。

## 2. 产品界面规划

移动端页面：

- `mobile-home.html`：智能体首页，展示今日小范围运行状态。
- `leads.html`：线索复核池，展示 staging、core、High 二次复核和待触达。
- `lead-detail.html`：线索详情，展示证据、AI 分级、复核闸门、联系方式。
- `agent-tasks.html`：Agent 任务中心，展示受控自动发现任务链路。
- `outreach.html`：触达助手，强调人工确认、勿扰和合规检查。
- `inventory.html`：车源匹配，服务 C 级销售推进。
- `analytics.html`：移动端数据洞察，查看有效线索、渠道产出和风险。
- `settings.html`：设置与合规，展示渠道边界、模型审计和知识库状态。

管理后台页面：

- `admin-dashboard.html`：第一阶段运行总览。
- `admin-risk.html`：渠道计划、风险等级、High 只读边界和暂停机制。
- `admin-sync.html`：PostgreSQL 入库、AI 审计、pgvector 知识库和任务日志。

第二阶段新增移动端页面：

- `source-candidates.html`：来源候选队列，展示 Low/Medium/High/Forbidden 风险分布、可抽取数量、High 待审数量和候选来源卡片。
- `source-detail.html`：来源详情审核，展示来源 URL、风险准入、证据摘要、LLM JSON 摘要、任务审计和审核动作。
- `agent-run.html`：Agent 手动调用，支持选择任务类型、国家城市、渠道策略、prompt template、运行上限，并展示运行控制台。

客户域新增移动端页面：

- `customers.html`：客户工作台，展示已经从线索完善并晋级后的客户池，按今日跟进、有车型意向、C 级待合规和待分配过滤。
- `customer-detail.html`：客户详情，展示客户补全数据、联系方式、意向车型、来源证据摘要、触达历史和下一步动作。
- `customer-followups.html`：客户跟进记录，展示人工触达历史、客户反馈、下一步计划和新增 CRM 跟进表单。

第二阶段新增管理后台页面：

- `admin-phase2.html`：第二阶段运行看板，展示来源新增、自动抽取、High 审核积压、LLM 成本、任务流和暂停阈值。
- `admin-llm.html`：LLM 与 Prompt 治理，展示 Provider 健康状态、prompt template 版本、fallback 边界和 Source Discovery 输出 schema。

## 3. 高保真 UI 方向

视觉方向：冷静、专业、运营控制台感。移动端模拟 iPhone 17 Pro 尺寸，使用圆角设备框、状态栏、底部 Tab Bar。界面以白色、石墨黑、冷灰为底，配合蓝色、绿色、琥珀色和红色表达任务、有效、待复核和风险状态。

设计原则：

- 操作优先，避免营销式大 hero。
- 每个页面都要能看到“下一步动作”。
- 风险标签必须可见，不把合规信息藏在二级页面。
- AI 输出必须和证据、审计、复核状态一起出现。
- 关键数字使用紧凑卡片，便于移动端扫读。

## 4. 开发落地说明

- 每个页面保持独立 HTML 文件。
- `index.html` 使用 iframe 平铺展示，不做跳转。
- 样式集中在 `css/prototype.css`。
- 图标使用 FontAwesome。
- 图片使用 Unsplash 真实车辆、物流和运营场景图片。
- 后续可按页面拆分为 uni-app 页面和 Vue 管理后台组件。

第二阶段页面落地建议：

- 移动端 `source-candidates.html` 可拆为 uni-app `pages/sources/index.vue`。
- 移动端 `source-detail.html` 可拆为 uni-app `pages/sources/detail.vue`。
- 移动端 `agent-run.html` 可拆为 uni-app `pages/agent-run/index.vue`。
- 移动端 `customers.html` 可拆为 uni-app `pages/customers/index.vue`。
- 移动端 `customer-detail.html` 可拆为 uni-app `pages/customers/detail.vue`。
- 移动端 `customer-followups.html` 可拆为 uni-app `pages/customers/followups.vue`。
- 后台 `admin-phase2.html` 可拆为 Vue 管理后台第二阶段 dashboard 页面。
- 后台 `admin-llm.html` 可拆为 Vue 管理后台 LLM/Prompt 治理页面。
- 所有页面都应对接真实 API，不应停留在 seed 静态数据。
- 来源审核页面必须保留风险闸门文案：审核通过只代表允许抽取，不代表允许触达。

客户域接口落地建议：

- 客户工作台读取 `customers`，并聚合 `contact_methods`、`lead_sources`、最近一条 `outreach_records` 和跟进计划。
- 客户详情读取单个客户完整档案，包括从 `staging_leads` 晋级时保存的来源证据、AI 摘要和缺失字段补全结果。
- 跟进记录读取并写入 `outreach_records` 或后续 CRM follow-up 表；记录人工发送状态时必须再次检查勿扰状态。
- C 级客户在报价、合同或实质交易前必须显示合规复核状态，不能只依赖客户等级标签。

## 5. 第二阶段双轮评审记录

### 第一轮评审：需求与信息架构

结论：通过。

发现项：

- 原型已覆盖移动端来源候选队列、来源详情审核、Agent 手动调用三类新增核心界面。
- 原型已覆盖管理后台第二阶段运行看板和 LLM/Prompt 治理界面。
- `index.html` 继续使用 iframe 平铺展示，符合原型交付要求。

修正结果：

- 已在移动端来源详情页明确“审核通过只代表允许抽取，不表示允许触达”。
- 已在后台 LLM 治理页补充 fallback 边界。

### 第二轮评审：合规、视觉与开发可落地性

结论：通过。

发现项：

- High/Forbidden 风险边界在移动端和后台均有可见表达。
- 新增页面沿用 iPhone 17 Pro 设备框、iOS 状态栏、底部 Tab Bar、FontAwesome 图标和真实车辆图片。
- 页面拆分方式与后续 uni-app/Vue 开发路径一致。

修正结果：

- 已补充第二阶段页面到开发落地说明，明确对应 uni-app 和 Vue 管理后台文件方向。

## 6. 客户域新增页面双轮评审记录

### 第一轮评审：需求与信息架构

结论：通过。

发现项：

- 新增页面已覆盖客户工作台、客户详情和客户跟进记录，符合“线索完善后才流转到客户页面”的业务边界。
- 客户详情已包含补全后的客户数据、联系方式、客户触达历史、客户意向车型信息和下一步动作。
- 页面没有把未完善线索直接混入客户池，保留了 `staging_leads -> customers` 的数据语义。

修正结果：

- 已在客户工作台副标题和卡片中明确“由完善线索晋级 / 来源已复核 / core customers”。
- 已在客户详情页补充“来自 staging 晋级”的客户补全数据区。

### 第二轮评审：合规、体验与开发可落地性

结论：通过。

发现项：

- 客户触达历史和跟进记录均强调人工触达，不存在自动发送、自动私信或自动加好友入口。
- C 级客户在列表中显示“合规复核”，避免销售交付前绕过复核。
- 新增页面沿用 iPhone 17 Pro 设备框、状态栏、底部 Tab Bar、FontAwesome 图标和真实车辆场景图片，风格与现有二阶段原型一致。

修正结果：

- 已在跟进记录页补充“不可自动发送”和勿扰校验状态。
- 已在开发落地建议中明确客户页对应的 uni-app 页面路径和 API 聚合方向。
