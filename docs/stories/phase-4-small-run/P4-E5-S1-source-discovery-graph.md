# Story P4-E5-S1：实现 Source Discovery Graph

状态：待实现  
Sprint：Sprint 5  
优先级：P0  
Epic：P4-E5

## 用户故事

作为 Agent 服务开发者，我希望在 `apps/agents` 中实现 Source Discovery 的 LangGraph 平行版本，以便在不影响现有生产链路的情况下进行 shadow 对照。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`
- `docs/brainstorm/brainstorming-session-2026-06-04-第四阶段小范围运行-LangGraph-Agent迁移.md`

## Story 定义

**目标：** 创建 Source Discovery LangGraph graph，支持 shadow_run 输入和结构化候选来源输出。

**建议文件：**

- Create: `apps/agents/app/graphs/source_discovery.py`
- Create: `apps/agents/app/schemas/source_discovery.py`
- Modify: `apps/agents/app/api/agent_runs.py`
- Test: `apps/agents/tests/test_source_discovery_graph.py`

**验收标准：**

- graph 能接收来源发现输入并输出候选 URL、来源类型、初步风险和证据摘要。
- API 或 graph mode 明确标记为 `shadow_run`。
- shadow_run 不写 `lead_source_candidates` 或任何 core 业务表。
- run 状态写入 `agent_service_runs`。

**非目标：**

- 不替换现有 Source Discovery 生产入口。
- 不抓取非公开数据。
- 不实现完整对照报告。

## Codex 提示词

```text
请执行 P4-E5-S1：实现 Source Discovery Graph。
要求使用 TDD；仅做 shadow_run；不得写 lead_source_candidates 或 core 业务表；完成后执行两轮独立评审。
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
