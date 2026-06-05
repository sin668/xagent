# Story P4-E4-S4：apps/api 接入 Lead Cleanup HTTP active_run

状态：待实现  
Sprint：Sprint 4  
优先级：P0  
Epic：P4-E4

## 用户故事

作为业务操作人员，我希望 Lead Cleanup 可以通过 `apps/api` 调用 `apps/agents` active_run，并仍由 `apps/api` 控制人工审核和清洗执行，以便小范围验证清洗建议质量。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 在 `apps/api` 中为 Lead Cleanup 接入 HTTP active_run，保留现有业务写入、人工审核和清洗执行边界。

**建议文件：**

- Modify: `apps/api/app/services/`
- Modify: `apps/api/app/agents/`
- Test: `apps/api/tests/test_lead_cleanup_http_active_run.py`

**验收标准：**

- `apps/api` 通过 HTTP 调用 `apps/agents` Lead Cleanup。
- `agent_task_runs.output_summary_json` 保存 `external_agent_run_id`。
- 清洗建议仍由 `apps/api` schema 校验、风险门禁和人工确认后处理。
- 不出现自动归并、自动恢复 Invalid 或自动删除数据。

**非目标：**

- 不删除现有本地 Lead Cleanup 逻辑。
- 不自动执行清洗建议。
- 不改 core 表结构。

## Codex 提示词

```text
请执行 P4-E4-S4：apps/api 接入 Lead Cleanup HTTP active_run。
要求使用 TDD；保留现有本地 Agent 行为；清洗建议必须由 apps/api 审核后处理；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 必须执行 `apps/api` 与 `apps/agents` 服务间真实联调。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- `apps/api` 中现有 LLM Agent 保持不变。
- Lead Cleanup 只输出建议，不自动执行。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。
