# Story P4-E6-S3：实现组合 API /agent-runs/lead-extraction-grading

状态：待实现  
Sprint：Sprint 6  
优先级：P0  
Epic：P4-E6

## 用户故事

作为 `apps/api` 的调用方，我希望通过一个组合 API 触发 Lead Extraction 和 Lead Grading shadow_run，以便减少服务间编排复杂度，同时保留内部子图边界。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`
- `docs/brainstorm/brainstorming-session-2026-06-04-第四阶段小范围运行-LangGraph-Agent迁移.md`

## Story 定义

**目标：** 在 `apps/agents` 中实现 `POST /agent-runs/lead-extraction-grading`，内部编排 Lead Extraction 子图和 Lead Grading 子图。

**建议文件：**

- Modify: `apps/agents/app/api/agent_runs.py`
- Create/Modify: `apps/agents/app/graphs/lead_extraction_grading.py`
- Create/Modify: `apps/agents/app/schemas/lead_extraction_grading.py`
- Test: `apps/agents/tests/test_lead_extraction_grading_api.py`

**验收标准：**

- 外部优先暴露组合 API。
- 内部保留 Lead Extraction 和 Lead Grading 子图边界。
- API 明确标记为 `shadow_run`。
- 输出包含抽取结果、分级结果、硬规则摘要和差异解释字段。
- 不写 `staging_leads` 或客户主数据。

**非目标：**

- 不接入 `apps/api` active_run。
- 不切换生产入口。
- 不实现样本报告。

## Codex 提示词

```text
请执行 P4-E6-S3：实现组合 API /agent-runs/lead-extraction-grading。
要求使用 TDD；外部用组合 API，内部保留子图边界；shadow_run 不写 staging_leads；完成后执行两轮独立评审。
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
