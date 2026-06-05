# 第四阶段 Go/No-Go 决策报告

生成方式：基于第四阶段样本指标、失败案例、观测摘要和 P4-E7 两轮独立评审记录形成决策建议。

## 1. 决策摘要

- Deep Enrichment：Go，继续小范围 active_run。
- Lead Cleanup：Go，继续小范围 active_run。
- Source Discovery：No-Go，保持 shadow_run。
- Lead Extraction/Grading：No-Go，保持 shadow_run。
- `apps/api` retry worker：No-Go，下一阶段暂不开始废弃。

## 2. 依据来源

- `docs/reports/phase-4/agent-observability-summary.md`
- `docs/reports/phase-4/phase4-sample-metrics.md`
- `docs/reports/phase-4/failed-cases-and-non-retryable-errors.md`
- `docs/reports/phase-4/source-discovery-shadow-report.md`
- `docs/reports/phase-4/lead-extraction-grading-shadow-report.md`
- `docs/stories/phase-4-small-run/P4-E7-S1-agent-observability-summary.md` 的两轮独立评审记录
- `docs/stories/phase-4-small-run/P4-E7-S2-phase4-sample-metrics.md` 的两轮独立评审记录
- `docs/stories/phase-4-small-run/P4-E7-S3-failed-cases-non-retryable-errors.md` 的两轮独立评审记录

## 3. 分 Agent 决策

| 对象 | 决策 | 主要依据 | 下一步 |
|---|---|---|---|
| Deep Enrichment | Go：继续小范围 active_run | 第四阶段 active_run 只输出字段候选，仍由 apps/api 人工审核后写入；样本指标显示无证据候选率为 0%。 | 继续小范围运行，重点观察人工接受率、无证据候选和 provider 暂态失败。 |
| Lead Cleanup | Go：继续小范围 active_run | 第四阶段 active_run 只输出清洗建议，不自动归并、不自动恢复 Invalid；样本指标显示错误合并建议数为 0。 | 继续小范围运行，重点观察重复建议准确率、人工拒绝率和超时案例。 |
| Source Discovery | No-Go：保持 shadow_run | Source Discovery 30 条 shadow 样本存在 Forbidden 误放，来源发现仍不得进入 active_run。 | 补充 Forbidden 来源回归样本，修正过滤和风险阻断规则后再做更大样本 shadow。 |
| Lead Extraction/Grading | No-Go：保持 shadow_run | Lead Extraction/Grading 30 条 shadow 样本存在硬规则不一致，且联系方式和证据仍有失败案例。 | 强化硬规则优先级、证据命中和联系方式反编造后，再做 shadow 对照复核。 |
| `apps/api` retry worker | No-Go：下一阶段暂不开始废弃 | Source Discovery 与 Lead Extraction/Grading 尚未具备切换条件，且第四阶段仍需保留 apps/api 临时兼容摘要和既有 retry worker。 | 待核心链路 shadow 阻塞风险解除、active_run 覆盖面扩大并完成独立迁移 Story 后，再规划废弃。 |

## 4. 阻塞风险

- Source Discovery 存在 Forbidden 误放，修正过滤规则前不得进入 active_run。
- Lead Extraction/Grading 存在硬规则不一致，合规硬规则优先级必须高于 LLM 判断。
- 证据缺失和联系方式反编造失败仍存在，字段或联系方式不得自动写入业务表。
- 当前阶段不具备废弃 `apps/api` retry worker 的条件。

## 5. 非阻塞风险

- Deep Enrichment 存在 provider 限流类暂态失败，可按 retry policy 重试，但不得绕过人工审核。
- Lead Cleanup 存在超时类暂态失败，可按 retry policy 重试，但不得自动归并或恢复 Invalid。
- 当前沙箱环境无法完成真实端口绑定联调，已使用 TestClient、契约测试、服务测试和报告生成脚本替代验证。

## 6. 后续 Epic/Story 建议

- 新增 Source Discovery Forbidden 来源回归与阻断规则强化 Story。
- 新增 Lead Extraction/Grading 硬规则优先级、证据命中和联系方式反编造强化 Story。
- 新增 Deep Enrichment / Lead Cleanup 小范围 active_run 运行周报和人工审核指标复核 Story。
- 在核心链路 shadow 阻塞风险解除后，再新增 `apps/api` retry worker 废弃设计与迁移 Story。

## 7. 执行边界

- 本报告只形成决策建议，不得执行生产切换。
- 本报告不得删除 `apps/api` retry worker。
- 本报告不得自动调整任何 Agent 开关。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。
