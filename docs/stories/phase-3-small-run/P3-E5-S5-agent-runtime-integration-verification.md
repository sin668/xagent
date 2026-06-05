# Story P3-E5-S5：Agent 项目与 apps/api 任务审计联调验证

状态：实现完成
Sprint：Sprint 5
优先级：P1
Epic：P3-E5

## 用户故事

作为第三阶段小范围运行的研发执行者，我希望完成“Agent 项目与 apps/api 任务审计联调验证”，以便系统可以按 BMAD 已冻结方案推进线索完善、客户晋级、客户承接、清洗治理和 LangGraph 局部试点闭环。

## 上下文来源

- `docs/brainstorm/brainstorming-session-2026-06-04-第三阶段小范围运行-客户管理工作台.md`
- `docs/product/2026-06-04-海外车辆采购AI获客系统-第三阶段小范围运行方案与产品技术设计.md`
- `docs/architecture/2026-06-03-LLM-Agent服务编排选型分析.md`
- `prototypes/mvp-mobile-agent/design-brief.md`
- `docs/AI协同开发执行标准.md`
- `agents.md`

## Story 定义

**目标：** 验证新 Agent 项目可被现有后端触发，并回写任务状态和结构化结果。

**Files:**

- Modify: `apps/api/app/services/lead_enrichment.py`
- Modify: `apps/api/app/services/lead_cleanup.py`
- Test: `apps/api/tests/test_phase3_agent_runtime_integration.py`
- Test: `apps/agents/tests/test_agent_runtime_integration.py`

**Codex 提示词：**

```text
请执行 P3-E5-S5：Agent 项目与 apps/api 任务审计联调验证。

要求：
1. 使用 superpowers:test-driven-development。
2. 严格依据第三阶段方案和本 Story 验收标准实现。
3. 保持 raw/staging/core/audit 分层，不让 AI 直接污染 core 数据。
4. 所有关键动作必须保留来源证据、操作人、时间和审计记录。
5. 不自动社交私信、不自动加好友、不自动发送触达消息。
6. 运行本 Story 对应测试，并按需执行相关联调验证。
7. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p3-e5-s5-执行结果.md。
8. 不要执行下一个 Story。
```

**验收标准：**

- apps/api 可触发 mock Agent。
- 任务状态写入 `agent_task_runs` 或第三阶段 run 表。
- Agent 失败不会阻塞 API 主线程。
- 结果经 apps/api Service 校验后写入候选/建议表。

**非目标：**

- 不迁移 Source Discovery/Lead Extraction。

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作。
- 不做 git 操作。
- 代码实现 Story 必须使用 `superpowers:test-driven-development`。
- 调试异常必须使用 `superpowers:systematic-debugging`。
- 完成前必须使用 `superpowers:verification-before-completion`。
- 完成后必须执行两轮独立多维度评审，并记录结论、发现项和修正结果。
- 必须执行必要的前后端真实联调，不允许只验证 seed 静态页面。
- 所有过程、结果、注解和文档使用中文。


## 通用风控边界

- 不自动社交私信。
- 不自动加好友。
- 不登录后批量采集。
- 不反爬规避。
- 不抓取非公开数据。
- High 来源未审核不得进入自动触达。
- Forbidden 来源不得作为客户晋级关键来源。
- Invalid 和 Watch 不进入触达队列。
- 勿扰客户不得再次进入触达队列。
- C 级客户报价、合同、付款、物流、清关、交付周期等动作前必须合规复核。
- 所有 AI 输出必须保存来源证据、prompt 版本、模型和审计记录。
- Agent 不得自动晋级客户、自动归并客户、自动恢复 Invalid、自动触达客户。

## 执行记录

执行时间：2026-06-04
执行者：Codex
执行方式：`superpowers:executing-plans` + `superpowers:test-driven-development`

### 实现内容

- 新增 `apps/agents/app/runtime/mock_runtime.py` 和 `apps/agents/app/runtime/__init__.py`，统一封装 Deep Enrichment 与 Lead Cleanup mock Agent runtime。
- 更新 `apps/api/app/services/lead_enrichment.py`，新增 `run_deep_enrichment_agent`，支持触发 mock Agent、写入 `agent_task_runs`、校验结构化输出并写入 `lead_enrichment_field_candidates`。
- 更新 `apps/api/app/services/lead_cleanup.py`，新增 `run_cleanup_agent`，支持触发 mock Agent、写入 `agent_task_runs`、校验结构化输出并写入 `lead_cleanup_suggestions`。
- 新增 `apps/api/tests/test_phase3_agent_runtime_integration.py`，覆盖 API 服务层 runtime 联调契约。
- 新增 `apps/agents/tests/test_agent_runtime_integration.py`，覆盖 Agent 项目 runtime 统一调用契约。

### 验收结果

- apps/api 可触发 mock Agent：已通过 `LeadEnrichmentService.run_deep_enrichment_agent` 和 `LeadCleanupSuggestionService.run_cleanup_agent` 验证。
- 任务状态写入 `agent_task_runs`：成功路径写入 `succeeded`，失败路径写入 `failed`，并保留 `output_summary_json` / `error_message`。
- Agent 失败不会阻塞 API 主线程：`run_deep_enrichment_agent` 捕获 runtime 异常并标记任务失败，不向调用方抛出异常。
- 结果经 apps/api Service 校验后写入候选/建议表：Deep Enrichment 写 `lead_enrichment_field_candidates`，Lead Cleanup 写 `lead_cleanup_suggestions`。
- 未迁移 Source Discovery / Lead Extraction，符合非目标。

### 测试记录

- 红灯验证：
  - `python -m pytest tests/test_phase3_agent_runtime_integration.py -q`，失败原因为缺少 `run_deep_enrichment_agent` / `run_cleanup_agent`。
  - `python -m pytest tests/test_agent_runtime_integration.py -q`，失败原因为缺少 `app.runtime`。
- 绿灯验证：
  - `apps/api` 当前 Story 测试：`3 passed in 0.39s`。
  - `apps/agents` 当前 Story 测试：`2 passed in 0.04s`。
- 关联回归：
  - `apps/api` P3-E5 相关回归：`48 passed in 2.56s`。
  - `apps/agents` 全量测试：`17 passed in 0.05s`。
  - `apps/api` 编译检查：`python -m compileall app/api app/services app/schemas app/models`，退出码 0。
  - `apps/agents` 编译检查：`python -m compileall app`，退出码 0。

### 两轮独立评审

第一轮评审：

- 结论：通过。
- 发现项：需确认 Agent runtime 输出不会直接污染 core 表。
- 修正结果：API 服务层仅写 `lead_enrichment_field_candidates` 与 `lead_cleanup_suggestions`，并要求 runtime 输出 `audit.writes_core_tables=false`。

第二轮评审：

- 结论：通过。
- 发现项：需确认 Agent 失败不会阻塞 API 主线程，且状态可审计。
- 修正结果：Deep Enrichment 失败路径捕获异常并标记 `LeadEnrichmentResult=failed`、`AgentTaskRun=failed`；Cleanup 失败路径标记 `LeadCleanupRun=failed`、`AgentTaskRun=failed`，保留错误摘要。
