# Story P4-E7-S3：整理失败案例和不可重试错误

状态：已完成  
Sprint：Sprint 7  
优先级：P1  
Epic：P4-E7

## 用户故事

作为 Agent 运行质量负责人，我希望整理第四阶段失败案例和不可重试错误，以便改进错误分类、提示词、数据质量和后续迁移策略。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`
- `docs/brainstorm/brainstorming-session-2026-06-04-第四阶段小范围运行-LangGraph-Agent迁移.md`

## Story 定义

**目标：** 从 `agent_service_runs`、节点 trace 和对照报告中整理失败案例库，区分可重试和不可重试错误。

**建议文件：**

- Create: `docs/reports/phase-4/failed-cases-and-non-retryable-errors.md`
- Create/Modify: `apps/agents/app/services/error_classification.py`
- Test: `apps/agents/tests/test_failed_case_classification.py`

**验收标准：**

- 失败案例按 Agent 类型、错误类型、是否可重试分类。
- 不可重试错误包含 schema 不满足、证据缺失、Forbidden 来源、硬规则冲突等类别。
- 每类失败案例给出修正建议或后续 Story 建议。
- 不把合规硬规则失败归类为可自动重试成功的问题。

**非目标：**

- 不自动修改历史 run 状态。
- 不自动重跑失败任务。
- 不输出最终 Go/No-Go 结论。

## Codex 提示词

```text
请执行 P4-E7-S3：整理失败案例和不可重试错误。
要求报告中文；合规硬规则失败不得归类为可自动重试；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`，若仅生成报告则至少使用可复核的数据生成或校验脚本。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- 失败案例整理只用于改进，不自动恢复 Invalid、不自动重跑、不自动触达。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。

## Dev Agent Record

### 实施记录

- 已新增 `FailedCaseClassificationService`，用结构化案例整理第四阶段失败信号。
- 已新增不可重试合规错误判断函数 `is_non_retryable_compliance_error`。
- 已新增报告生成脚本 `apps/agents/scripts/generate_failed_cases_report.py`。
- 已生成中文报告 `docs/reports/phase-4/failed-cases-and-non-retryable-errors.md`。
- 报告覆盖：
  - 按 Agent 类型、错误类型、是否可重试分类。
  - schema 不满足、证据缺失、Forbidden 来源、硬规则冲突等不可重试类别。
  - 每类失败案例的根因判断、修正建议和后续 Story 建议。
  - 合规硬规则失败不得归类为可自动重试成功的问题。

### TDD 记录

- RED：
  - 先新增 `apps/agents/tests/test_failed_case_classification.py`。
  - 执行 `cd apps/agents && PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_failed_case_classification.py -q`。
  - 初始失败符合预期：`ModuleNotFoundError: No module named 'app.services.error_classification'`。
- GREEN：
  - 新增 `apps/agents/app/services/error_classification.py`。
  - 新增 `apps/agents/scripts/generate_failed_cases_report.py`。
  - 生成 `docs/reports/phase-4/failed-cases-and-non-retryable-errors.md`。
  - 聚焦测试通过：`4 passed in 0.02s`。
- REFACTOR：
  - 失败案例集中在服务层，脚本只负责生成报告。
  - 文件内容测试确保报告产物与服务渲染内容一致，避免手工维护漂移。

### 验证结果

- 报告生成：
  - 命令：`PYTHONPATH=$PWD/apps/agents /opt/miniconda3/envs/booking-room/bin/python apps/agents/scripts/generate_failed_cases_report.py`
  - 结果：已生成 `docs/reports/phase-4/failed-cases-and-non-retryable-errors.md`。
- 聚焦测试：
  - 命令：`cd apps/agents && PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_failed_case_classification.py -q`
  - 结果：`4 passed in 0.02s`。
- 相关回归：
  - 命令：`cd apps/agents && PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_failed_case_classification.py tests/test_agent_retry_policy.py tests/test_agent_node_trace_summary.py tests/test_phase4_metrics.py tests/test_extraction_grading_report_generation.py tests/test_source_discovery_report_generation.py -q`
  - 结果：`24 passed in 0.43s`。
- `apps/agents` 全量测试：
  - 命令：`cd apps/agents && PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest -q`
  - 结果：`115 passed in 1.90s`。
- 服务启动探测：
  - 命令：`cd apps/agents && AGENTS_API_KEY=agents-test-key AGENTS_DATABASE_URL=sqlite+pysqlite:///:memory: PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 18125`
  - 结果：应用 startup 完成，但端口绑定失败：`ERROR: [Errno 1] error while attempting to bind on address ('127.0.0.1', 18125): operation not permitted`。
  - 结论：当前沙箱禁止 bind 本地端口，本 Story 使用服务测试、脚本测试和报告生成替代真实 socket 级验证。

### Git 与 worktree 限制记录

- 当前环境此前执行 `git fetch --prune origin` 返回：`error: cannot open '.git/FETCH_HEAD': Operation not permitted`。
- 因 `.git` 写入受限，本 Story 未执行拉取最新代码、创建 git 分支或创建 worktree。
- 当前 Story 按既有工作区继续推进，未执行锁操作、分支切换或 destructive git 操作。

## 文件清单

- 新增：`apps/agents/app/services/error_classification.py`
- 新增：`apps/agents/scripts/generate_failed_cases_report.py`
- 新增：`apps/agents/tests/test_failed_case_classification.py`
- 新增：`docs/reports/phase-4/failed-cases-and-non-retryable-errors.md`
- 修改：`docs/stories/phase-4-small-run/P4-E7-S3-failed-cases-non-retryable-errors.md`

## 两轮独立评审记录

### 第一轮独立评审：失败分类与合规边界复核

评审维度：

- 是否按 Agent 类型、错误类型、是否可重试分类。
- 不可重试错误是否包含 schema 不满足、证据缺失、Forbidden 来源、硬规则冲突。
- 每类失败案例是否给出修正建议或后续 Story 建议。
- 合规硬规则失败是否明确不可自动重试。
- 是否不自动修改历史 run 状态、不自动重跑失败任务。

结论：

- 通过。当前报告满足 P4-E7-S3 验收标准，且合规硬规则失败被明确列为不可重试问题。

发现项：

- 无新增实质阻塞问题。

修正结果：

- 无需修正。
- 聚焦测试通过：`4 passed in 0.02s`。
- 相关回归通过：`24 passed in 0.43s`。

### 第二轮独立评审：回归、来源口径与非目标复核

评审维度：

- 失败案例是否可追溯到 `agent_service_runs` retry policy、节点 trace 或对照报告。
- 是否未输出最终 Go/No-Go 结论。
- 是否未触碰 `apps/api` 现有 LLM Agent 行为。
- 是否未引入业务表写入、自动触达、自动晋级、自动归并或自动恢复 Invalid。
- 是否完成全量测试和环境限制记录。

结论：

- 通过。P4-E7-S3 的服务、脚本、报告和测试均符合当前 Story 范围；第二轮未发现新增实质阻塞问题，当前 Story 可收口。

发现项：

- 当前沙箱仍禁止本地端口绑定，真实 `uvicorn` socket 级启动验证失败，错误为 `operation not permitted`。
- 当前 `.git/FETCH_HEAD` 写入受限，无法执行拉取最新代码或创建分支/worktree。

修正结果：

- 已记录端口绑定和 git/worktree 环境限制。
- `apps/agents` 全量测试通过：`115 passed in 1.90s`。
- 报告生成脚本通过，产物与服务渲染内容一致。
