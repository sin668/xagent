# P2-E5-S3 LEAD_EXTRACTION 从来源候选池消费 approved 来源执行结果

## 基本信息

- Story：`docs/stories/phase-2-small-run/P2-E5-S3-lead-extraction-source-selection.md`
- 状态：已完成
- 执行日期：2026-06-02
- 执行原则：每次只执行一个 Story；不做锁操作；不做 git 操作；使用 TDD；完成前执行验证；完成后执行两轮独立多维度评审。

## 交付内容

- 新增：`apps/api/app/services/lead_extraction_from_sources.py`
- 新增：`apps/api/app/api/lead_extraction_from_sources.py`
- 新增：`apps/api/app/schemas/lead_extraction_from_sources.py`
- 新增：`apps/api/tests/test_lead_extraction_source_selection.py`
- 修改：`apps/api/app/main.py`
- 修改：`docs/stories/phase-2-small-run/P2-E5-S3-lead-extraction-source-selection.md`

## 功能说明

### 来源选择规则

新增 `LeadExtractionFromSourcesService`，只消费符合以下条件的来源候选：

- `review_status in ('auto_approved', 'approved')`
- `approved_for_extraction=true`
- `extraction_status in ('pending', 'retry')`
- `risk_level != Forbidden`
- High 来源必须人工审核通过，即 `review_status=approved`
- 未匹配 paused/archived 渠道计划

不符合条件的候选会返回阻断原因，用于审计和后续指标看板。

### 任务创建

新增接口：

```text
POST /agent-tasks/lead-extraction/from-sources/run
```

接口行为：

- 选择合格来源。
- 将选中来源标记为 `queued`。
- 创建 `AgentTaskRun(task_type=LEAD_EXTRACTION, status=pending)`。
- 在 `input_json` 中记录：
  - `candidate_ids`
  - `source_urls`
  - `source_selection_rule`
  - `risk_policy`
  - `country`
  - `city`
  - `limit`
- 在 `output_summary_json` 中记录：
  - `selected_count`
  - `blocked_count`
  - `blocked_candidates`

### 范围边界

本 Story 只完成来源池消费和 `LEAD_EXTRACTION` 任务创建，不执行真实 LLM 抽取，不写入 staging/core/audit 抽取结果。抽取结果写回属于 `P2-E5-S4`。

## TDD 记录

### RED

先创建 `apps/api/tests/test_lead_extraction_source_selection.py`，覆盖以下行为：

- 只选择 approved/auto_approved 且 approved_for_extraction=true 的 pending/retry 来源。
- 创建 `LEAD_EXTRACTION` 类型 `agent_task_runs`。
- 选中来源标记为 `queued`。
- 未审核 High 和 Forbidden 被阻断。
- paused/archived 渠道和 blocked extraction_status 不被消费。
- 无合格来源时返回 422。

运行：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_lead_extraction_source_selection.py
```

结果：4 项失败，符合 RED 预期。

```text
assert 404 == 200
```

失败原因：`/agent-tasks/lead-extraction/from-sources/run` 尚未实现和注册。

### GREEN

新增 service、schema、API 路由并注册到 `main.py` 后，目标测试通过：

```text
4 passed
```

## 调试记录

GREEN 首次运行后有 2 项失败：

- 成功创建任务时，测试期望 `blocked_count=0`，但服务返回了 3 条被规则排除的候选。
- 只有暂停/blocked 来源时，测试期望 200，但服务因没有可选来源返回 422。

根因：

- 审计要求应保留被规则排除的来源和阻断原因，因此成功创建任务时返回阻断明细更符合需求。
- run API 的语义是创建 `LEAD_EXTRACTION` 任务；完全没有合格来源时返回 422 更合理。

修正：

- 修正测试期望：成功任务可以同时返回 `blocked_candidates`。
- 保持无任何合格来源时返回 422。
- 复跑目标测试通过。

## 验证结果

### 目标测试

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_lead_extraction_source_selection.py
```

结果：`4 passed`。

### 相关后端回归

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_lead_extraction_source_selection.py apps/api/tests/test_lead_source_candidates_review_api.py apps/api/tests/test_lead_source_candidates_query_api.py apps/api/tests/test_agent_task_run_model.py apps/api/tests/test_agent_scheduler.py apps/api/tests/test_agent_retries.py
```

结果：`33 passed`。

### 语法检查

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/lead_extraction_from_sources.py apps/api/app/api/lead_extraction_from_sources.py apps/api/app/schemas/lead_extraction_from_sources.py apps/api/app/main.py
```

结果：通过。

## 验收对照

- 只消费 `review_status in ('auto_approved','approved')` 且 `approved_for_extraction=true` 的来源：通过。
- Forbidden 不得消费：通过。
- High 必须人工审核通过后才可只读抽取：通过。
- `extraction_status` 必须是 `pending` 或 `retry`：通过。
- 未触发渠道暂停规则：通过。
- 创建 `LEAD_EXTRACTION agent_task_runs`：通过。
- 消费范围符合风险规则：通过。
- 未审核 High 和 Forbidden 被阻断：通过。

## 第一轮独立多维度评审

- 结论：通过，无实质阻塞问题。
- 功能完整性：来源选择、风险阻断、渠道暂停阻断、任务创建和 queued 标记均已实现。
- 合规边界：Forbidden、未审核 High、暂停渠道均不会进入自动抽取队列；未执行私信、加好友、登录采集或反爬规避。
- 审计完整性：`agent_task_runs.input_json` 记录候选来源、选择规则和风险策略，`output_summary_json` 记录阻断明细。
- 状态一致性：被消费来源从 `pending/retry` 进入 `queued`，避免重复消费。
- 测试覆盖：目标测试覆盖准入、阻断、暂停渠道、任务创建和无合格来源。
- 发现项：无新增实质问题。
- 修正结果：无需修正。

## 第二轮独立多维度评审

- 结论：通过，连续两轮未发现新增实质阻塞问题。
- 回归风险：相关后端回归 `33 passed`，未破坏来源审核、来源查询、任务状态机、调度和重试逻辑。
- 产品边界：本 Story 未提前实现抽取结果写回，范围保持在来源消费和任务创建。
- 技术边界：API 使用现有 `AsyncSession.run_sync` 模式，与项目已有来源审核和 LLM 抽取 API 风格一致。
- 风险边界：High 只在人工审核通过且明确放行抽取后入队；Forbidden 始终阻断。
- 范围控制：未执行下一 Story；未做锁操作；未做 git 操作。
- 修正结果：无需修正。

## 后续建议

下一 Story 可进入 `P2-E5-S4`，实现抽取结果写入 staging/core/audit 并更新来源抽取状态。但本次执行未进入下一 Story。
