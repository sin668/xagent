# 海外车辆采购 AI 获客系统 - 第一阶段小范围运行 Epic / Story 拆解

创建日期：2026-05-29  
阶段：BMAD Epic / Story 拆解  
输入文档：

- `docs/product/2026-05-29-海外车辆采购AI获客系统-第一阶段小范围运行方案与产品技术设计.md`
- `prototypes/mvp-mobile-agent/design-brief.md`
- `prototypes/mvp-mobile-agent/index.html`

## 1. 拆解原则

本拆解服务第一阶段小范围运行，优先顺序为：

1. PostgreSQL 数据底座。
2. 渠道计划与风险规则。
3. staging 复核队列。
4. Agent 任务流。
5. 知识库 RAG。
6. 指标看板。

每个 Story 必须包含：

- 用户故事。
- 业务价值。
- 优先级。
- 依赖。
- 实现范围。
- 数据/API 影响。
- 验收标准。
- 非目标。
- 风控检查。

优先级定义：

- P0：第一阶段闭环必需。
- P1：小范围运行建议完成，显著提升效率和可治理性。
- P2：后续增强，不阻塞第一阶段上线。

## 2. 需求抽取

### 2.1 Functional Requirements

FR1：系统必须支持配置 A/B/C 渠道计划，包括国家、城市、渠道、关键词、风险等级、每日任务上限和负责人。

FR2：系统必须支持 Agent 生成候选 URL，并保存发现理由、来源平台、风险等级和任务 ID。

FR3：系统必须支持读取允许范围内的公开页面文本，并保存页面标题、公开文本摘要、来源链接和证据备注。

FR4：系统必须支持 LLM 从公开文本中抽取客户名称、国家、城市、客户类型、联系方式、活跃度、规模信号、进口/二手相关性和来源证据。

FR5：系统必须支持 LLM + 规则输出 A/B/C/Invalid/Watch 推荐等级、推荐原因、缺失字段、下一步动作和建议交付团队。

FR6：系统必须采用 PostgreSQL `raw / staging / core / audit / knowledge` 分层保存数据。

FR7：系统必须支持 staging 线索人工复核，并允许复核人员确认有效/无效、修正字段、标记重复、确认等级、分配团队和标记勿扰。

FR8：系统必须支持 High 风险渠道只读公开发现任务隔离，High 来源不得直接进入触达队列。

FR9：系统必须支持 High 来源线索二次复核，只有转为 Low/Medium 复核来源后才能进入 core。

FR10：系统必须支持来源链接和证据备注准入校验，无来源或无证据线索不得进入 core。

FR11：系统必须支持 Invalid/Watch 阻断，不进入触达队列。

FR12：系统必须支持勿扰客户阻断，不得再次进入触达队列。

FR13：系统必须支持 C 级线索报价/合同前合规复核。

FR14：系统必须保存 AI 调用审计，包括 prompt 版本、模型、输入引用、输出 JSON、知识库引用、来源证据和校验结果。

FR15：系统必须支持 PostgreSQL + pgvector 知识库，保存渠道 SOP、FAQ、触达模板、关键词、车辆知识、合规规则和失败案例。

FR16：系统必须只允许 approved 知识条目进入生产 Agent 检索。

FR17：系统必须提供后台或 API 查看每日候选 URL、staging 线索、core 有效线索、渠道产出、重复率、风险事件和 AI 成本。

FR18：系统必须支持渠道暂停和风险事件记录。

### 2.2 Non-Functional Requirements

NFR1：所有 AI 输出必须可审计、可复核、可追溯。

NFR2：系统不得执行自动社交私信、自动加好友、登录后批量采集、反爬规避或抓取非公开数据。

NFR3：缺失字段必须保留 Unknown、null 或空数组，不允许编造。

NFR4：所有入库任务必须具备幂等能力，避免重复写入。

NFR5：High 风险任务必须与 Low/Medium 自动任务隔离。

NFR6：关键规则必须后端强制执行，不能只依赖前端提示。

NFR7：每日小范围运行默认目标约 100 条候选线索，任务必须支持配额限制。

NFR8：风险事件、任务失败和规则阻断必须记录日志。

NFR9：知识库规则和 prompt 必须支持版本化。

### 2.3 UX Design Requirements

UX-DR1：移动端首页必须展示今日候选、staging、core 和风险事件，帮助运营快速判断运行状态。

UX-DR2：移动端线索池必须突出 staging 复核、High 二次复核、B/C 线索和 Watch/Invalid 状态。

UX-DR3：线索详情必须优先展示来源证据、AI 推荐原因、准入闸门和人工复核动作。

UX-DR4：Agent 任务中心必须展示渠道发现、页面读取、LLM 抽取、分级、入库的任务链路和状态。

UX-DR5：触达助手必须展示人工确认、勿扰、拒绝联系路径和合规检查，不得呈现自动发送能力。

UX-DR6：管理后台必须展示渠道计划、风险规则、High 只读边界、入库流水、知识库状态和 AI 审计。

UX-DR7：指标看板必须围绕有效线索数量，同时展示辅助硬闸门。

### 2.4 Technical Requirements

TR1：后端基于 FastAPI + PostgreSQL + SQLAlchemy/Alembic。

TR2：PostgreSQL 需要支持 pgvector 扩展。

TR3：现有 `customers`、`contact_methods`、`lead_sources`、`outreach_records`、`ai_audit_logs`、`compliance_reviews` 等 core 表应继续复用或兼容迁移。

TR4：新增表应覆盖 `channel_plans`、`collection_tasks`、`candidate_urls`、`page_snapshots`、`staging_leads`、`knowledge_collections`、`knowledge_items`、`knowledge_embeddings`、`rule_configs`、`risk_events`。

TR5：Agent 任务可先通过同步 API/脚本触发，后续再接入任务队列。

TR6：LLM 调用必须封装为可替换服务，并统一写入审计日志。

TR7：前端包括 uni-app 移动端和 Vue3 管理后台，必须对齐 `prototypes/mvp-mobile-agent` 原型的信息架构。

## 3. Epic 总览

| Epic ID | Epic | 优先级 | 目标 |
|---|---|---|---|
| P1-E1 | PostgreSQL 数据底座 | P0 | 建立 raw/staging/core/audit/knowledge 分层和关键表 |
| P1-E2 | 渠道计划与风险规则 | P0 | 管理 A/B/C/High 渠道计划、动作边界和暂停机制 |
| P1-E3 | staging 复核队列 | P0 | 支持候选线索复核、晋级 core、阻断不合规线索 |
| P1-E4 | Agent 任务流 | P0/P1 | 实现受控自动发现、公开页面读取、LLM 抽取分级和入库 |
| P1-E5 | 知识库 RAG | P1 | 使用 PostgreSQL + pgvector 支撑 Agent 上下文检索 |
| P1-E6 | 指标看板 | P1 | 展示有效线索、渠道产出、风险事件、成本和复核效率 |

## 4. P1-E1：PostgreSQL 数据底座

### Story P1-E1-S1：创建第一阶段数据分层与迁移基线

**用户故事：**  
作为研发负责人，我希望数据库明确区分 raw、staging、core、audit、knowledge 数据层，以便 Agent 结果不会直接污染正式客户库。

**业务价值：**  
为 PostgreSQL 直入库、宽进严出、AI 审计和人工复核提供基础。

**优先级：** P0

**依赖：** 现有 FastAPI/PostgreSQL/Alembic 可运行。

**实现范围：**

- 梳理现有 core 表。
- 新增第一阶段数据层命名约定。
- 新建 Alembic migration。
- 确认 pgvector 扩展安装检测方式。

**数据/API 影响：**

- 新增迁移脚本。
- 不破坏现有 core 表。

**验收标准：**

- Alembic migration 可在目标 PostgreSQL 执行。
- 数据层设计文档或表注释明确 raw/staging/core/audit/knowledge 用途。
- 迁移不删除现有业务数据。
- pgvector 缺失时给出明确错误或安装指引。

**非目标：**

- 不实现 Agent 任务逻辑。
- 不实现前端页面。

**风控检查：**

- 不修改勿扰、C 级复核等现有核心规则。
- 不使用内存 SQLite 作为正式验证环境。

### Story P1-E1-S2：实现 raw 层采集任务和候选 URL 表

**用户故事：**  
作为线索运营，我希望每个候选 URL 都能关联任务、渠道和风险等级，以便追溯线索来源。

**业务价值：**  
让候选数据有来源、有证据、有任务上下文。

**优先级：** P0

**依赖：** P1-E1-S1

**实现范围：**

- 新增 `collection_tasks`。
- 新增 `candidate_urls`。
- 支持 URL hash 幂等。
- 保存 source_platform、source_risk_level、source_usage_type、requires_secondary_verification、discovery_reason。

**数据/API 影响：**

- 新增创建/查询 collection task API。
- 新增候选 URL upsert API 或 service。

**验收标准：**

- 同一 URL 重复写入不会产生重复记录。
- High URL 默认 `requires_secondary_verification=true`。
- Forbidden 渠道不得创建可执行任务。
- 每条 candidate URL 必须关联 task_id。

**非目标：**

- 不读取页面正文。
- 不调用 LLM。

**风控检查：**

- High 任务只能标记为 public_discovery_only。
- 禁止动作字段必须可记录。

### Story P1-E1-S3：实现 page_snapshots 与来源证据保存

**用户故事：**  
作为复核人员，我希望看到候选页面标题、公开文本摘要和证据摘录，以便判断线索是否可信。

**业务价值：**  
支撑“无证据不进 core”的准入规则。

**优先级：** P0

**依赖：** P1-E1-S2

**实现范围：**

- 新增 `page_snapshots`。
- 保存 page_title、text_excerpt、evidence_note、read_status、captured_at、robots_or_policy_note。
- 支持一个 candidate URL 多次读取，但有最新快照。

**数据/API 影响：**

- 新增 page snapshot upsert/list API 或 service。

**验收标准：**

- 无 candidate_url_id 不允许写入 snapshot。
- evidence_note 为空时允许进入 raw，但不得进入 core。
- read_status 可表达 success、blocked、failed、needs_manual_review。

**非目标：**

- 不保存完整网页镜像。
- 不保存评论、粉丝、关系链等非业务必要数据。

**风控检查：**

- 登录墙、验证码、访问异常必须写入 read_status，不得继续执行读取任务。

### Story P1-E1-S4：实现 staging_leads 候选线索表

**用户故事：**  
作为线索运营，我希望 AI 抽取结果先进入 staging，以便人工复核后再进入正式客户库。

**业务价值：**  
防止 AI 错误或低质量数据污染 core。

**优先级：** P0

**依赖：** P1-E1-S3

**实现范围：**

- 新增 `staging_leads`。
- 字段覆盖客户名称、国家、城市、客户类型、contacts_json、经营信号、证据、推荐等级、推荐原因、缺失字段、review_status、queue_status、dedupe_key、requires_compliance_review。
- 支持候选 URL 关联。

**数据/API 影响：**

- 新增 staging lead create/list/detail/update API。

**验收标准：**

- 缺失字段允许 Unknown/null/[]。
- Invalid/Watch 默认 queue_status 为 not_eligible。
- High 来源默认 review_status 为 needs_secondary_verification。
- C 级默认 requires_compliance_review=true。

**非目标：**

- 不实现人工复核晋级 core。

**风控检查：**

- 不允许无来源 URL 的 staging lead 晋级 core。

### Story P1-E1-S5：实现 audit/risk 基础日志表

**用户故事：**  
作为合规负责人，我希望 AI 调用、Agent 执行、规则阻断和风险事件都被记录，以便追责和复盘。

**业务价值：**  
满足 AI 输出可审计、渠道风险可追踪的要求。

**优先级：** P0

**依赖：** P1-E1-S1

**实现范围：**

- 扩展或复用 `ai_audit_logs`。
- 新增 `agent_run_logs`、`review_logs`、`risk_events`。
- 统一记录 task_id、agent_name、action、input_ref、output_ref、result、error_message。

**数据/API 影响：**

- 新增日志写入 service。
- 可选新增后台查询 API。

**验收标准：**

- LLM 调用必须能记录 prompt_version、model_name、output_json、source_urls。
- 风险事件必须能记录 channel、risk_level、event_type、severity、resolution_status。
- 规则阻断必须记录阻断原因。

**非目标：**

- 不做复杂 SIEM 或告警平台。

**风控检查：**

- 审计日志不得保存无关私人内容。

## 5. P1-E2：渠道计划与风险规则

### Story P1-E2-S1：实现 channel_plans 渠道计划管理

**用户故事：**  
作为线索运营，我希望能配置每天运行哪些渠道、关键词、城市和配额，以便控制小范围运行节奏。

**业务价值：**  
让每日 100 条候选线索目标可控、可调、可复盘。

**优先级：** P0

**依赖：** P1-E1-S1

**实现范围：**

- 新增 `channel_plans`。
- 支持国家、城市、渠道名称、渠道类型、风险等级、关键词、daily_url_limit、daily_lead_limit、status、owner。
- 支持启用、暂停、归档。

**数据/API 影响：**

- 新增 channel plan CRUD API。

**验收标准：**

- Low/Medium/High/Forbidden 风险等级必须枚举校验。
- daily_url_limit 不得为空。
- Forbidden 计划不能启用。
- High 计划启用时必须限定 public_discovery_only。

**非目标：**

- 不实现自动搜索执行。

**风控检查：**

- 不允许创建包含自动私信、加好友、登录采集的计划。

### Story P1-E2-S2：实现渠道允许/禁止动作规则校验

**用户故事：**  
作为合规负责人，我希望每个 Agent 动作都经过允许/禁止动作校验，以便阻断越界行为。

**业务价值：**  
把合规边界落到后端规则，而不是只停留在文档。

**优先级：** P0

**依赖：** P1-E2-S1、现有 channel risk rules

**实现范围：**

- 新增或扩展 `rule_configs` / `channel_risk_rules`。
- 实现 action validator service。
- 支持 allowed_actions、forbidden_actions、risk_level、source_usage_type 校验。

**数据/API 影响：**

- 新增规则查询/校验 API 或 service。

**验收标准：**

- login、message、friend_request、join_group、scrape_comments、scrape_followers、bypass_rate_limit 必须被阻断。
- High 渠道只允许 read_public_page、extract_business_contact、capture_limited_evidence 等只读动作。
- 阻断动作必须写 risk_events 或 agent_run_logs。

**非目标：**

- 不做自动政策变更监控。

**风控检查：**

- 规则必须服务端执行。

### Story P1-E2-S3：实现 High 只读公开发现任务隔离

**用户故事：**  
作为合规负责人，我希望 High 渠道任务与 Low/Medium 自动任务隔离，以便防止 High 结果误入触达队列。

**业务价值：**  
在探索 High 公开线索密度的同时控制平台和触达风险。

**优先级：** P0

**依赖：** P1-E1-S2、P1-E2-S2

**实现范围：**

- 支持 task_type=`high_risk_public_discovery`。
- High task 默认 max sample 限制。
- High candidate 默认 queue_eligible=false。
- High candidate 默认 requires_secondary_verification=true。

**数据/API 影响：**

- 更新 collection task 创建逻辑。
- 更新 candidate URL 默认值规则。

**验收标准：**

- High 任务无法触发触达类 action。
- High 线索无法直接进入 core 或 outreach queue。
- High 任务出现验证码/登录墙时自动进入 blocked。

**非目标：**

- 不实现 High 平台登录访问。

**风控检查：**

- 不允许采集评论、粉丝、好友、关系链。

### Story P1-E2-S4：实现渠道暂停与风险事件处理

**用户故事：**  
作为运营负责人，我希望某个渠道出现异常时能立即暂停，以便保护账号、平台和品牌风险。

**业务价值：**  
让小范围运行有可控的止损机制。

**优先级：** P1

**依赖：** P1-E2-S1、P1-E1-S5

**实现范围：**

- 支持 channel_plan status=pause。
- 风险事件可关联 channel_plan。
- 暂停后不允许创建新 collection_task。
- 支持风险事件 resolution_status。

**数据/API 影响：**

- 更新 channel plan 状态 API。
- 新增 risk event create/resolve API。

**验收标准：**

- 暂停渠道无法启动新任务。
- 恢复渠道必须记录处理说明。
- 风险事件可按 severity 查询。

**非目标：**

- 不做自动发消息告警。

**风控检查：**

- 投诉、封禁、违规风险必须触发暂停建议。

## 6. P1-E3：staging 复核队列

### Story P1-E3-S1：实现 staging 复核列表与筛选

**用户故事：**  
作为线索运营，我希望按待复核、B/C、High 二次复核、缺联系方式、Watch 等视图查看 staging 线索。

**业务价值：**  
提升人工复核效率，优先处理最可能进入 core 的线索。

**优先级：** P0

**依赖：** P1-E1-S4

**实现范围：**

- 新增 staging 列表 API 筛选。
- 支持 review_status、recommended_grade、queue_status、source_risk_level、has_contact、requires_secondary_verification。
- 前端实现复核队列页面。

**数据/API 影响：**

- 新增或扩展 `/staging-leads` API。
- 管理后台和移动端线索复核池对接。

**验收标准：**

- 可筛选待复核线索。
- 可筛选 High 二次复核线索。
- 可筛选 Invalid/Watch。
- 列表展示来源、风险、推荐等级、联系方式状态和证据状态。

**非目标：**

- 不实现批量自动晋级 core。

**风控检查：**

- High/Watch/Invalid 在列表中必须有明显风险标记。

### Story P1-E3-S2：实现 staging 线索详情与证据视图

**用户故事：**  
作为复核人员，我希望在线索详情中看到来源证据、AI 推荐原因、缺失字段和准入闸门，以便做出复核决定。

**业务价值：**  
保证进入 core 的线索有证据、有判断依据。

**优先级：** P0

**依赖：** P1-E3-S1、P1-E1-S3

**实现范围：**

- 线索详情 API 返回 staging lead、candidate URL、page snapshot、AI audit summary。
- 前端展示来源链接、证据备注、AI 推荐、缺失字段、闸门状态。

**数据/API 影响：**

- 扩展 staging detail API。

**验收标准：**

- 详情页必须展示来源链接和证据备注。
- 详情页必须展示推荐等级和推荐原因。
- 详情页必须展示能否进入 core 的原因。
- 无证据或无来源时禁止晋级按钮。

**非目标：**

- 不展示完整网页内容。

**风控检查：**

- 不展示无关私人内容或关系链。

### Story P1-E3-S3：实现人工复核晋级 core

**用户故事：**  
作为线索运营，我希望把复核通过的 staging 线索晋级到 core 客户库，以便交付客服或销售。

**业务价值：**  
完成宽进严出的关键闭环。

**优先级：** P0

**依赖：** P1-E3-S2、现有 core customer/contact/source 模型

**实现范围：**

- 实现 promote staging lead to core service。
- 写入或更新 customers、contact_methods、lead_sources。
- 保留 staging 与 core 的映射。
- 写 review_logs。

**数据/API 影响：**

- 新增 `/staging-leads/{id}/promote` API。

**验收标准：**

- 来源链接缺失不得晋级。
- 证据备注缺失不得晋级。
- High 未二次复核不得晋级。
- Invalid/Watch 不得晋级到待触达。
- C 级晋级后必须带合规复核标记。
- 勿扰状态必须保留。

**非目标：**

- 不自动触达客户。

**风控检查：**

- 晋级动作必须记录操作人、时间和复核结论。

### Story P1-E3-S4：实现重复检测和合并建议

**用户故事：**  
作为线索运营，我希望系统提示强重复和疑似重复，以便避免重复触达。

**业务价值：**  
减少数据污染，提高客户库可信度。

**优先级：** P1

**依赖：** P1-E1-S4、core customer/contact/source 模型

**实现范围：**

- 强重复：标准化客户名称 + 联系方式 hash。
- 疑似重复：标准化客户名称 + 城市 + 来源域名。
- 来源重复：URL hash。
- 展示重复候选并允许人工处理。

**数据/API 影响：**

- 新增 dedupe service。
- staging list/detail 返回 duplicate signals。

**验收标准：**

- 强重复必须阻止重复晋级。
- 疑似重复必须进入人工复核，不自动删除。
- 合并后保留所有来源证据。

**非目标：**

- 不做复杂机器学习去重。

**风控检查：**

- 不因去重丢失勿扰状态。

## 7. P1-E4：Agent 任务流

### Story P1-E4-S1：实现渠道发现 Agent 任务

**用户故事：**  
作为线索运营，我希望 Agent 根据渠道计划自动生成候选 URL，以便每天稳定发现候选线索。

**业务价值：**  
支撑每日 100 条候选线索目标。

**优先级：** P0

**依赖：** P1-E1-S2、P1-E2-S1

**实现范围：**

- 根据 channel_plan 生成 search_task。
- 支持关键词、城市、渠道类型。
- 输出候选 URL 和发现理由。
- 写入 collection_tasks 和 candidate_urls。

**数据/API 影响：**

- 新增 run channel discovery API 或脚本入口。

**验收标准：**

- 不超过 channel_plan daily_url_limit。
- Forbidden 计划不执行。
- High 计划只生成 public_discovery_only 候选。
- 所有候选 URL 幂等写入。

**非目标：**

- 不实现登录平台检索。
- 不绕过搜索引擎限制。

**风控检查：**

- 不生成私信、加好友、入群任务。

### Story P1-E4-S2：实现公开页面读取 Agent 任务

**用户故事：**  
作为线索运营，我希望 Agent 读取候选 URL 的公开文本摘要，以便后续 AI 抽取。

**业务价值：**  
减少人工复制公开文本，提高处理效率。

**优先级：** P0

**依赖：** P1-E1-S3、P1-E2-S2

**实现范围：**

- 读取公开页面标题和文本摘要。
- 保存 page_snapshots。
- 检测登录墙、验证码、访问异常。
- 支持 read_status。

**数据/API 影响：**

- 新增 run page read API 或脚本入口。

**验收标准：**

- 不登录。
- 不绕过访问限制。
- 出现验证码或登录墙时停止并记录 blocked。
- High 页面只保存公开商务字段和有限证据。

**非目标：**

- 不做大规模爬虫。
- 不保存完整网页镜像。

**风控检查：**

- 不保存评论、粉丝、好友、关系链。

### Story P1-E4-S3：实现 LLM 线索抽取任务

**用户故事：**  
作为线索运营，我希望 LLM 从公开文本中抽取结构化客户信息，以便进入 staging 复核。

**业务价值：**  
减少俄语网页人工阅读和整理成本。

**优先级：** P0

**依赖：** P1-E1-S4、P1-E1-S5、P1-E4-S2

**实现范围：**

- 调用 lead extraction prompt。
- 输出符合 schema 的 JSON。
- 写入 staging_leads。
- 写入 ai_audit_logs。

**数据/API 影响：**

- 新增 LLM extraction service。

**验收标准：**

- 输出包含客户名称、国家、城市、客户类型、联系方式、经营信号、来源证据。
- 缺失字段为 Unknown/null/[]。
- 不允许编造联系方式。
- 输出 JSON schema 校验失败时不得写入 staging，需记录失败案例。

**非目标：**

- 不做自动触达。

**风控检查：**

- 每条抽取结果必须关联 source_url 和 evidence_note。

### Story P1-E4-S4：实现 LLM 分级与规则校验任务

**用户故事：**  
作为线索运营，我希望系统给出 A/B/C/Invalid/Watch 建议并执行规则校验，以便更快筛选有效线索。

**业务价值：**  
提升复核优先级排序，减少无效线索进入人工队列。

**优先级：** P0

**依赖：** P1-E4-S3、P1-E2-S2

**实现范围：**

- 调用 lead grading prompt。
- 结合规则校验渠道风险、联系方式、证据、勿扰、C 级复核。
- 更新 staging_leads 推荐等级和 queue_status。

**数据/API 影响：**

- 新增 grading service。
- 写入 ai_audit_logs 和 rule validation result。

**验收标准：**

- Invalid/Watch queue_status 必须为 not_eligible。
- High 未二次复核 queue_status 必须为 blocked 或 needs_secondary_verification。
- C 级 requires_compliance_review=true。
- 推荐原因必须引用证据。

**非目标：**

- 不做黑箱评分模型。

**风控检查：**

- LLM 推荐不得覆盖硬规则阻断。

### Story P1-E4-S5：实现 Agent 失败案例记录

**用户故事：**  
作为 AI/Agent 操作人员，我希望任务失败、schema 错误、无证据输出和风险阻断被记录，以便优化 prompt 和渠道策略。

**业务价值：**  
建立质量反馈闭环。

**优先级：** P1

**依赖：** P1-E1-S5、P1-E4-S3、P1-E4-S4

**实现范围：**

- 记录 failed_cases。
- 分类失败原因：fetch_failed、schema_invalid、missing_evidence、risk_blocked、duplicate、llm_suspected_fabrication。
- 支持后台查询。

**数据/API 影响：**

- 新增 failed_cases 表或复用 knowledge failed_cases 集合。

**验收标准：**

- schema 校验失败必须有失败记录。
- 疑似编造必须有风险事件或失败案例。
- 失败案例可用于后续知识库 RAG。

**非目标：**

- 不自动修复 prompt。

**风控检查：**

- 失败记录不能把无效线索推进触达队列。

## 8. P1-E5：知识库 RAG

### Story P1-E5-S1：创建 PostgreSQL + pgvector 知识库表

**用户故事：**  
作为 AI 负责人，我希望知识库和业务数据统一放在 PostgreSQL 中，以便 Agent 可检索已审核知识。

**业务价值：**  
为 LLM 抽取、分级、话术和合规提示提供可控上下文。

**优先级：** P1

**依赖：** P1-E1-S1

**实现范围：**

- 新增 `knowledge_collections`、`knowledge_items`、`knowledge_embeddings`。
- 支持 status、review_status、version、source_ref。
- 配置 pgvector embedding 字段。

**数据/API 影响：**

- 新增知识库 CRUD API。

**验收标准：**

- 只有 approved 知识可被生产检索。
- deprecated 知识不得进入 RAG。
- embedding 写入失败不影响结构化知识保存，但要记录错误。

**非目标：**

- 不做复杂知识图谱。

**风控检查：**

- 合规规则不可仅作为语义建议，仍需结构化规则执行。

### Story P1-E5-S2：导入第一阶段知识集合

**用户故事：**  
作为线索运营，我希望关键词、渠道 SOP、FAQ、话术模板、合规规则和失败案例进入知识库，以便 Agent 使用统一上下文。

**业务价值：**  
减少散落文档和 prompt 漂移。

**优先级：** P1

**依赖：** P1-E5-S1、现有 docs/poc 文档

**实现范围：**

- 从现有 markdown/Excel/seed 数据导入 knowledge_items。
- 建立 collection：channel_sop、faq、script_template、keyword_library、vehicle_knowledge、compliance_rules、failed_cases。
- 设置初始 review_status。

**数据/API 影响：**

- 新增导入脚本或管理后台导入入口。

**验收标准：**

- 至少导入渠道 SOP、俄罗斯关键词库、FAQ/话术、失败案例。
- 每条知识有 collection、title、body、language、country、source_ref。
- 未审核知识不得进入生产 Agent。

**非目标：**

- 不要求一次性导入所有历史文档。

**风控检查：**

- 触达话术必须保留禁止承诺点和拒绝联系路径。

### Story P1-E5-S3：实现知识检索 API

**用户故事：**  
作为 Agent 服务，我希望根据任务类型检索相关知识条目，以便给 LLM 提供上下文。

**业务价值：**  
提高抽取、分级和话术生成的一致性。

**优先级：** P1

**依赖：** P1-E5-S1

**实现范围：**

- 支持按 collection、country、language、channel、query 检索。
- 支持向量检索和关键词 fallback。
- 只返回 approved 条目。

**数据/API 影响：**

- 新增 `/knowledge/search` API 或 service。

**验收标准：**

- 查询 channel_sop 只返回 approved SOP。
- 查询 faq/script_template 可按语言过滤。
- pgvector 不可用时给出明确错误或使用关键词 fallback。

**非目标：**

- 不实现多模型 rerank。

**风控检查：**

- 不返回 deprecated 或未审核合规规则。

### Story P1-E5-S4：将 RAG 接入抽取、分级和话术 prompt

**用户故事：**  
作为 AI 负责人，我希望 LLM 调用能引用知识库条目，以便输出更稳定并可追溯。

**业务价值：**  
降低模型漂移，提高审计质量。

**优先级：** P1

**依赖：** P1-E5-S3、P1-E4-S3、P1-E4-S4

**实现范围：**

- 抽取任务检索关键词库、渠道 SOP。
- 分级任务检索分级规则、失败案例、渠道 SOP。
- 话术任务检索 FAQ、触达模板、合规规则。
- AI 审计保存 knowledge_item_refs。

**数据/API 影响：**

- 更新 LLM service 输入上下文。
- 扩展 ai_audit_logs 字段或 JSON。

**验收标准：**

- 每次 RAG 调用保存知识条目引用。
- 未命中知识库时记录 empty_context，不阻塞基础抽取。
- 合规硬规则仍由规则服务执行，不由 LLM 自行决定。

**非目标：**

- 不做全自动知识更新。

**风控检查：**

- 禁止用未审核话术生成外发内容。

## 9. P1-E6：指标看板

### Story P1-E6-S1：实现每日运行漏斗指标

**用户故事：**  
作为业务负责人，我希望看到每日候选 URL、staging 线索和 core 有效线索，以便判断小范围运行是否达标。

**业务价值：**  
支撑 Go/No-Go 主指标：有效线索数量。

**优先级：** P1

**依赖：** P1-E1-S2、P1-E1-S4、P1-E3-S3

**实现范围：**

- 统计 candidate_urls、staging_leads、core customers。
- 支持按日期、渠道、风险等级过滤。
- 管理后台展示漏斗。

**数据/API 影响：**

- 新增 `/dashboard/phase-one-funnel` API。

**验收标准：**

- 能展示每日候选线索约 100 的完成情况。
- 能展示 core 有效线索数量。
- 能按渠道查看贡献。

**非目标：**

- 不做完整 BI。

**风控检查：**

- High 只读结果不得计入可触达有效线索。

### Story P1-E6-S2：实现渠道有效率和质量指标

**用户故事：**  
作为运营负责人，我希望按渠道查看有效率、B/C 比例、联系方式完整率和重复率，以便调整渠道配额。

**业务价值：**  
让 A/B/C 渠道并重策略可评估。

**优先级：** P1

**依赖：** P1-E6-S1、P1-E3-S4

**实现范围：**

- 统计各渠道候选、staging、core、B/C、Invalid/Watch、重复率。
- 展示联系方式完整率、证据完整率。

**数据/API 影响：**

- 新增或扩展渠道指标 API。

**验收标准：**

- 能区分 Low/Medium/High/Quality 渠道。
- 能展示 High 二次复核通过率。
- 能展示重复率。

**非目标：**

- 不做自动预算优化。

**风控检查：**

- 风险事件应与渠道指标关联展示。

### Story P1-E6-S3：实现风险事件与暂停渠道看板

**用户故事：**  
作为合规负责人，我希望看到风险事件、阻断动作和暂停渠道，以便及时处理。

**业务价值：**  
保障小范围运行不越界。

**优先级：** P1

**依赖：** P1-E1-S5、P1-E2-S4

**实现范围：**

- 展示 risk_events。
- 展示暂停中的 channel_plans。
- 展示阻断原因和处理状态。

**数据/API 影响：**

- 新增风险看板 API。

**验收标准：**

- High 越界、勿扰误入触达、验证码/平台警告必须可见。
- 风险事件可标记 resolved。
- 暂停渠道恢复需说明。

**非目标：**

- 不接入短信/IM 告警。

**风控检查：**

- 风险事件不得被物理删除，只能关闭或归档。

### Story P1-E6-S4：实现 LLM 成本与人工复核效率统计

**用户故事：**  
作为业务负责人，我希望看到每条有效线索的 LLM 成本和人工复核耗时，以便判断 ROI。

**业务价值：**  
避免只追数量导致成本失控。

**优先级：** P2

**依赖：** P1-E1-S5、P1-E3-S3

**实现范围：**

- 统计 LLM 调用次数、token/cost 字段、失败率。
- 统计 staging 创建到复核完成耗时。
- 计算每条 core 有效线索平均成本。

**数据/API 影响：**

- 扩展 ai_audit_logs 成本字段。
- 新增 ROI 指标 API。

**验收标准：**

- 能按日期和渠道查看 LLM 成本。
- 能查看人工复核平均耗时。
- 能计算每条 core 有效线索平均 AI 成本。

**非目标：**

- 不做财务级成本核算。

**风控检查：**

- 成本指标不得包含敏感 prompt 原文。

## 10. 建议实施顺序

1. P1-E1-S1：创建第一阶段数据分层与迁移基线。
2. P1-E1-S2：实现 raw 层采集任务和候选 URL 表。
3. P1-E1-S3：实现 page_snapshots 与来源证据保存。
4. P1-E1-S4：实现 staging_leads 候选线索表。
5. P1-E1-S5：实现 audit/risk 基础日志表。
6. P1-E2-S1：实现 channel_plans 渠道计划管理。
7. P1-E2-S2：实现渠道允许/禁止动作规则校验。
8. P1-E2-S3：实现 High 只读公开发现任务隔离。
9. P1-E3-S1：实现 staging 复核列表与筛选。
10. P1-E3-S2：实现 staging 线索详情与证据视图。
11. P1-E3-S3：实现人工复核晋级 core。
12. P1-E4-S1 至 P1-E4-S4：实现 Agent 任务流。
13. P1-E5-S1 至 P1-E5-S4：实现知识库 RAG。
14. P1-E6-S1 至 P1-E6-S3：实现指标和风险看板。
15. P1-E6-S4：补充成本与复核效率统计。

## 11. 第一批建议创建的 Story 文件

建议先创建 Sprint 级目录：

`docs/stories/phase-1-small-run/`

第一批 Story：

- `P1-E1-S1-data-layer-migration-baseline.md`
- `P1-E1-S2-raw-collection-task-candidate-url.md`
- `P1-E1-S3-page-snapshots-source-evidence.md`
- `P1-E1-S4-staging-leads.md`
- `P1-E1-S5-audit-risk-logs.md`
- `P1-E2-S1-channel-plans.md`
- `P1-E2-S2-channel-action-policy-validator.md`
- `P1-E2-S3-high-risk-public-discovery-isolation.md`

## 12. 拆解自检

- 已覆盖 PostgreSQL 数据底座。
- 已覆盖渠道计划与风险规则。
- 已覆盖 staging 复核队列。
- 已覆盖 Agent 任务流。
- 已覆盖知识库 RAG。
- 已覆盖指标看板。
- 已保留不自动私信、不自动加好友、不登录批采、不反爬规避边界。
- 已保留 AI 审计、来源证据、勿扰阻断、C 级复核、High 二次复核。
