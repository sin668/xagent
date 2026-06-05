# Story P4-E6-S1：实现 Lead Extraction 子图

状态：待实现  
Sprint：Sprint 6  
优先级：P0  
Epic：P4-E6

## 用户故事

作为 Agent 服务开发者，我希望在 `apps/agents` 中实现 Lead Extraction 子图，以便在 shadow_run 中验证结构化线索抽取质量。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 创建 Lead Extraction LangGraph 子图，输出符合 schema 的 staging lead 候选结构和证据映射。

**建议文件：**

- Create: `apps/agents/app/graphs/lead_extraction.py`
- Create: `apps/agents/app/schemas/lead_extraction.py`
- Test: `apps/agents/tests/test_lead_extraction_subgraph.py`

**验收标准：**

- 子图能从输入文本或来源内容中抽取结构化字段。
- 每个关键字段必须保留证据引用或缺失原因。
- 输出用于 shadow_run，不写 `staging_leads`。
- schema 校验失败时返回明确错误。

**非目标：**

- 不实现 Lead Grading。
- 不实现组合 API。
- 不写业务表。

## Codex 提示词

```text
请执行 P4-E6-S1：实现 Lead Extraction 子图。
要求使用 TDD；关键字段必须有证据引用或缺失原因；shadow_run 不写 staging_leads；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- Lead Extraction/Grading 第四阶段只 shadow_run。
- 不得编造联系方式或证据。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。
