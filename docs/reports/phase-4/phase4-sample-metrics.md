# 第四阶段小范围运行样本指标汇总

生成方式：汇总第四阶段各 Agent shadow/active 小范围运行样本指标，仅用于阶段评估。

## 1. 范围说明

- Agent 数量：5
- 样本总数：130
- 本报告不输出最终 Go/No-Go 结论；最终结论由 P4-E7-S4 汇总。
- 指标只用于阶段评估，不自动调整 Agent 开关。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。

## 2. 指标总览

| Agent | 样本数 | 指标 | 结果 | 来源 |
|---|---:|---|---:|---|
| Source Discovery | 30 | URL 有效率 | 90% | docs/reports/phase-4/source-discovery-shadow-report.md |
| Source Discovery | 30 | 重复率 | 10% | docs/reports/phase-4/source-discovery-shadow-report.md |
| Source Discovery | 30 | 风险分级一致率 | 80% | docs/reports/phase-4/source-discovery-shadow-report.md |
| Source Discovery | 30 | 证据完整率 | 90% | docs/reports/phase-4/source-discovery-shadow-report.md |
| Lead Extraction | 30 | schema 通过率 | 96.67% | docs/reports/phase-4/lead-extraction-grading-shadow-report.md |
| Lead Extraction | 30 | 证据命中率 | 93.33% | docs/reports/phase-4/lead-extraction-grading-shadow-report.md |
| Lead Extraction | 30 | 联系方式反编造通过率 | 90% | docs/reports/phase-4/lead-extraction-grading-shadow-report.md |
| Lead Extraction | 30 | 字段完整度 | 87.5% | docs/reports/phase-4/lead-extraction-grading-shadow-report.md |
| Lead Grading | 30 | 等级一致率 | 80% | docs/reports/phase-4/lead-extraction-grading-shadow-report.md |
| Lead Grading | 30 | 硬规则一致率 | 96.67% | docs/reports/phase-4/lead-extraction-grading-shadow-report.md |
| Lead Grading | 30 | C/Invalid/Watch 分流准确性 | 96.67% | docs/reports/phase-4/lead-extraction-grading-shadow-report.md |
| Deep Enrichment | 20 | 字段候选有效率 | 92% | docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md |
| Deep Enrichment | 20 | 人工接受率 | 78% | docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md |
| Deep Enrichment | 20 | 无证据候选率 | 0% | docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md |
| Lead Cleanup | 20 | 重复建议准确率 | 88% | docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md |
| Lead Cleanup | 20 | 错误合并建议数 | 0 | docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md |
| Lead Cleanup | 20 | 人工拒绝率 | 12% | docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md |

## 3. 分 Agent 说明

### Source Discovery

- 样本数：30
- 来源：`docs/reports/phase-4/source-discovery-shadow-report.md`
- 说明：来自 Source Discovery shadow 30 条样本对照报告。

| 指标 | 结果 |
|---|---:|
| URL 有效率 | 90% |
| 重复率 | 10% |
| 风险分级一致率 | 80% |
| 证据完整率 | 90% |

### Lead Extraction

- 样本数：30
- 来源：`docs/reports/phase-4/lead-extraction-grading-shadow-report.md`
- 说明：来自 Lead Extraction/Grading shadow 30 条样本对照报告中的抽取指标。

| 指标 | 结果 |
|---|---:|
| schema 通过率 | 96.67% |
| 证据命中率 | 93.33% |
| 联系方式反编造通过率 | 90% |
| 字段完整度 | 87.5% |

### Lead Grading

- 样本数：30
- 来源：`docs/reports/phase-4/lead-extraction-grading-shadow-report.md`
- 说明：来自 Lead Extraction/Grading shadow 30 条样本对照报告中的分级指标。

| 指标 | 结果 |
|---|---:|
| 等级一致率 | 80% |
| 硬规则一致率 | 96.67% |
| C/Invalid/Watch 分流准确性 | 96.67% |

### Deep Enrichment

- 样本数：20
- 来源：`docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`
- 说明：第四阶段小范围运行基线样本指标；后续由 P4-E7-S4 总结报告统一评估。

| 指标 | 结果 |
|---|---:|
| 字段候选有效率 | 92% |
| 人工接受率 | 78% |
| 无证据候选率 | 0% |

### Lead Cleanup

- 样本数：20
- 来源：`docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`
- 说明：第四阶段小范围运行基线样本指标；后续由 P4-E7-S4 总结报告统一评估。

| 指标 | 结果 |
|---|---:|
| 重复建议准确率 | 88% |
| 错误合并建议数 | 0 |
| 人工拒绝率 | 12% |

## 4. 使用边界

- 本报告只汇总样本指标，不输出最终 Go/No-Go 结论。
- 本报告不修改业务数据，不自动调整 Agent 开关。
- Deep Enrichment 与 Lead Cleanup 指标为第四阶段小范围运行基线口径，后续需在 P4-E7-S4 中结合失败案例和人工审核结果复核。
