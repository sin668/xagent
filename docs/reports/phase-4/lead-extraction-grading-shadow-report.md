# Lead Extraction/Grading shadow 对照报告

生成方式：由 `apps/agents` Lead Extraction/Grading shadow 样本数据生成，报告只用于第四阶段对照验证。

## 1. 结论

- 样本数：30
- 建议：No-Go：存在硬规则不一致，禁止进入 active_run。
- 本报告不等同于生产切换批准；Lead Extraction/Grading 第四阶段仍只允许 shadow_run。

## 2. 指标总览

| 指标 | 结果 | 说明 |
|---|---:|---|
| schema 通过率 | 96.67% | schema 通过样本 / 样本数 |
| 证据命中率 | 93.33% | 证据命中样本 / 样本数 |
| 联系方式反编造通过率 | 90% | 联系方式通过反编造校验 / 样本数 |
| 字段完整度 | 87.5% | 已抽取字段 / 应抽取字段 |
| 等级一致率 | 80% | shadow 等级与现有链路一致 / 样本数 |
| 硬规则一致率 | 96.67% | 硬规则分流一致 / 样本数 |
| C/Invalid/Watch 分流准确性 | 96.67% | C/Invalid/Watch 分流正确 / 样本数 |
| 硬规则不一致数 | 1 | 必须列为阻塞问题 |

## 3. 主要差异

### 等级差异

| 差异类型 | 样本 | 可解释原因 | 处理建议 |
|---|---|---|---|
| 等级差异 | LEG-05 | 现有链路为 B，shadow 因出口意向和车型兴趣建议 A。 | 复核评分权重，确认 A 级阈值是否过宽。 |
| 等级差异 | LEG-09 | 现有链路为 C，shadow 因联系方式完整建议 B。 | 检查现有链路是否漏计联系方式完整性。 |
| 等级差异 | LEG-14 | 现有链路为 B，shadow 因证据较弱建议 C。 | 要求补充公开证据后再比较等级。 |
| 等级差异 | LEG-27 | 现有链路为 Watch，shadow 建议 C。 | 复核 Watch/Invalid 历史状态分流规则。 |

### 硬规则不一致

| 差异类型 | 样本 | 可解释原因 | 处理建议 |
|---|---|---|---|
| 硬规则不一致 | LEG-17 | shadow 未按 Forbidden 规则分流到 Invalid/risk_blocked。 | 作为阻塞问题处理，修正硬规则后才能考虑 active_run。 |

### 证据/联系方式差异

| 差异类型 | 样本 | 可解释原因 | 处理建议 |
|---|---|---|---|
| 证据/联系方式差异 | LEG-19 | shadow 部分字段证据命中不足。 | 补充证据命中校验样本，证据不足字段不得自动采纳。 |
| 证据/联系方式差异 | LEG-22 | shadow 联系方式反编造校验失败。 | 联系方式必须出现在公开来源文本中，否则标记无效。 |
| 证据/联系方式差异 | LEG-28 | shadow 电话未在来源文本中命中。 | 保持无效联系方式标记，不得写入 staging_leads。 |

## 4. 风险与处理建议

- 硬规则不一致必须作为阻塞问题处理，修正前不得进入 active_run。
- 联系方式必须在公开来源文本中命中，否则标记为无效联系方式。
- schema 或证据不足样本不得自动写入 `staging_leads`。
- 等级差异必须保留可解释原因，不得只输出等级结论。

## 5. 样本明细

| 样本 | 差异类型 | 现有等级 | shadow 等级 | 状态分流 | schema 通过 | 证据命中 | 反编造通过 | 硬规则一致 | 分流准确 | 原因 | 处理建议 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| LEG-01 | 一致 | B | B | ready_for_manual_review | 是 | 是 | 是 | 是 | 是 | 现有链路与 shadow 抽取分级基本一致。 | 继续纳入样本观察。 |
| LEG-02 | 一致 | B | B | ready_for_manual_review | 是 | 是 | 是 | 是 | 是 | 现有链路与 shadow 抽取分级基本一致。 | 继续纳入样本观察。 |
| LEG-03 | 一致 | B | B | ready_for_manual_review | 是 | 是 | 是 | 是 | 是 | 现有链路与 shadow 抽取分级基本一致。 | 继续纳入样本观察。 |
| LEG-04 | 一致 | B | B | ready_for_manual_review | 否 | 是 | 是 | 是 | 是 | 现有链路与 shadow 抽取分级基本一致。 | 继续纳入样本观察。 |
| LEG-05 | 等级差异 | B | B | ready_for_manual_review | 是 | 是 | 是 | 是 | 是 | 现有链路为 B，shadow 因出口意向和车型兴趣建议 A。 | 复核评分权重，确认 A 级阈值是否过宽。 |
| LEG-06 | 一致 | B | B | ready_for_manual_review | 是 | 是 | 是 | 是 | 是 | 现有链路与 shadow 抽取分级基本一致。 | 继续纳入样本观察。 |
| LEG-07 | 一致 | B | B | ready_for_manual_review | 是 | 是 | 是 | 是 | 是 | 现有链路与 shadow 抽取分级基本一致。 | 继续纳入样本观察。 |
| LEG-08 | 一致 | B | B | ready_for_manual_review | 是 | 否 | 是 | 是 | 是 | 现有链路与 shadow 抽取分级基本一致。 | 继续纳入样本观察。 |
| LEG-09 | 等级差异 | B | B | ready_for_manual_review | 是 | 是 | 是 | 是 | 是 | 现有链路为 C，shadow 因联系方式完整建议 B。 | 检查现有链路是否漏计联系方式完整性。 |
| LEG-10 | 一致 | B | B | ready_for_manual_review | 是 | 是 | 是 | 是 | 是 | 现有链路与 shadow 抽取分级基本一致。 | 继续纳入样本观察。 |
| LEG-11 | 一致 | B | B | ready_for_manual_review | 是 | 是 | 否 | 是 | 是 | 现有链路与 shadow 抽取分级基本一致。 | 继续纳入样本观察。 |
| LEG-12 | 一致 | B | B | ready_for_manual_review | 是 | 是 | 是 | 是 | 是 | 现有链路与 shadow 抽取分级基本一致。 | 继续纳入样本观察。 |
| LEG-13 | 一致 | B | B | ready_for_manual_review | 是 | 是 | 是 | 是 | 是 | 现有链路与 shadow 抽取分级基本一致。 | 继续纳入样本观察。 |
| LEG-14 | 等级差异 | B | B | ready_for_manual_review | 是 | 是 | 是 | 是 | 是 | 现有链路为 B，shadow 因证据较弱建议 C。 | 要求补充公开证据后再比较等级。 |
| LEG-15 | 一致 | B | B | ready_for_manual_review | 是 | 是 | 是 | 是 | 是 | 现有链路与 shadow 抽取分级基本一致。 | 继续纳入样本观察。 |
| LEG-16 | 一致 | B | B | ready_for_manual_review | 是 | 是 | 是 | 是 | 是 | 现有链路与 shadow 抽取分级基本一致。 | 继续纳入样本观察。 |
| LEG-17 | 硬规则不一致 | Invalid | B | ready_for_manual_review | 是 | 是 | 是 | 否 | 否 | shadow 未按 Forbidden 规则分流到 Invalid/risk_blocked。 | 作为阻塞问题处理，修正硬规则后才能考虑 active_run。 |
| LEG-18 | 一致 | B | B | ready_for_manual_review | 是 | 是 | 是 | 是 | 是 | 现有链路与 shadow 抽取分级基本一致。 | 继续纳入样本观察。 |
| LEG-19 | 证据/联系方式差异 | B | B | ready_for_manual_review | 是 | 否 | 是 | 是 | 是 | shadow 部分字段证据命中不足。 | 补充证据命中校验样本，证据不足字段不得自动采纳。 |
| LEG-20 | 一致 | B | B | ready_for_manual_review | 是 | 是 | 是 | 是 | 是 | 现有链路与 shadow 抽取分级基本一致。 | 继续纳入样本观察。 |
| LEG-21 | 一致 | B | B | ready_for_manual_review | 是 | 是 | 是 | 是 | 是 | 现有链路与 shadow 抽取分级基本一致。 | 继续纳入样本观察。 |
| LEG-22 | 证据/联系方式差异 | B | B | ready_for_manual_review | 是 | 是 | 否 | 是 | 是 | shadow 联系方式反编造校验失败。 | 联系方式必须出现在公开来源文本中，否则标记无效。 |
| LEG-23 | 一致 | B | B | ready_for_manual_review | 是 | 是 | 是 | 是 | 是 | 现有链路与 shadow 抽取分级基本一致。 | 继续纳入样本观察。 |
| LEG-24 | 一致 | B | B | ready_for_manual_review | 是 | 是 | 是 | 是 | 是 | 现有链路与 shadow 抽取分级基本一致。 | 继续纳入样本观察。 |
| LEG-25 | 一致 | B | B | ready_for_manual_review | 是 | 是 | 是 | 是 | 是 | 现有链路与 shadow 抽取分级基本一致。 | 继续纳入样本观察。 |
| LEG-26 | 一致 | B | B | ready_for_manual_review | 是 | 是 | 是 | 是 | 是 | 现有链路与 shadow 抽取分级基本一致。 | 继续纳入样本观察。 |
| LEG-27 | 等级差异 | B | B | ready_for_manual_review | 是 | 是 | 是 | 是 | 是 | 现有链路为 Watch，shadow 建议 C。 | 复核 Watch/Invalid 历史状态分流规则。 |
| LEG-28 | 证据/联系方式差异 | B | B | ready_for_manual_review | 是 | 是 | 否 | 是 | 是 | shadow 电话未在来源文本中命中。 | 保持无效联系方式标记，不得写入 staging_leads。 |
| LEG-29 | 一致 | B | B | ready_for_manual_review | 是 | 是 | 是 | 是 | 是 | 现有链路与 shadow 抽取分级基本一致。 | 继续纳入样本观察。 |
| LEG-30 | 一致 | B | B | ready_for_manual_review | 是 | 是 | 是 | 是 | 是 | 现有链路与 shadow 抽取分级基本一致。 | 继续纳入样本观察。 |
