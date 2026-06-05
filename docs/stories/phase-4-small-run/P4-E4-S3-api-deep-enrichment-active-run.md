# Story P4-E4-S3：apps/api 接入 Deep Enrichment HTTP active_run

状态：待实现  
Sprint：Sprint 4  
优先级：P0  
Epic：P4-E4

## 用户故事

作为业务操作人员，我希望 Deep Enrichment 可以通过 `apps/api` 调用 `apps/agents` active_run，并仍由 `apps/api` 控制字段候选采纳，以便小范围验证独立 Agent 服务。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 在 `apps/api` 中为 Deep Enrichment 接入 HTTP active_run，保留现有业务写入和人工审核边界。

**建议文件：**

- Modify: `apps/api/app/services/`
- Modify: `apps/api/app/agents/`
- Test: `apps/api/tests/test_deep_enrichment_http_active_run.py`

**验收标准：**

- `apps/api` 通过 HTTP 调用 `apps/agents` Deep Enrichment。
- `agent_task_runs.output_summary_json` 保存 `external_agent_run_id`。
- 字段候选仍由 `apps/api` schema 校验、风险门禁和人工确认后写入。
- 可通过配置或小范围开关控制是否使用 HTTP active_run。

**非目标：**

- 不删除现有本地 Deep Enrichment 逻辑。
- 不自动采纳字段候选。
- 不改 core 表结构。

## Codex 提示词

```text
请执行 P4-E4-S3：apps/api 接入 Deep Enrichment HTTP active_run。
要求使用 TDD；保留现有本地 Agent 行为；字段候选必须由 apps/api 审核后写入；完成后执行两轮独立评审。
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
- Deep Enrichment 只输出候选，不自动写入客户主数据。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。
