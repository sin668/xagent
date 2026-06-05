# Story P4-E2-S3：实现可重试错误分类和重试策略

状态：已实现  
Sprint：Sprint 2  
优先级：P0  
Epic：P4-E2

## 用户故事

作为 Agent 服务开发者，我希望 `apps/agents` 能根据结构化错误类型决定是否重试，以便后续逐步去掉 `apps/api` 的 Agent retry worker。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 实现 retryable error 分类、retry_count 更新、next_retry_at 计算和最大重试次数限制。

**建议文件：**

- Create: `apps/agents/app/services/retry_policy.py`
- Modify: `apps/agents/app/services/agent_service_runs.py`
- Test: `apps/agents/tests/test_agent_retry_policy.py`

**验收标准：**

- `timeout_error`、`provider_rate_limited`、`transient_network_error` 可重试。
- `schema_validation_error`、`evidence_validation_error`、`risk_blocked`、`contract_mismatch` 不可重试。
- 默认最大重试次数为 2。
- 超过最大重试次数后状态为 failed。
- 重试记录更新 `retry_count` 和 `next_retry_at`。

**非目标：**

- 不实现后台 worker。
- 不调用真实 LLM。

## Codex 提示词

```text
请执行 P4-E2-S3：实现可重试错误分类和重试策略。
要求使用 TDD；重试由 apps/agents 负责；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- schema、证据、风险阻断错误不得重试。
- 不因重试绕过合规硬规则。

## 执行记录

执行日期：2026-06-05  
执行方式：按 `docs/superpowers/plans/2026-06-05-海外车辆采购AI获客系统-第四阶段小范围运行LangGraph-Agent迁移推进计划.md` 执行当前 Story。

### Git / Worktree 记录

- 延续当前环境事实：沙箱禁止写 `.git/FETCH_HEAD` 和 `.git/refs/heads/*.lock`。
- 无法在本环境完成 `git fetch`、创建分支和 worktree。
- 按当前目标的 sandbox fallback，在当前工作区继续执行本 Story。
- 未执行 git 提交。

### TDD 记录

红灯：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_agent_retry_policy.py -q
```

结果：失败，原因是 `ModuleNotFoundError: No module named 'app.services.retry_policy'`，符合当前 Story 需要新增重试策略模块的预期。

实现后的第一次运行发现：

- SQLite 内存测试会把 `DateTime(timezone=True)` 读回为 naive datetime，测试不能直接与 aware datetime 比较。
- SQLAlchemy 同一个 ORM 实例会随 session commit/refresh 反映后续状态，测试中不能把早先返回对象当作不可变快照。

修正：

- 对 SQLite 读回的 `next_retry_at` 在测试断言中补充 `UTC` 后比较。
- 在连续重试测试中立即保存每一步的 `status`、`retry_count`、`next_retry_at` 断言值，避免 ORM 引用被后续刷新影响。

绿灯：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_agent_retry_policy.py -q
```

结果：`5 passed in 0.21s`。

### 实现摘要

- 新增 `apps/agents/app/services/retry_policy.py`。
- 定义 `DEFAULT_MAX_RETRIES = 2`。
- 定义可重试错误类型：`timeout_error`、`provider_rate_limited`、`transient_network_error`。
- 定义不可重试错误类型：`schema_validation_error`、`evidence_validation_error`、`risk_blocked`、`contract_mismatch`。
- 新增 `RetryPolicy` 和 `RetryDecision`。
- 重试延迟采用保守线性 backoff：第 1 次 60 秒，第 2 次 120 秒。
- 在 `AgentServiceRunService` 中新增 `record_failure_with_retry_policy`。
- 可重试且未超过最大次数时，状态更新为 `retrying`，递增 `retry_count`，写入 `next_retry_at`。
- 不可重试或超过最大重试次数时，状态更新为 `failed`，不继续增加 `retry_count`，清空 `next_retry_at`。
- 旧有 `mark_retrying` 保持兼容，仅新增可选 `next_retry_at` 参数。
- 未实现后台 worker。
- 未调用真实 LLM。
- 未写 core 业务表。

### 验证命令

当前 Story 测试：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_agent_retry_policy.py -q
```

结果：`5 passed in 0.21s`。

`apps/agents` 全量测试：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest -q
```

结果：`43 passed in 0.51s`。

`apps/api` 回归导入检查：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/python - <<'PY'
from app.main import app
print(app.title)
print(len(app.routes) > 0)
PY
```

执行目录：`apps/api`  
结果：

```text
Overseas Vehicle Leads AI API
True
```

## 两轮独立评审记录

### 第一轮评审：验收标准、状态机和风控边界

结论：

- 通过。`timeout_error`、`provider_rate_limited`、`transient_network_error` 被识别为可重试。
- 通过。`schema_validation_error`、`evidence_validation_error`、`risk_blocked`、`contract_mismatch` 被识别为不可重试。
- 通过。默认最大重试次数为 2。
- 通过。超过最大重试次数后状态为 `failed`。
- 通过。重试记录会更新 `retry_count` 和 `next_retry_at`。
- 通过。未实现后台 worker，未调用真实 LLM。

发现项：

- `AgentServiceRunService.create_run` 的默认最大重试次数和 retry policy 常量存在重复硬编码风险。
- `risk_blocked` 后续可能更适合映射为 `blocked`，但本 Story 的明确验收标准是“不可重试”和“超过最大重试次数后 failed”，当前阶段不扩大状态语义。

修正结果：

- 已将 `create_run` 默认值改为复用 `DEFAULT_MAX_RETRIES`。
- `risk_blocked` 当前通过 retry policy 进入不可重试失败路径；阻断状态细分保留给后续明确 Story，不在本 Story 越界实现。

### 第二轮评审：测试覆盖、回归风险和维护性

结论：

- 通过。测试覆盖错误类型分类、默认最大次数、重试调度、最大次数失败和不可重试失败。
- 通过。旧有 `mark_retrying` 调用保持兼容，前序状态服务测试未被破坏。
- 通过。`apps/agents` 全量测试通过：`43 passed in 0.51s`。
- 通过。`apps/api` 可正常导入自身 `app.main`，现有 API agent 行为未被改动。
- 通过。当前实现只处理 `agent_service_runs`，未写 core 业务表。

发现项：

- 测试文件初版 `pytest` 导入位置不符合常规 import 分组。

修正结果：

- 已整理 `apps/agents/tests/test_agent_retry_policy.py` 的 import 顺序。
