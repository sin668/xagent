---
stepsCompleted: [1]
inputDocuments:
  - docs/x-p1-deploy.md
  - docs/product/2026-05-29-海外车辆采购AI获客系统-第一阶段小范围运行方案与产品技术设计.md
  - docs/stories/phase-1-small-run/README.md
session_topic: "海外车辆采购 AI 获客系统第二阶段小范围运行 - LLM 来源发现 Agent"
session_goals: "围绕真实 LLM 接入、自动定时运行、持续新增 lead_sources、移动端来源审核、LEAD_EXTRACTION 自动消费来源池和端到端链路串联，形成可执行的第二阶段方案"
selected_approach: "BMAD 引导式分维度头脑风暴"
techniques_used: []
ideas_generated: []
context_file: ""
---

# 第二阶段小范围运行 - LLM 来源发现 Agent 头脑风暴记录

创建时间：2026-06-02 CST

## Session Overview

**主题：** 当前系统 LLM 不能正常直接使用，第二阶段需要实现真实 LLM 连接、自动定时启动、持续新增线索来源，并把来源审核、线索搜索、抽取、审计和移动端复核串成闭环。

**目标：**

1. 让系统可以正常连接真实 LLM Provider。
2. 让 LLM Agent 可以自动定时运行。
3. 新增持续发现来源的 LLM Agent，自动不断丰富 `lead_sources` 来源池。
4. 移动端新增线索来源审核页面，由人工复核风险。
5. `LEAD_EXTRACTION` 从来源池中获取来源并自动执行搜索、抽取、审计和后续处理。
6. 保持不自动社交私信、不自动加好友、不登录后批量采集、不反爬规避。

## 已继承的核心边界

- 不自动社交私信。
- 不自动加好友。
- 不登录后批量采集。
- 不反爬规避。
- 不抓取非公开数据。
- 高风险来源可以被发现，但不得直接进入触达链路。
- 所有 LLM 输出必须保留来源证据、输入输出、模型、prompt 版本和审计记录。
- 缺失字段不得编造。
- 勿扰客户不得进入触达队列。
- C 级线索报价、合同或实质交易前必须合规复核。

## 当前关键判断

第一阶段已实现 LLM 输出 JSON 的校验、入库和审计，但系统目前主要是“间接调用模式”：外部先产生 LLM JSON，再调用后端接口校验和入库。第二阶段需要补齐真实 LLM Provider 调用、定时任务、来源发现 Agent、来源审核页面和自动消费链路。

## 讨论记录

### 维度 1：来源发现范围与风险边界

#### 已确认决定

第二阶段来源发现 Agent 采用 **A + B + C 并行**：

- A：官网、公开目录、搜索引擎、地图等 Low/Medium 风险来源。
- B：公开社媒、公开视频页、平台公开商户页等 High 风险发现入口。
- C：行业链路来源，例如协会、展会、B2B、物流/清关、检测/维修机构、进口车服务生态。

高风险来源允许进入“来源候选/待审池”，但不得直接进入自动触达链路。

#### 专业建议

- 来源发现 Agent 应以“全量发现、分级入池、人工审核、定时消费”为主流程。
- `lead_sources` 不宜继续只表示已绑定客户的正式来源；第二阶段需要扩展或新增来源候选状态字段，否则“自动新增来源”和“正式客户来源”会混在一起。
- 高风险来源默认只允许 `discovery_only`，后续必须由人工复核或 Low/Medium 二次来源确认后，才允许进入抽取链路。

#### 初步流程

`LLM Source Discovery Agent -> lead_sources 来源池 -> 移动端来源审核 -> approved 来源进入 LEAD_EXTRACTION 队列 -> 自动读取/搜索/抽取 -> staging/core/audit`

### 维度 2：数据模型与来源池边界

#### 已确认决定

第二阶段新增 `lead_source_candidates` 表，作为 LLM Source Discovery Agent 持续自动发现的来源候选池。

审核通过后，再进入正式自动化链路：

`lead_source_candidates -> 人工审核 approved -> LEAD_EXTRACTION 自动消费 -> candidate_urls/page_snapshots/staging_leads -> core customers/lead_sources`

#### 专业建议

不建议直接扩展现有 `lead_sources` 承载未审核来源。当前 `lead_sources.customer_id` 为必填，语义是“已确认客户的正式来源”。如果把未绑定客户的来源直接写入 `lead_sources`，会破坏 core 层数据含义，也会影响已有客户来源、ROI 和渠道看板统计。

建议第二阶段采用三层来源结构：

1. `lead_source_candidates`
   - 来源候选池。
   - 由 LLM Agent、搜索 Agent、人工导入或行业渠道拓展产生。
   - 可以没有客户 ID。
   - 必须有来源 URL、平台、风险等级、发现原因、证据摘要、审核状态和审计引用。

2. `candidate_urls/page_snapshots`
   - 已批准来源进入自动读取和抽取链路后的 raw 层记录。
   - 负责页面读取、公开文本、快照、读取状态和异常。

3. `lead_sources`
   - core 层正式来源。
   - 只在 staging 晋级 core 或客户来源确认后写入。
   - 继续保持与 `customers` 绑定。

#### 建议字段方向

`lead_source_candidates` 建议包含：

- `id`
- `source_url`
- `source_url_hash`
- `source_title`
- `platform`
- `country`
- `city`
- `channel_name`
- `channel_risk_level`
- `source_usage_type`
- `discovery_method`
- `discovered_by_agent`
- `discovery_task_id`
- `discovery_prompt_version`
- `discovery_model_name`
- `discovery_reason`
- `evidence_excerpt`
- `evidence_note`
- `risk_flags`
- `review_status`
- `reviewer`
- `review_note`
- `reviewed_at`
- `approved_for_extraction`
- `extraction_status`
- `last_extracted_at`
- `created_at`
- `updated_at`

#### 风控边界

- High 来源默认 `approved_for_extraction=false`，只能人工审核后进入只读公开抽取。
- Forbidden 来源不得进入自动抽取。
- 无证据摘要、无来源 URL、无法识别平台或出现登录墙/验证码的平台来源，不得进入自动抽取。
- 人工审核只批准“来源是否可用于自动抽取”，不代表客户可触达。

### 维度 3：真实 LLM Provider 接入策略

#### 已确认决定

第二阶段采用 **多 Provider 可切换，默认 DeepSeek**：

- 默认 Provider：DeepSeek。
- 兼容接口：OpenAI-compatible。
- 预留 Provider：OpenAI、Claude，以及后续其他兼容模型。
- 目标不是固定某一家，而是抽象统一的 LLM client，保证可替换、可降级、可重试。

#### 专业建议

- 先做一层统一的 `LLMClient` 抽象，不要让业务服务直接依赖某一家 SDK。
- 配置至少需要拆成：`LLM_PROVIDER`、`LLM_API_KEY`、`LLM_BASE_URL`、`LLM_DEFAULT_MODEL`、`LLM_EXTRACTION_MODEL`、`LLM_GRADING_MODEL`、`LLM_SOURCE_DISCOVERY_MODEL`。
- `.env` 当前配置明显不正确，应该在第二阶段先修正为可运行配置，再做运行时健康检查和失败降级。
- 真实调用要支持：
  - 超时
  - 重试
  - 失败回退
  - 审计写入
  - prompt 版本记录
  - token/cost 记录

#### 需要确认的调用范围

- 来源发现 Agent 是否直接调用 LLM 生成候选来源描述。
- `LEAD_EXTRACTION` 是否自动调用真实 LLM 读取来源候选并输出结构化结果。
- `LEAD_GRADING` 是否自动调用真实 LLM 做分级建议。
- 触达草稿是否在第二阶段一并接入真实 LLM，还是后置。

### 维度 4：自动定时运行方式

#### 已确认决定

第二阶段采用 **混合模式：定时自动跑 + 手动触发 + 失败重试队列**。

建议节奏：

- 定时任务：每 1 小时自动运行一次来源发现 Agent。
- 手动触发：后台或移动端允许运营/合规/管理员触发专项补跑。
- 重试队列：失败任务进入重试队列，由独立 worker 处理，避免主任务链路阻塞。

#### 专业建议

- 不建议只做 cron；因为小范围运行会遇到渠道波动、封禁、超时、关键词误差，必须保留人工补跑入口。
- 不建议只做手动触发；因为“不断自动新增来源”本质上需要稳定的定时巡航。
- 失败重试应区分：
  - LLM 调用失败
  - 页面读取失败
  - 风险阻断
  - schema 校验失败
  - 重复来源跳过

#### 推荐任务编排

1. `source_discovery_scheduler`
   - 定时拉起来源发现。
2. `source_discovery_worker`
   - 读取渠道规则、关键词库、风险策略。
3. `source_candidate_upsert_worker`
   - 写入 `lead_source_candidates`。
4. `source_review_queue_worker`
   - 推送待审任务到移动端审核队列。
5. `lead_extraction_worker`
   - 仅消费已批准来源，自动调用 LLM 抽取。
6. `lead_grading_worker`
   - 自动调用 LLM 分级并执行硬规则。
7. `retry_worker`
   - 处理失败任务重试与告警记录。

### 维度 5：LEAD_EXTRACTION 自动消费范围

#### 已确认决定

`LEAD_EXTRACTION` 采用 **按风险分层自动消费**：

- Low：可自动进入 `LEAD_EXTRACTION`。
- Medium：可自动进入 `LEAD_EXTRACTION`，但需要限量、异常暂停和审计。
- High：必须人工审核通过后，才允许只读抽取；不得直接触达。
- Forbidden：不得进入自动抽取任务。

#### 专业建议

- `lead_source_candidates.review_status` 和 `approved_for_extraction` 应共同决定是否可消费。
- 对 Low/Medium，可以默认 `approved_for_extraction=true`，但仍要保留人工抽查与风控暂停机制。
- 对 High，必须默认 `approved_for_extraction=false`，移动端人工审核后才可进入只读抽取。
- 对 Forbidden，系统应直接阻断，并写入 `risk_events` 或失败案例。

#### 建议准入规则

`LEAD_EXTRACTION` worker 只消费满足以下条件的来源：

- `review_status in ('auto_approved', 'approved')`
- `approved_for_extraction = true`
- `extraction_status in ('pending', 'retry')`
- `channel_risk_level in ('Low', 'Medium')`，或 `channel_risk_level = 'High' and human_review_required=false after approval`
- 非 Forbidden。
- 未触发暂停渠道规则。
- 有 `source_url`、`platform`、`evidence_note` 或 `discovery_reason`。

#### 风险边界

- Low/Medium 自动抽取不等于自动触达。
- High 审核通过只表示允许读取公开来源，不表示客户可交付。
- 所有抽取输出仍需走 schema 校验、证据校验、去重和 staging/core 闸门。

### 维度 6：来源发现 Agent 的持续生成策略

#### 已确认决定

来源发现 Agent 采用 **A + B + C 全部使用，分阶段实现**：

1. A：基于关键词库 + 国家/城市 + 渠道计划，自动生成搜索查询。
2. B：基于已有高质量来源，推导相似来源、相关目录和行业链路。
3. C：基于失败案例和渠道质量指标，自动调整关键词与渠道优先级。

#### 专业建议

- 第一阶段实现优先级应是 A -> B -> C。
- A 是稳定基座，负责可重复、可审计的来源发现。
- B 提升覆盖面，但必须受限于白名单渠道和相似来源证据。
- C 是闭环优化能力，应该等前两层稳定后再打开自动调参。

#### 推荐输出

来源发现 Agent 每次运行应输出：

- 新候选来源 URL
- 来源平台
- 国家/城市
- 渠道名称
- 风险等级
- 发现理由
- 关键词命中项
- 证据摘要
- 是否建议进入待审池
- 是否建议进入自动抽取队列

#### 任务边界

- 不直接写入 `lead_sources` 正式表，除非审核通过或明确进入正式来源流程。
- 不自动触达。
- 不自动社交私信。
- 不绕过平台限制。

### 维度 7：移动端来源审核页面

#### 已确认决定

移动端审核对象为 `lead_source_candidates`，不是正式 `lead_sources`。

审核页面需要支持：

- 查看候选来源 URL、平台、国家、城市、渠道、风险等级、发现理由和证据摘要。
- 查看 LLM 发现输出和审计信息。
- 查看该来源是否已进入自动抽取队列。
- 执行审核动作并记录审核备注。

#### 建议审核动作

- `approve_for_extraction`：通过并进入自动抽取。
- `reject`：驳回来源候选。
- `mark_high_risk`：标记高风险，仅允许只读分析或人工复核。
- `send_to_manual_review`：送人工二次复核。
- `pause_channel`：暂停当前渠道计划。
- `add_review_note`：添加备注。
- `retrigger_discovery`：触发重新发现或补充来源。

#### 专业建议

- 移动端页面应以“待审队列 -> 详情页 -> 审核动作”三段式为主，不要把所有信息塞在一屏。
- 详情页必须突出：
  - 来源 URL
  - 风险等级
  - 证据摘要
  - 是否可自动抽取
  - 最近一次发现时间
  - 审核状态
  - 审核备注
- 审核通过后，不代表可触达，只代表可进入自动抽取。

#### 状态建议

- `pending`
- `in_review`
- `approved_for_extraction`
- `rejected`
- `high_risk_review`
- `paused`
- `needs_recheck`

### 维度 8：候选来源默认审核状态

#### 已确认决定

LLM 来源发现 Agent 写入候选来源时，按风险等级设置默认审核状态：

- Low：默认 `auto_approved`，`approved_for_extraction=true`。
- Medium：默认 `auto_approved`，`approved_for_extraction=true`，但需要限量和异常暂停。
- High：默认 `high_risk_review`，`approved_for_extraction=false`。
- Forbidden：默认阻断或驳回，不进入自动抽取。

#### 专业建议

- 这样可以兼顾“不断自动新增来源”和“高风险来源不越界”。
- Low/Medium 自动通过只代表可进入自动抽取，不代表可触达。
- Medium 必须记录渠道限额、异常事件和最近暂停状态。
- High 必须通过移动端人工审核后才能进入只读抽取。

#### 风控边界

- 自动通过不得跳过证据要求。
- 自动通过不得跳过去重。
- 自动通过不得跳过后续 staging/core 闸门。
- High/Forbidden 不得因为 LLM 推荐而直接放行。

### 维度 9：第二阶段初始运行配额与暂停阈值

#### 已确认决定

第二阶段小范围运行先采用保守配额，连续运行 3-5 天后再根据质量、成本和风险调整。

初始配额如下：

- 来源发现任务：每小时运行 1 次。
- 每次新增候选来源：20-50 条。
- 每日新增候选来源上限：300-500 条。
- 每日进入自动抽取来源：100-200 条。
- High 风险待审来源：每日 20-50 条。
- 单渠道连续失败 3 次：自动暂停该渠道计划。
- 单渠道出现 1 次投诉、封禁、验证码异常、平台限制或疑似违规事件：进入人工复核。

#### 专业建议

- 先限制吞吐，而不是追求最大采集量。第二阶段的核心目标是验证“来源发现 -> 审核 -> 抽取 -> 分级 -> 入库 -> 审计”链路是否稳定。
- 每日进入自动抽取的来源数量应小于每日候选来源数量，保留人工审核和风险过滤空间。
- High 风险来源只做候选发现和人工审核，不直接进入自动抽取；审核通过后也只允许只读抽取，不自动触达。
- 3-5 天后按以下指标调整配额：
  - B/C 级线索比例。
  - 重复率。
  - 失败率。
  - LLM 成本。
  - 人工审核压力。
  - 风险事件数。

#### 调整规则建议

- 若 B 级线索比例低于 20%，应优先调整关键词、渠道计划和来源质量规则，而不是盲目提高采集量。
- 若重复率高于 30%，应优先增强来源去重、域名归并和相似来源识别。
- 若单渠道失败率连续两天高于 50%，应暂停该渠道并进入复盘。
- 若人工审核积压超过 300 条，应降低 High/Medium 来源发现配额。
- 若 LLM 成本超预算，应优先减少页面长文本输入和重复来源重跑。

### 维度 10：Agent 任务状态机与失败重试规则

#### 已确认决定

第二阶段所有 Agent 任务采用统一任务状态机：

```text
pending -> running -> succeeded
        -> failed -> retry_pending -> running
        -> paused
        -> cancelled
        -> manual_review_required
```

适用任务包括：

- `SOURCE_DISCOVERY`
- `SOURCE_CANDIDATE_UPSERT`
- `LEAD_EXTRACTION`
- `LEAD_GRADING`
- `RAG_CONTEXT_BUILD`
- `RETRY_WORKER`

#### 审计要求

每次任务运行必须写入 `agent_task_runs` 审计记录，至少包含：

- 任务类型。
- 任务状态。
- 输入参数。
- 输出摘要。
- LLM Provider。
- LLM 模型。
- token 用量和成本估算。
- 来源证据。
- schema 校验结果。
- 错误信息。
- 重试次数。
- 触发来源：定时、手动、系统重试。
- 创建时间、开始时间、结束时间。

#### 失败重试规则

- 单任务最多重试 3 次。
- LLM Provider 调用失败：指数退避重试。
- JSON schema 校验失败：不自动重试，进入人工复核或 prompt 修正队列。
- 来源风险异常：不重试，暂停渠道并进入人工复核。
- 数据库写入失败：允许重试。
- Forbidden 来源：直接阻断并审计，不进入重试。
- High 来源未审核通过：不进入自动抽取，不进入重试。

#### 专业建议

- 状态机应放在后端统一服务层，不要分散写在不同 worker 中。
- `agent_task_runs` 应作为第二阶段排障核心表，移动端和后台都可以读取任务运行状态。
- 自动重试只能处理技术失败，不能处理合规失败。合规失败必须人工介入。
- 每个任务都要能从审计记录还原当时的输入、输出、模型和来源证据。

### 维度 11：`lead_source_candidates` 表结构

#### 已确认决定

第二阶段新增 `lead_source_candidates`，作为 LLM Source Discovery Agent 自动发现来源的候选池。

该表不等同于正式 `lead_sources`：

- `lead_source_candidates`：未确认客户前的来源候选，面向来源发现、风险审核和自动抽取准入。
- `lead_sources`：已确认客户后的正式来源记录，关联客户实体。

#### 字段分组

1. 基础来源字段：
   - `id`
   - `source_url`
   - `normalized_domain`
   - `platform`
   - `channel_name`
   - `country`
   - `city`

2. 风险审核字段：
   - `risk_level`
   - `review_status`
   - `approved_for_extraction`
   - `reviewer_id`
   - `review_note`
   - `reviewed_at`

3. 发现证据字段：
   - `discovery_method`
   - `discovery_query`
   - `discovery_reason`
   - `evidence_note`
   - `evidence_links`

4. LLM 输出字段：
   - `llm_provider`
   - `llm_model`
   - `llm_output_json`
   - `confidence_score`

5. 队列状态字段：
   - `extraction_status`
   - `last_extracted_at`
   - `next_retry_at`
   - `retry_count`

6. 去重归并字段：
   - `dedupe_key`
   - `duplicate_of_id`
   - `is_duplicate`

7. 审计时间字段：
   - `created_at`
   - `updated_at`
   - `created_by_task_run_id`

#### 默认审核状态

- Low：`review_status=auto_approved`，`approved_for_extraction=true`。
- Medium：`review_status=auto_approved`，`approved_for_extraction=true`，但受配额和暂停规则控制。
- High：`review_status=high_risk_review`，`approved_for_extraction=false`。
- Forbidden：`review_status=rejected`，`approved_for_extraction=false`。

#### 专业建议

- `source_url` 和 `normalized_domain` 必须分开。URL 用于证据回溯，domain 用于去重和渠道统计。
- `evidence_links` 建议使用 JSONB 数组，保留多个证据链接。
- `llm_output_json` 必须保留原始 LLM 输出，不能只保存解析后的字段。
- `created_by_task_run_id` 必须关联 `agent_task_runs`，保证来源候选可追溯到具体 Agent 运行。
- `approved_for_extraction=true` 只表示允许自动抽取，不表示允许触达。

### 维度 12：Source Discovery Agent Prompt/Schema 入库与移动端页面设计

#### 已确认决定

第二阶段采用结构化 Source Discovery Agent prompt/schema，并将 prompt/schema 入库管理。

Source Discovery Agent 的职责边界：

- 只负责发现潜在线索来源。
- 不直接抽取客户。
- 不自动触达。
- 不生成私信内容。
- 不绕过登录、验证码、反爬或平台限制。
- 不把 High/Forbidden 来源直接放入自动抽取链路。

#### Source Discovery Agent 输出 Schema 方向

```json
{
  "task_type": "SOURCE_DISCOVERY",
  "country": "Russia",
  "city": "Moscow",
  "channel_strategy": "official_website_public_directory_search_engine",
  "candidates": [
    {
      "source_url": "https://example.com/dealers",
      "platform": "official_website",
      "channel_name": "dealer_directory",
      "country": "Russia",
      "city": "Moscow",
      "risk_level": "Low",
      "discovery_method": "keyword_search",
      "discovery_query": "автосалон импорт авто Москва",
      "discovery_reason": "页面公开展示车商目录，可能包含二级经销商线索",
      "evidence_note": "公开页面包含 dealer / auto sales / contact 相关信息",
      "evidence_links": ["https://example.com/dealers"],
      "confidence_score": 0.72,
      "recommended_review_status": "auto_approved",
      "approved_for_extraction": true
    }
  ],
  "blocked_candidates": [
    {
      "source_url": "https://blocked.example.com",
      "risk_level": "Forbidden",
      "blocked_reason": "需要登录或违反渠道规则"
    }
  ]
}
```

#### Schema 规则

- 缺失字段必须输出 `Unknown`、`null` 或空数组。
- 不允许编造 URL、联系方式、客户名称。
- 每条候选来源必须有 `source_url` 和 `evidence_note`。
- High 来源只能进入待审，不自动抽取。
- Forbidden 来源直接阻断并审计。
- 只输出公开来源，不输出需要登录、绕过限制、批量私信相关动作。
- 输出必须通过 JSON schema 校验后才能写入 `lead_source_candidates`。

#### Prompt/Schema 入库设计

建议新增 `llm_prompt_templates` 表，用于管理不同 Agent 的 prompt 和 schema。

核心字段：

- `id`
- `name`
- `task_type`
- `provider`
- `model`
- `system_prompt`
- `user_prompt_template`
- `output_schema_json`
- `version`
- `status`
- `is_default`
- `created_by`
- `created_at`
- `updated_at`

建议状态：

- `draft`
- `active`
- `paused`
- `archived`

专业建议：

- 每次 Agent 运行必须记录使用的 prompt template id 和版本。
- 不要只把 prompt 写在代码里，否则后续难以审计、灰度和回滚。
- Prompt 变更必须保留版本，不覆盖历史版本。
- 默认 prompt 只允许一个 active 版本，避免任务运行时不确定。

#### 移动端页面设计

第二阶段移动端新增“来源审核”功能模块，面向运营、客服主管或出口销售负责人。

页面一：来源候选队列

- 展示 `lead_source_candidates` 列表。
- 支持按风险等级筛选：Low、Medium、High、Forbidden。
- 支持按审核状态筛选：自动通过、待复核、高风险待审、已驳回、已暂停。
- 支持按国家、城市、平台、渠道筛选。
- 列表卡片展示：
  - 来源平台。
  - 来源 URL/domain。
  - 风险等级。
  - 推荐审核状态。
  - 发现理由摘要。
  - 证据摘要。
  - 最近发现时间。
  - 是否已进入抽取队列。

页面二：来源详情页

- 展示来源 URL、domain、平台、国家、城市、渠道名称。
- 展示 LLM 发现理由、关键词、证据摘要、证据链接。
- 展示风险等级、审核状态、是否允许自动抽取。
- 展示原始 LLM 输出 JSON 摘要。
- 展示关联的 `agent_task_runs` 审计信息。
- 展示历史审核记录和备注。

页面三：审核动作页/底部动作区

- 通过并进入自动抽取。
- 驳回。
- 标记高风险。
- 暂停渠道。
- 送人工二次复核。
- 添加审核备注。
- 重新触发来源发现。

页面四：Agent 手动调用页

- 选择任务类型：`SOURCE_DISCOVERY`、`LEAD_EXTRACTION`。
- 选择国家、城市、渠道策略、风险范围。
- 选择 prompt template 版本。
- 设置本次运行上限。
- 点击“启动任务”后生成 `agent_task_runs`。
- 展示任务状态、输出数量、失败原因和重试入口。

#### 调用流程

移动端手动启动 Source Discovery：

```text
移动端调用启动接口
 -> 创建 agent_task_runs
 -> 读取 active prompt/schema
 -> 调用 LLM Provider
 -> 校验 JSON schema
 -> 写入 lead_source_candidates
 -> 返回任务结果摘要
```

移动端审核通过来源：

```text
来源候选详情
 -> approve_for_extraction
 -> 更新 review_status/approved_for_extraction
 -> 若满足准入规则，进入 LEAD_EXTRACTION 队列
```

LEAD_EXTRACTION 自动消费：

```text
定时任务扫描 approved 来源
 -> 创建 LEAD_EXTRACTION agent_task_runs
 -> 抓取/读取公开来源文本
 -> 调用 LLM 抽取和分级
 -> schema 校验
 -> staging_leads/core customers 入库
 -> 审计记录
```

#### 风险边界

- 移动端“通过”只表示允许自动抽取，不表示允许自动触达。
- High 来源审核通过后也只能只读抽取，不能自动私信、加好友或批量触达。
- Prompt/schema 页面不建议第二阶段开放给普通运营编辑，先由技术/管理员维护。
- 所有手动启动任务也必须走相同审计链路，不允许绕过 `agent_task_runs`。

### 维度 13：LLM Provider 接入与 Fallback 规则

#### 已确认决定

第二阶段新增统一 `LLMClient` 抽象，默认接入 DeepSeek，并保留后续切换 OpenAI、Claude、Qwen、Gemini 等 Provider 的能力。

默认配置方向：

```env
LLM_PROVIDER=deepseek
LLM_API_KEY=sk-xxxxx
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_DEFAULT_MODEL=deepseek-chat
LLM_SOURCE_DISCOVERY_MODEL=deepseek-chat
LLM_EXTRACTION_MODEL=deepseek-chat
LLM_GRADING_MODEL=deepseek-chat
```

#### 调用审计字段

每次 LLM 调用必须记录：

- `provider`
- `model`
- `base_url`
- `prompt_template_id`
- `prompt_version`
- `input_hash`
- `output_json`
- `token_usage`
- `latency_ms`
- `error`
- `agent_task_run_id`

#### Fallback 规则

Fallback 只处理技术失败，不处理内容失败或合规失败。

```text
DeepSeek 调用成功
 -> 使用 DeepSeek 输出

DeepSeek 网络/超时/限流失败
 -> fallback 到备用 Provider

DeepSeek 输出 schema 不合法
 -> 不 fallback，进入人工复核/Prompt 修正队列

DeepSeek 输出命中风险规则
 -> 不 fallback，进入风控处理
```

#### 不允许 Fallback 的场景

- JSON schema 校验失败。
- LLM 输出疑似编造来源、客户或联系方式。
- 输出命中 Forbidden 或 High 风险阻断规则。
- 来源证据缺失。
- Prompt 模板处于 `draft`、`paused`、`archived` 状态。

#### 专业建议

- `LLMClient` 应提供统一接口，例如 `generate_json(task_type, prompt_template, variables, schema)`。
- Provider 适配层只处理协议差异，不处理业务规则。
- JSON schema 校验应放在 LLM 调用之后、业务入库之前。
- 成本、延迟、失败率需要按 Provider 和任务类型统计，作为后续模型切换依据。
- 当前 `.env` 中 LLM 配置必须修正，避免把 `LLM_API_KEY` 写成 base URL 或模型名拼写错误。

### 维度 14：自动定时调度技术选型

#### 已确认决定

第二阶段小范围运行采用：

```text
APScheduler + Redis 锁/状态 + PostgreSQL agent_task_runs
```

#### 选型理由

- 第二阶段目标是小范围运行和链路验证，不需要一开始引入 Celery 的完整复杂度。
- APScheduler 适合在 FastAPI 后端内做轻量定时任务。
- Redis 用于防止多实例重复执行、保存短期运行锁。
- PostgreSQL 作为最终审计事实来源。
- 后续任务量增大后，再评估迁移到 Celery、RQ 或 Arq。

#### 推荐定时任务

- `source_discovery_hourly`：每小时发现来源。
- `lead_extraction_interval`：每 15-30 分钟消费已审核来源。
- `retry_failed_tasks`：每 10 分钟处理可重试失败任务。
- `channel_health_check_daily`：每天复盘渠道失败率和风险事件。
- `llm_cost_rollup_daily`：每天汇总 LLM 成本。

#### 运行规则

- 单任务必须先获取 Redis lock。
- lock 过期时间必须大于任务最大运行时间。
- 任务启动必须写入 `agent_task_runs`。
- 任务结束必须更新状态。
- 服务重启后可恢复 `pending` 和 `retry_pending` 任务。
- `running` 超时任务必须标记为 `failed` 或 `retry_pending`。

#### 专业建议

- APScheduler 只负责触发任务，不承载业务状态。
- Redis lock 只负责短期互斥，不作为审计依据。
- `agent_task_runs` 是任务运行的最终事实来源。
- 第二阶段应提供开关配置，例如 `AGENT_SCHEDULER_ENABLED=true/false`，避免开发环境误触发。
- 所有自动任务必须支持手动触发同一套服务逻辑，避免“定时”和“手动”两套实现分叉。

### 本步骤双轮评审记录

#### 第一轮评审：需求一致性

结论：通过。

发现项：

- 已覆盖用户提出的“自动定时启动运行 LLM”和“所有流程串起来”要求。
- 已明确不再依赖飞书，数据通过 PostgreSQL 审计表承载。
- 已保持 High/Forbidden 风险边界。

修正结果：

- 无需修正。

#### 第二轮评审：合规与落地性

结论：通过。

发现项：

- APScheduler + Redis + PostgreSQL 适合第二阶段小范围运行，复杂度可控。
- Redis lock 没有替代 PostgreSQL 审计事实来源，符合可追溯要求。
- 已加入 `AGENT_SCHEDULER_ENABLED` 开关，降低开发环境误运行风险。

修正结果：

- 无需修正。
