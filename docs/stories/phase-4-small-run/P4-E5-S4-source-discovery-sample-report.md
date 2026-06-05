# Story P4-E5-S4：输出 Source Discovery 30-50 条样本对照报告

状态：待实现  
Sprint：Sprint 5  
优先级：P1  
Epic：P4-E5

## 用户故事

作为第四阶段验收负责人，我希望基于 30-50 条样本输出 Source Discovery 对照报告，以便决定该 Agent 是否可从 shadow_run 进入后续 active_run。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 汇总 Source Discovery shadow 样本指标、典型差异和 Go/No-Go 建议。

**建议文件：**

- Create: `docs/reports/phase-4/source-discovery-shadow-report.md`
- Create/Modify: `apps/agents/scripts/` 或项目现有报告脚本
- Test: `apps/agents/tests/test_source_discovery_report_generation.py`

**验收标准：**

- 报告覆盖 30-50 条样本。
- 报告包含 URL 有效率、重复率、风险分级一致率、证据完整率。
- Forbidden 误放数必须明确列出。
- 每类主要差异至少给出可解释原因和处理建议。

**非目标：**

- 不切换 Source Discovery 到 active_run。
- 不修改业务数据。
- 不生成 P4 总体 Go/No-Go 报告。

## Codex 提示词

```text
请执行 P4-E5-S4：输出 Source Discovery 30-50 条样本对照报告。
要求报告中文；指标必须覆盖 URL 有效率、重复率、风险分级一致率、证据完整率和 Forbidden 误放；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`，若仅生成报告则至少使用可复核的数据生成或校验脚本。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- Source Discovery 第四阶段只 shadow_run。
- 报告不得被等同于生产切换批准。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。
