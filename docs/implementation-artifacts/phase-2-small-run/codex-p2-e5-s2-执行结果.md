# P2-E5-S2 失败重试、超时恢复和任务状态机收敛执行结果

## 基本信息

- Story：`docs/stories/phase-2-small-run/P2-E5-S2-agent-retry-timeout-recovery.md`
- 状态：已完成
- 执行日期：2026-06-02
- 执行原则：每次只执行一个 Story；不做锁操作；不做 git 操作；使用 TDD；完成前执行验证；完成后执行两轮独立多维度评审。

## 交付内容

- 新增：`apps/api/app/services/agent_retries.py`
- 新增：`apps/api/tests/test_agent_retries.py`
- 修改：`apps/api/app/services/agent_task_runs.py`
- 修改：`docs/stories/phase-2-small-run/P2-E5-S2-agent-retry-timeout-recovery.md`

## 功能说明

### 重试策略

新增 `AgentRetryPolicy`：

- 最大重试次数：`3`
- 可自动重试错误：
  - `network_error`
  - `timeout_error`
  - `rate_limit_error`
- 不可自动重试错误：
  - `schema_validation_error`
  - `suspected_fabrication`
  - `risk_blocked`
  - `forbidden_risk`
  - `high_risk_blocked`
  - `source_risk_exception`

达到最大重试次数后，即使是技术失败也不再自动重试。

### 任务失败状态收敛

扩展 `AgentTaskRunService.fail()`：

- 传入结构化 `error` 时，按 `AgentRetryPolicy` 判断是否进入 `retry_pending`。
- 可重试技术失败：
  - `status=retry_pending`
  - `retry_count + 1`
  - `finished_at=None`
- 不可重试失败：
  - `status=failed`
  - 不增加 `retry_count`
  - `finished_at` 写入失败时间
- 审计信息写入 `output_summary_json.error` 和 `output_summary_json.retry_decision`。

未传入结构化 `error` 的旧调用保持兼容，按未知失败处理，不自动重试。

### 超时恢复

新增 `AgentRetryRecoveryService`：

- 仅处理 `running` 状态任务。
- 未超时任务原样返回。
- 超时任务按 `timeout_error` 进入重试策略：
  - 未达到最大重试次数：标记 `retry_pending`
  - 已达到最大重试次数：标记 `failed`
- 写入 `agent_task_timeout` 错误和重试决策，便于审计和后续看板统计。

## TDD 记录

### RED

先创建 `apps/api/tests/test_agent_retries.py`，覆盖以下行为：

- 技术失败允许重试。
- 最大重试次数后不再重试。
- Schema、风险、Forbidden 类失败不自动重试。
- `AgentTaskRunService.fail()` 可根据错误类型进入 `retry_pending` 或 `failed`。
- 超时 `running` 任务可恢复为 `retry_pending` 或 `failed`。

运行：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_agent_retries.py
```

结果：收集失败，符合 RED 预期。

```text
ModuleNotFoundError: No module named 'app.services.agent_retries'
```

### GREEN

新增 `agent_retries.py` 并扩展 `agent_task_runs.py` 后，目标测试通过：

```text
7 passed
```

## 验证结果

### 目标测试

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_agent_retries.py
```

结果：`7 passed`。

### 相关后端回归

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_agent_retries.py apps/api/tests/test_agent_task_run_model.py apps/api/tests/test_llm_fallback.py apps/api/tests/test_agent_scheduler.py apps/api/tests/test_agent_locks.py
```

结果：`26 passed`。

### 语法检查

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/agent_retries.py apps/api/app/services/agent_task_runs.py
```

结果：通过。

## 验收对照

- 单任务最多重试 3 次：通过。
- LLM 网络、超时、限流可重试：通过。
- JSON schema 校验失败不自动重试：通过。
- 来源风险异常不自动重试：通过。
- Forbidden 直接阻断并审计：通过。
- running 超时任务标记 failed 或 retry_pending：通过。
- 运行 `pytest apps/api/tests/test_agent_retries.py`：通过，`7 passed`。

## 第一轮独立多维度评审

- 结论：通过，无实质阻塞问题。
- 功能完整性：重试策略、失败状态收敛和超时恢复均已实现并测试。
- 风险合规：Schema、风险异常、High/Forbidden 类错误不会自动重试，未绕过风控边界。
- 审计完整性：失败原因和重试决策均写入 `output_summary_json`，后续可用于审计和指标看板。
- 兼容性：旧的 `fail()` 调用未传结构化错误时仍保持失败语义，不会意外进入重试队列。
- 测试覆盖：目标测试覆盖核心状态机分支和最大重试边界。
- 发现项：无新增实质问题。
- 修正结果：无需修正。

## 第二轮独立多维度评审

- 结论：通过，连续两轮未发现新增实质阻塞问题。
- 回归风险：相关后端回归 `26 passed`，未破坏任务运行模型、LLM fallback、调度和 Redis lock。
- 状态机一致性：`pending/retry_pending -> running -> retry_pending/failed/succeeded` 路径明确，超时恢复不会修改新鲜运行任务。
- 数据与执行边界：本 Story 只处理状态和审计，不执行来源采集、线索抽取、社交触达或反爬规避。
- 范围控制：未执行下一 Story；未做锁操作；未做 git 操作。
- 修正结果：无需修正。

## 后续建议

下一 Story 可继续推进 P2-E5 后续 Agent 执行闭环，但本次执行未进入下一 Story。
