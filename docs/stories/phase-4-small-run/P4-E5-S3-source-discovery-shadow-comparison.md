# Story P4-E5-S3：实现 shadow 输出与现有来源发现结果对照

状态：待实现  
Sprint：Sprint 5  
优先级：P1  
Epic：P4-E5

## 用户故事

作为产品和技术评审者，我希望 Source Discovery 的 LangGraph shadow 输出能与现有来源发现结果对照，以便判断新图是否具备进入 active_run 的条件。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 建立 Source Discovery shadow 对照逻辑，比较 URL 有效率、重复率、风险分级一致率和证据完整率。

**建议文件：**

- Create: `apps/agents/app/services/source_discovery_comparison.py`
- Create/Modify: `apps/api/app/services/` 或对照导出脚本
- Test: `apps/agents/tests/test_source_discovery_shadow_comparison.py`

**验收标准：**

- 能输入现有链路结果和 shadow_run 输出并生成对照摘要。
- 对照摘要包含新增、缺失、风险分级差异、证据差异。
- Forbidden 误放必须单独标记为阻塞风险。
- 对照逻辑不写 `lead_source_candidates`。

**非目标：**

- 不生成最终 30-50 条样本报告。
- 不切换生产入口。
- 不自动采纳 shadow 输出。

## Codex 提示词

```text
请执行 P4-E5-S3：实现 Source Discovery shadow 输出与现有来源发现结果对照。
要求使用 TDD；对照必须标出 Forbidden 误放、风险分级差异和证据差异；不得写业务表；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- Source Discovery 第四阶段只 shadow_run。
- shadow 输出只用于对照，不自动进入业务候选表。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。
