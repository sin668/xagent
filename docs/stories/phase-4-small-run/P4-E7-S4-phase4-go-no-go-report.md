# Story P4-E7-S4：输出第四阶段 Go/No-Go 报告

状态：待实现  
Sprint：Sprint 7  
优先级：P1  
Epic：P4-E7

## 用户故事

作为项目负责人，我希望输出第四阶段 Go/No-Go 报告，以便决定哪些 Agent 继续 active，哪些保持 shadow，以及下一阶段是否开始废弃 `apps/api` retry worker。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`
- `docs/brainstorm/brainstorming-session-2026-06-04-第四阶段小范围运行-LangGraph-Agent迁移.md`

## Story 定义

**目标：** 汇总第四阶段运行结果、样本指标、失败案例和风险评估，形成中文 Go/No-Go 决策报告。

**建议文件：**

- Create: `docs/reports/phase-4/phase4-go-no-go-report.md`
- Modify: `docs/stories/phase-4-small-run/README.md`
- Test/Verify: 报告数据来源校验脚本或人工复核记录

**验收标准：**

- 报告能回答哪些 Agent 可以继续 active。
- 报告能回答 Source Discovery 是否可从 shadow 进入 active。
- 报告能回答 Lead Extraction/Grading 是否具备切换条件。
- 报告明确下一阶段是否开始废弃 `apps/api` retry worker。
- 报告列出阻塞风险、非阻塞风险和后续 Epic/Story 建议。

**非目标：**

- 不执行生产切换。
- 不删除 `apps/api` retry worker。
- 不自动调整任何 Agent 开关。

## Codex 提示词

```text
请执行 P4-E7-S4：输出第四阶段 Go/No-Go 报告。
要求报告中文；必须基于样本指标、失败案例和两轮评审记录；不得执行生产切换或删除 retry worker；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- Go/No-Go 报告只形成决策建议，不自动执行切换。
- `apps/api` retry worker 后续废弃必须作为独立阶段或独立 Story。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。
