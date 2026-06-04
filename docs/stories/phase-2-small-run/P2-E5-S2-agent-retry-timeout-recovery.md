# Story P2-E5-S2：失败重试、超时恢复和任务状态机收敛

状态：Done  
Sprint：Sprint 4  
优先级：P1  
Epic：P2-E5

## 用户故事

作为第二阶段小范围运行的研发执行者，我希望完成“失败重试、超时恢复和任务状态机收敛”，以便系统可以按 BMAD 已冻结方案推进真实 LLM、来源发现、审核、抽取、审计和联调闭环。

## 上下文来源

- `docs/product/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行方案与产品技术设计.md`
- `_bmad-output/brainstorming/brainstorming-session-2026-06-02-第二阶段小范围运行-LLM来源发现Agent.md`
- `docs/superpowers/plans/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行Codex推进计划.md`
- `docs/AI协同开发执行标准.md`
- `AGENTS.md`

## Story 定义

**目标：** 支持 retry_pending、running 超时恢复和最大重试次数。

**Files:**

- Create: `apps/api/app/services/agent_retries.py`
- Modify: `apps/api/app/services/agent_task_runs.py`
- Test: `apps/api/tests/test_agent_retries.py`

**Codex 提示词：**

```text
请执行 P2-E5-S2：失败重试、超时恢复和任务状态机收敛。

要求：
1. 使用 superpowers:test-driven-development。
2. 单任务最多重试 3 次。
3. LLM 网络、超时、限流可重试。
4. JSON schema 校验失败不自动重试。
5. 来源风险异常不自动重试。
6. Forbidden 直接阻断并审计。
7. running 超时任务标记 failed 或 retry_pending。
8. 运行 pytest apps/api/tests/test_agent_retries.py。
9. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p2-e5-s2-执行结果.md。
不要执行下一个 Story。
```

**验收标准：**

- 技术失败可重试。
- 合规失败不重试。

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

- 新增：`apps/api/app/services/agent_retries.py`
- 新增：`apps/api/tests/test_agent_retries.py`
- 修改：`apps/api/app/services/agent_task_runs.py`

### 实现说明

- 新增 `AgentRetryPolicy`，统一判断 Agent 失败是否允许自动重试。
- 单任务最大重试次数为 3 次。
- `network_error`、`timeout_error`、`rate_limit_error` 归类为技术失败，未达到最大次数时进入 `retry_pending`。
- `schema_validation_error`、`suspected_fabrication`、`risk_blocked`、`forbidden_risk`、`high_risk_blocked`、`source_risk_exception` 归类为不可自动重试失败。
- `Forbidden` 风险失败保持 `failed`，不增加 `retry_count`，并在 `output_summary_json` 中保留错误和重试决策。
- 新增 `AgentRetryRecoveryService`，用于将超时 `running` 任务恢复为 `retry_pending` 或 `failed`。
- `AgentTaskRunService.fail()` 保持原有调用兼容；传入结构化 `error` 时记录审计信息和重试决策。

### TDD 记录

#### RED

先创建 `apps/api/tests/test_agent_retries.py`，覆盖：

- 技术失败允许重试。
- 最大重试次数后不再重试。
- Schema、风险、Forbidden 类失败不自动重试。
- `AgentTaskRunService.fail()` 可按错误类型进入 `retry_pending` 或 `failed`。
- 超时 `running` 任务可恢复为 `retry_pending` 或 `failed`。

运行：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_agent_retries.py
```

结果：收集失败，符合 RED 预期。

```text
ModuleNotFoundError: No module named 'app.services.agent_retries'
```

#### GREEN

新增 `agent_retries.py` 并扩展 `agent_task_runs.py` 后，目标测试通过：

```text
7 passed
```

### 验证结果

目标测试：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_agent_retries.py
```

结果：`7 passed`。

相关后端回归：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_agent_retries.py apps/api/tests/test_agent_task_run_model.py apps/api/tests/test_llm_fallback.py apps/api/tests/test_agent_scheduler.py apps/api/tests/test_agent_locks.py
```

结果：`26 passed`。

语法检查：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/agent_retries.py apps/api/app/services/agent_task_runs.py
```

结果：通过。

### 验收对照

- 技术失败可重试：通过，网络、超时、限流错误在 `retry_count < 3` 时进入 `retry_pending`。
- 合规失败不重试：通过，Schema、风险、Forbidden 类失败保持 `failed`。
- 单任务最多重试 3 次：通过，`retry_count >= 3` 时不再重试。
- Forbidden 直接阻断并审计：通过，保持 `failed`，并记录 `error` 与 `retry_decision`。
- running 超时任务标记 failed 或 retry_pending：通过，未达最大次数进入 `retry_pending`，达到最大次数进入 `failed`。

### 第一轮独立多维度评审

- 结论：通过，无实质阻塞问题。
- 功能完整性：重试策略、失败状态收敛和超时恢复均已覆盖。
- 风险合规：合规类失败、来源风险异常和 Forbidden 均不自动重试，未放宽 High/Forbidden 风控边界。
- 审计完整性：结构化 `error` 和 `retry_decision` 写入 `output_summary_json`，便于后续审计和看板统计。
- 兼容性：未传入 `error` 的既有失败调用仍按未知失败处理并保持 `failed`。
- 测试覆盖：目标测试覆盖技术失败、最大次数、不可重试失败、Forbidden 和超时恢复。
- 发现项：无新增实质问题。
- 修正结果：无需修正。

### 第二轮独立多维度评审

- 结论：通过，连续两轮未发现新增实质阻塞问题。
- 回归风险：相关后端回归 `26 passed`，未破坏任务模型、LLM fallback、调度和 Redis lock 测试。
- 状态机一致性：`pending/retry_pending -> running -> retry_pending/failed/succeeded` 路径清晰，超时恢复不会修改未超时任务。
- 数据边界：本 Story 只处理任务状态和审计摘要，不执行来源采集、线索抽取或触达动作。
- 范围控制：未执行下一 Story；未做锁操作；未做 git 操作。
- 修正结果：无需修正。
