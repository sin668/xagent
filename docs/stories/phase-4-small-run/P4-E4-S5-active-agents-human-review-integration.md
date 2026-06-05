# Story P4-E4-S5：字段候选和清洗建议人工审核链路联调

状态：待实现  
Sprint：Sprint 4  
优先级：P1  
Epic：P4-E4

## 用户故事

作为业务审核人员，我希望 HTTP active_run 产生的字段候选和清洗建议进入既有人工审核链路，以便验证新 Agent 服务不会绕过人工确认和合规门禁。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 对 Deep Enrichment 和 Lead Cleanup 的 HTTP active_run 结果执行服务间联调，验证候选输出、人工审核、业务写入或拒绝链路完整。

**建议文件：**

- Modify: `apps/api/app/services/`
- Modify: `apps/web/` 或现有审核入口相关文件
- Test: `apps/api/tests/integration/test_active_agents_human_review.py`
- Test: `apps/web/` 相关联调或 E2E 测试

**验收标准：**

- Deep Enrichment 字段候选可进入人工审核链路。
- Lead Cleanup 清洗建议可进入人工审核链路。
- 人工拒绝后不写入、不执行。
- 人工接受后仍由 `apps/api` 执行业务写入。
- 至少完成一次 `apps/api` 与 `apps/agents` 真实服务间联调记录。

**非目标：**

- 不新增复杂审核 UI。
- 不自动通过审核。
- 不迁移 Source Discovery 或 Lead Extraction/Grading 到 active_run。

## Codex 提示词

```text
请执行 P4-E4-S5：字段候选和清洗建议人工审核链路联调。
要求使用 TDD；必须做 apps/api 与 apps/agents 真实服务间联调；不得绕过人工审核；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 必须执行前后端或服务间真实联调。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- 所有业务表写入、合规硬规则、人工确认仍由 `apps/api` 负责。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。
