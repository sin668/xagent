# Story P4-E7-S3：整理失败案例和不可重试错误

状态：待实现  
Sprint：Sprint 7  
优先级：P1  
Epic：P4-E7

## 用户故事

作为 Agent 运行质量负责人，我希望整理第四阶段失败案例和不可重试错误，以便改进错误分类、提示词、数据质量和后续迁移策略。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`
- `docs/brainstorm/brainstorming-session-2026-06-04-第四阶段小范围运行-LangGraph-Agent迁移.md`

## Story 定义

**目标：** 从 `agent_service_runs`、节点 trace 和对照报告中整理失败案例库，区分可重试和不可重试错误。

**建议文件：**

- Create: `docs/reports/phase-4/failed-cases-and-non-retryable-errors.md`
- Create/Modify: `apps/agents/app/services/error_classification.py`
- Test: `apps/agents/tests/test_failed_case_classification.py`

**验收标准：**

- 失败案例按 Agent 类型、错误类型、是否可重试分类。
- 不可重试错误包含 schema 不满足、证据缺失、Forbidden 来源、硬规则冲突等类别。
- 每类失败案例给出修正建议或后续 Story 建议。
- 不把合规硬规则失败归类为可自动重试成功的问题。

**非目标：**

- 不自动修改历史 run 状态。
- 不自动重跑失败任务。
- 不输出最终 Go/No-Go 结论。

## Codex 提示词

```text
请执行 P4-E7-S3：整理失败案例和不可重试错误。
要求报告中文；合规硬规则失败不得归类为可自动重试；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`，若仅生成报告则至少使用可复核的数据生成或校验脚本。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- 失败案例整理只用于改进，不自动恢复 Invalid、不自动重跑、不自动触达。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。
