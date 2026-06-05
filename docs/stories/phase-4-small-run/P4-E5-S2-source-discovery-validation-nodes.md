# Story P4-E5-S2：实现来源归一化、风险分级、去重、证据校验节点

状态：待实现  
Sprint：Sprint 5  
优先级：P0  
Epic：P4-E5

## 用户故事

作为 Source Discovery shadow_run 的质量负责人，我希望 LangGraph 中有明确的来源归一化、风险分级、去重和证据校验节点，以便对照结果可解释且不会放过 Forbidden 来源。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 在 Source Discovery graph 中实现质量与合规校验节点，并将节点执行摘要写入 run audit。

**建议文件：**

- Modify: `apps/agents/app/graphs/source_discovery.py`
- Modify: `apps/agents/app/schemas/source_discovery.py`
- Test: `apps/agents/tests/test_source_discovery_validation_nodes.py`

**验收标准：**

- 来源 URL 归一化规则可测试。
- 重复 URL 或等价来源可被识别并标记。
- 风险分级覆盖 allowed、watch、high、forbidden 或项目约定等价级别。
- 缺少证据的候选不得进入有效候选列表。
- `audit_json.executed_nodes` 能体现关键节点执行结果摘要。

**非目标：**

- 不写业务表。
- 不做样本报告。
- 不切换现有 Source Discovery 入口。

## Codex 提示词

```text
请执行 P4-E5-S2：实现来源归一化、风险分级、去重、证据校验节点。
要求使用 TDD；Forbidden 误放必须为 0；shadow_run 不写业务表；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- Source Discovery 第四阶段只 shadow_run。
- Forbidden、High 风险、非公开数据不得被误放。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。
