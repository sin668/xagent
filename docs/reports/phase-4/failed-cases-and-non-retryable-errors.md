# 第四阶段失败案例与不可重试错误整理

生成方式：汇总 `agent_service_runs`、节点 trace、Source Discovery 对照报告和 Lead Extraction/Grading 对照报告中的失败信号，按 Agent 类型、错误类型、是否可重试分类。

## 1. 范围说明

- 失败案例数：7
- 涉及 Agent：Deep Enrichment, Lead Cleanup, Lead Extraction, Lead Grading, Source Discovery
- 可重试案例数：2
- 不可重试案例数：5
- 本报告不自动修改历史 run 状态。
- 本报告不自动重跑失败任务。
- 本报告不输出最终 Go/No-Go 结论；最终结论由 P4-E7-S4 汇总。
- 合规硬规则失败不得归类为可自动重试成功的问题。

## 2. 不可重试错误类别

| 类别 | error_type | 处理原则 |
|---|---|---|
| schema 不满足 | `schema_validation_error` | 修正 schema validator、prompt 输出格式或输入数据后再进入 shadow；不得靠自动重试视为成功。 |
| 证据缺失 | `evidence_validation_error` | 缺少公开证据命中的字段不得自动采纳，必须补充证据或缺失原因。 |
| Forbidden 来源 | `forbidden_source_error`、`risk_blocked` | Forbidden 或高风险来源必须硬阻断，修正过滤规则前不得进入 active_run。 |
| 硬规则冲突 | `hard_rule_conflict`、`contract_mismatch` | 合规硬规则优先级高于 LLM 判断，冲突时不得自动重试绕过。 |

## 3. 分类总览

| Agent | 错误类型 | 类别 | 是否可重试 | 案例 | 来源 |
|---|---|---|---|---|---|
| Source Discovery | `forbidden_source_error` | Forbidden 来源 | 否 | FC-SD-001 | docs/reports/phase-4/source-discovery-shadow-report.md#SD-17 |
| Lead Extraction | `schema_validation_error` | schema 不满足 | 否 | FC-LE-001 | docs/reports/phase-4/lead-extraction-grading-shadow-report.md#LEG-04 |
| Lead Extraction | `evidence_validation_error` | 证据缺失 | 否 | FC-LE-002 | docs/reports/phase-4/lead-extraction-grading-shadow-report.md#LEG-19 |
| Lead Extraction | `evidence_validation_error` | 证据缺失 | 否 | FC-LE-003 | docs/reports/phase-4/lead-extraction-grading-shadow-report.md#LEG-22 |
| Lead Grading | `hard_rule_conflict` | 硬规则冲突 | 否 | FC-LG-001 | docs/reports/phase-4/lead-extraction-grading-shadow-report.md#LEG-17 |
| Deep Enrichment | `provider_rate_limited` | 外部服务暂态失败 | 是 | FC-DE-001 | agent_service_runs retry policy |
| Lead Cleanup | `timeout_error` | 外部服务暂态失败 | 是 | FC-LC-001 | agent_service_runs retry policy |

## 4. 失败案例明细

### FC-SD-001：Source Discovery / Forbidden 来源

- 错误类型：`forbidden_source_error`
- 是否可重试：否
- 来源：`docs/reports/phase-4/source-discovery-shadow-report.md#SD-17`
- 现象：shadow 将登录墙来源输出为有效候选。
- 根因判断：Forbidden 过滤节点未在候选输出前形成硬阻断。
- 修正建议：不可自动重试；先修正 Forbidden 过滤和风险阻断规则，再重新进入 shadow 对照。
- 后续建议：后续 Story：补充 Forbidden 来源回归样本和阻断规则验收。

### FC-LE-001：Lead Extraction / schema 不满足

- 错误类型：`schema_validation_error`
- 是否可重试：否
- 来源：`docs/reports/phase-4/lead-extraction-grading-shadow-report.md#LEG-04`
- 现象：抽取结果缺少必填字段或字段类型不满足 schema。
- 根因判断：LLM 输出未完全遵守结构化契约，且缺少 schema 修复前置校验。
- 修正建议：不可自动重试成功；先收紧 schema validator 和 prompt 输出格式，再人工复核失败样本。
- 后续建议：后续 Story：增加结构化输出修复提示词和 schema 回归集。

### FC-LE-002：Lead Extraction / 证据缺失

- 错误类型：`evidence_validation_error`
- 是否可重试：否
- 来源：`docs/reports/phase-4/lead-extraction-grading-shadow-report.md#LEG-19`
- 现象：字段有抽取值，但缺少公开来源证据命中。
- 根因判断：证据引用节点未能拒绝弱证据字段。
- 修正建议：不可自动重试；证据不足字段不得自动采纳，需补充来源文本命中或缺失原因。
- 后续建议：后续 Story：扩充证据命中校验样本并强化字段级缺失原因。

### FC-LE-003：Lead Extraction / 证据缺失

- 错误类型：`evidence_validation_error`
- 是否可重试：否
- 来源：`docs/reports/phase-4/lead-extraction-grading-shadow-report.md#LEG-22`
- 现象：联系方式反编造校验失败。
- 根因判断：联系方式未在公开来源文本中命中。
- 修正建议：不可自动重试；联系方式必须保留无效标记，不得写入 staging_leads。
- 后续建议：后续 Story：增加联系方式反编造负样本和来源定位提示。

### FC-LG-001：Lead Grading / 硬规则冲突

- 错误类型：`hard_rule_conflict`
- 是否可重试：否
- 来源：`docs/reports/phase-4/lead-extraction-grading-shadow-report.md#LEG-17`
- 现象：shadow 未按 Forbidden 规则分流到 Invalid/risk_blocked。
- 根因判断：LLM 分级结论覆盖了合规硬规则。
- 修正建议：不可自动重试；合规硬规则失败不得归类为可自动重试成功的问题，必须先修正硬规则优先级。
- 后续建议：后续 Story：补充硬规则优先级回归和 risk_blocked 分流审计。

### FC-DE-001：Deep Enrichment / 外部服务暂态失败

- 错误类型：`provider_rate_limited`
- 是否可重试：是
- 来源：`agent_service_runs retry policy`
- 现象：字段候选生成期间 LLM provider 返回限流。
- 根因判断：外部 provider 临时容量限制。
- 修正建议：可按 retry policy 自动重试；不得绕过人工审核写入字段候选。
- 后续建议：后续 Story：观察 provider 限流频率，必要时调整并发和退避参数。

### FC-LC-001：Lead Cleanup / 外部服务暂态失败

- 错误类型：`timeout_error`
- 是否可重试：是
- 来源：`agent_service_runs retry policy`
- 现象：清洗建议生成超时。
- 根因判断：LLM 请求或上游网络暂态超时。
- 修正建议：可按 retry policy 自动重试；不得自动归并、自动恢复 Invalid 或自动触达。
- 后续建议：后续 Story：观察超时节点和输入规模，必要时拆分清洗建议生成。

## 5. 使用边界

- 失败案例整理只用于改进错误分类、提示词、数据质量和后续迁移策略。
- 不自动恢复 Invalid、不自动重跑、不自动触达。
- 不自动晋级、不自动归并、不自动调整 Agent 开关。
- 可重试仅限暂态 provider、限流或网络类错误；schema、证据、Forbidden、硬规则冲突均按不可重试处理。
