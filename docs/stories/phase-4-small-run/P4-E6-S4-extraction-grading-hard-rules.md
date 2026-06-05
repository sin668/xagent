# Story P4-E6-S4：实现 schema、证据、联系方式反编造和硬规则校验

状态：待实现  
Sprint：Sprint 6  
优先级：P0  
Epic：P4-E6

## 用户故事

作为合规和质量负责人，我希望 Lead Extraction/Grading shadow_run 强制执行 schema、证据、联系方式反编造和硬规则校验，以便 LLM 输出不能绕过业务安全边界。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 在组合图中加入 schema 校验、证据命中校验、联系方式反编造校验和硬规则校验。

**建议文件：**

- Modify: `apps/agents/app/graphs/lead_extraction_grading.py`
- Create/Modify: `apps/agents/app/validators/`
- Test: `apps/agents/tests/test_extraction_grading_hard_rules.py`

**验收标准：**

- schema 通过率可统计，失败有明确错误。
- 联系方式必须能在证据中命中或被标记为无效。
- High/Forbidden、勿扰、C 级合规复核、Invalid/Watch 分流硬规则优先于 LLM 判断。
- 硬规则一致率目标为 100%。
- 校验摘要写入 `audit_json`。

**非目标：**

- 不生成样本报告。
- 不写业务表。
- 不接入 active_run。

## Codex 提示词

```text
请执行 P4-E6-S4：实现 schema、证据、联系方式反编造和硬规则校验。
要求使用 TDD；硬规则优先级必须高于 LLM 判断；联系方式不得无证据编造；完成后执行两轮独立评审。
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
