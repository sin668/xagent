# Story P4-E6-S2：实现 Lead Grading 子图

状态：待实现  
Sprint：Sprint 6  
优先级：P0  
Epic：P4-E6

## 用户故事

作为 Agent 服务开发者，我希望在 `apps/agents` 中实现 Lead Grading 子图，以便对抽取结果进行可解释的等级、状态和合规分流。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 创建 Lead Grading LangGraph 子图，基于结构化线索、证据和硬规则输出等级建议与解释。

**建议文件：**

- Create: `apps/agents/app/graphs/lead_grading.py`
- Create: `apps/agents/app/schemas/lead_grading.py`
- Test: `apps/agents/tests/test_lead_grading_subgraph.py`

**验收标准：**

- 子图输出等级、状态分流、原因和触发规则。
- High/Forbidden、勿扰、C 级合规复核、Invalid/Watch 等硬规则不得被绕过。
- 等级差异必须包含可解释原因。
- 输出用于 shadow_run，不自动晋级客户。

**非目标：**

- 不实现 Lead Extraction。
- 不实现组合 API。
- 不写业务表。

## Codex 提示词

```text
请执行 P4-E6-S2：实现 Lead Grading 子图。
要求使用 TDD；硬规则必须优先于 LLM 判断；不得自动晋级客户；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- Lead Extraction/Grading 第四阶段只 shadow_run。
- High/Forbidden、勿扰、C 级合规复核、证据校验等硬规则不得被 LangGraph 绕过。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。
