# Story P4-E7-S2：统计第四阶段样本指标

状态：待实现  
Sprint：Sprint 7  
优先级：P1  
Epic：P4-E7

## 用户故事

作为第四阶段验收负责人，我希望统一统计各 Agent 的小范围运行指标，以便基于数据判断哪些 Agent 可以继续 active，哪些需要继续 shadow 或回退。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 汇总 Source Discovery、Lead Extraction、Lead Grading、Deep Enrichment、Lead Cleanup 的第四阶段样本指标。

**建议文件：**

- Create: `docs/reports/phase-4/phase4-sample-metrics.md`
- Create/Modify: `apps/agents/scripts/phase4_metrics.py`
- Test: `apps/agents/tests/test_phase4_metrics.py`

**验收标准：**

- 指标覆盖 Source Discovery 的 URL 有效率、重复率、风险分级一致率、证据完整率。
- 指标覆盖 Lead Extraction 的 schema 通过率、证据命中率、联系方式反编造通过率、字段完整度。
- 指标覆盖 Lead Grading 的等级一致率、硬规则一致率、C/Invalid/Watch 分流准确性。
- 指标覆盖 Deep Enrichment 的字段候选有效率、人工接受率、无证据候选率。
- 指标覆盖 Lead Cleanup 的重复建议准确率、错误合并建议数、人工拒绝率。

**非目标：**

- 不输出最终 Go/No-Go 结论。
- 不修改业务数据。
- 不自动调整 Agent 开关。

## Codex 提示词

```text
请执行 P4-E7-S2：统计第四阶段样本指标。
要求报告中文；指标必须覆盖五类 Agent 的方案指标；不得自动调整业务开关；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`，若仅生成报告则至少使用可复核的数据生成或校验脚本。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- 指标只用于阶段评估，不自动驱动生产切换。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。
