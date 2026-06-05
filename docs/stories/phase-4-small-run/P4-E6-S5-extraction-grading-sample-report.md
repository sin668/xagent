# Story P4-E6-S5：输出 Lead Extraction/Grading 30-50 条样本对照报告

状态：待实现  
Sprint：Sprint 6  
优先级：P1  
Epic：P4-E6

## 用户故事

作为第四阶段验收负责人，我希望基于 30-50 条样本输出 Lead Extraction/Grading 对照报告，以便判断抽取和分级组合图是否具备后续切换条件。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 汇总 Lead Extraction/Grading shadow 样本指标、硬规则一致性、等级差异和 Go/No-Go 建议。

**建议文件：**

- Create: `docs/reports/phase-4/lead-extraction-grading-shadow-report.md`
- Create/Modify: `apps/agents/scripts/` 或项目现有报告脚本
- Test: `apps/agents/tests/test_extraction_grading_report_generation.py`

**验收标准：**

- 报告覆盖 30-50 条样本。
- 报告包含 schema 通过率、证据命中率、联系方式反编造通过率、字段完整度。
- 报告包含等级一致率、硬规则一致率、C/Invalid/Watch 分流准确性。
- 硬规则不一致必须列为阻塞问题。
- 等级差异必须可解释。

**非目标：**

- 不切换 Lead Extraction/Grading 到 active_run。
- 不修改业务数据。
- 不生成 P4 总体 Go/No-Go 报告。

## Codex 提示词

```text
请执行 P4-E6-S5：输出 Lead Extraction/Grading 30-50 条样本对照报告。
要求报告中文；指标必须覆盖 schema、证据、联系方式反编造、等级一致率和硬规则一致率；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`，若仅生成报告则至少使用可复核的数据生成或校验脚本。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- Lead Extraction/Grading 第四阶段只 shadow_run。
- 报告不得被等同于生产切换批准。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。
