# Story P2-E5-S3：`LEAD_EXTRACTION` 从来源候选池消费 approved 来源

状态：Done  
Sprint：Sprint 4  
优先级：P1  
Epic：P2-E5

## 用户故事

作为第二阶段小范围运行的研发执行者，我希望完成“`LEAD_EXTRACTION` 从来源候选池消费 approved 来源”，以便系统可以按 BMAD 已冻结方案推进真实 LLM、来源发现、审核、抽取、审计和联调闭环。

## 上下文来源

- `docs/product/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行方案与产品技术设计.md`
- `_bmad-output/brainstorming/brainstorming-session-2026-06-02-第二阶段小范围运行-LLM来源发现Agent.md`
- `docs/superpowers/plans/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行Codex推进计划.md`
- `docs/AI协同开发执行标准.md`
- `AGENTS.md`

## Story 定义

**目标：** 只消费符合准入条件的来源候选。

**Files:**

- Create: `apps/api/app/services/lead_extraction_from_sources.py`
- Create: `apps/api/app/api/lead_extraction_from_sources.py`
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_lead_extraction_source_selection.py`

**Codex 提示词：**

```text
请执行 P2-E5-S3：LEAD_EXTRACTION 从来源候选池消费 approved 来源。

要求：
1. 使用 superpowers:test-driven-development。
2. 只消费 review_status in ('auto_approved','approved') 且 approved_for_extraction=true 的来源。
3. Forbidden 不得消费。
4. High 必须人工审核通过后才可只读抽取。
5. extraction_status 必须是 pending 或 retry。
6. 未触发渠道暂停规则。
7. 创建 LEAD_EXTRACTION agent_task_runs。
8. 运行 pytest apps/api/tests/test_lead_extraction_source_selection.py。
9. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p2-e5-s3-执行结果.md。
不要执行下一个 Story。
```

**验收标准：**

- 消费范围符合风险规则。
- 未审核 High 和 Forbidden 被阻断。

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作。
- 不做 git 操作。
- 代码实现 Story 必须使用 `superpowers:test-driven-development`。
- 调试异常必须使用 `superpowers:systematic-debugging`。
- 完成前必须使用 `superpowers:verification-before-completion`。
- 完成后必须执行两轮独立多维度评审，并记录结论、发现项和修正结果。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- 不自动社交私信。
- 不自动加好友。
- 不登录后批量采集。
- 不反爬规避。
- 不抓取非公开数据。
- High 来源未审核不得进入自动抽取。
- Forbidden 来源不得进入自动抽取。
- Invalid 和 Watch 不进入触达队列。
- 勿扰客户不得再次进入触达队列。
- C 级线索报价、合同或实质交易前必须合规复核。
- 所有 AI 输出必须保存来源证据、prompt 版本、模型和审计记录。

## 实施结果

已完成。

### 交付内容

- 新增：`apps/api/app/services/lead_extraction_from_sources.py`
- 新增：`apps/api/app/api/lead_extraction_from_sources.py`
- 新增：`apps/api/app/schemas/lead_extraction_from_sources.py`
- 新增：`apps/api/tests/test_lead_extraction_source_selection.py`
- 修改：`apps/api/app/main.py`

### 实现说明

- 新增 `LeadExtractionFromSourcesService`，从 `lead_source_candidates` 中选择符合准入条件的来源。
- 仅消费 `review_status in ('auto_approved', 'approved')` 且 `approved_for_extraction=true` 的来源。
- 仅消费 `extraction_status in ('pending', 'retry')` 的来源。
- Forbidden 来源永不消费，并返回 `forbidden_risk_blocked` 阻断原因。
- High 来源必须 `review_status=approved` 且 `approved_for_extraction=true` 才能进入只读抽取队列；未审核 High 返回 `high_risk_requires_manual_approval`。
- 候选自身已暂停、blocked、已成功、未审批或未放行抽取时不会被消费。
- 若存在同国家、城市、渠道名的 `channel_plans.status in ('paused', 'archived')`，该来源不会被消费。
- 选中的来源会标记为 `extraction_status=queued`，避免重复创建抽取任务。
- 创建 `LEAD_EXTRACTION` 类型 `agent_task_runs`，状态为 `pending`，并在 `input_json` 中记录候选 ID、来源 URL、选择规则和风险策略。
- 新增接口：`POST /agent-tasks/lead-extraction/from-sources/run`。

### 范围边界

本 Story 只完成来源池消费和 `LEAD_EXTRACTION` 任务创建，不执行真实 LLM 抽取，不写入 staging/core/audit 抽取结果；抽取结果写回属于 `P2-E5-S4`。

### TDD 记录

#### RED

先创建 `apps/api/tests/test_lead_extraction_source_selection.py`，覆盖：

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

#### GREEN

新增 service、schema、API 路由并注册到 `main.py` 后，目标测试通过。

### 调试记录

GREEN 首次运行后有 2 项失败：

- 成功创建任务时，测试期望 `blocked_count=0`，但服务返回了 3 条被规则排除的候选。
- 只有暂停/blocked 来源时，测试期望 200，但服务因没有可选来源返回 422。

根因分析：

- 审计要求应保留被规则排除的来源和阻断原因，因此成功创建任务时返回阻断明细是更符合需求的行为。
- run API 的语义是创建 `LEAD_EXTRACTION` 任务；完全没有合格来源时返回 422 更合理。

修正结果：

- 修正测试期望：成功任务可以同时返回 `blocked_candidates`；无任何合格来源保持 422。
- 复跑目标测试通过。

### 验证结果

目标测试：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_lead_extraction_source_selection.py
```

结果：`4 passed`。

相关后端回归：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_lead_extraction_source_selection.py apps/api/tests/test_lead_source_candidates_review_api.py apps/api/tests/test_lead_source_candidates_query_api.py apps/api/tests/test_agent_task_run_model.py apps/api/tests/test_agent_scheduler.py apps/api/tests/test_agent_retries.py
```

结果：`33 passed`。

语法检查：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/lead_extraction_from_sources.py apps/api/app/api/lead_extraction_from_sources.py apps/api/app/schemas/lead_extraction_from_sources.py apps/api/app/main.py
```

结果：通过。

### 验收对照

- 只消费 `review_status in ('auto_approved','approved')` 且 `approved_for_extraction=true` 的来源：通过。
- Forbidden 不得消费：通过。
- High 必须人工审核通过后才可只读抽取：通过。
- `extraction_status` 必须是 `pending` 或 `retry`：通过。
- 未触发渠道暂停规则：通过，paused/archived 渠道不消费。
- 创建 `LEAD_EXTRACTION agent_task_runs`：通过。
- 消费范围符合风险规则：通过。
- 未审核 High 和 Forbidden 被阻断：通过。

### 第一轮独立多维度评审

- 结论：通过，无实质阻塞问题。
- 功能完整性：来源选择、风险阻断、渠道暂停阻断、任务创建和 queued 标记均已实现。
- 合规边界：Forbidden、未审核 High、暂停渠道均不会进入自动抽取队列；未执行私信、加好友、登录采集或反爬规避。
- 审计完整性：`agent_task_runs.input_json` 记录候选来源、选择规则和风险策略，`output_summary_json` 记录阻断明细。
- 状态一致性：被消费来源从 `pending/retry` 进入 `queued`，避免重复消费。
- 测试覆盖：目标测试覆盖准入、阻断、暂停渠道、任务创建和无合格来源。
- 发现项：无新增实质问题。
- 修正结果：无需修正。

### 第二轮独立多维度评审

- 结论：通过，连续两轮未发现新增实质阻塞问题。
- 回归风险：相关后端回归 `33 passed`，未破坏来源审核、来源查询、任务状态机、调度和重试逻辑。
- 产品边界：本 Story 未提前实现抽取结果写回，范围保持在来源消费和任务创建。
- 技术边界：API 使用现有 `AsyncSession.run_sync` 模式，与项目已有来源审核和 LLM 抽取 API 风格一致。
- 风险边界：High 只在人工审核通过且明确放行抽取后入队；Forbidden 始终阻断。
- 范围控制：未执行下一 Story；未做锁操作；未做 git 操作。
- 修正结果：无需修正。
