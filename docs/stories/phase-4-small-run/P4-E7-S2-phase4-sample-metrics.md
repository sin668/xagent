# Story P4-E7-S2：统计第四阶段样本指标

状态：已完成  
Sprint：Sprint 7  
优先级：P1  
Epic：P4-E7

## 用户故事

作为第四阶段验收负责人，我希望统一统计各 Agent 的小范围运行指标，以便基于数据判断哪些 Agent 可以继续 active，哪些需要继续 shadow 或回退。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 汇总 Source Discovery、Lead Extraction、Lead Grading、Deep Enrichment、Lead Cleanup 的第四阶段样本指标。

**建议文件：**

- Create: `docs/reports/phase-4/phase4-sample-metrics.md`
- Create/Modify: `apps/agents/scripts/phase4_metrics.py`
- Test: `apps/agents/tests/test_phase4_metrics.py`

**验收标准：**

- 指标覆盖 Source Discovery 的 URL 有效率、重复率、风险分级一致率、证据完整率。
- 指标覆盖 Lead Extraction 的 schema 通过率、证据命中率、联系方式反编造通过率、字段完整度。
- 指标覆盖 Lead Grading 的等级一致率、硬规则一致率、C/Invalid/Watch 分流准确性。
- 指标覆盖 Deep Enrichment 的字段候选有效率、人工接受率、无证据候选率。
- 指标覆盖 Lead Cleanup 的重复建议准确率、错误合并建议数、人工拒绝率。

**非目标：**

- 不输出最终 Go/No-Go 结论。
- 不修改业务数据。
- 不自动调整 Agent 开关。

## Codex 提示词

```text
请执行 P4-E7-S2：统计第四阶段样本指标。
要求报告中文；指标必须覆盖五类 Agent 的方案指标；不得自动调整业务开关；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`，若仅生成报告则至少使用可复核的数据生成或校验脚本。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- 指标只用于阶段评估，不自动驱动生产切换。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。

## Dev Agent Record

### 实施记录

- 已新增 `Phase4SampleMetricsService`，统一维护第四阶段五类 Agent 的样本指标、来源报告和说明口径。
- 已新增报告生成脚本 `apps/agents/scripts/generate_phase4_sample_metrics.py`，可重复生成 `docs/reports/phase-4/phase4-sample-metrics.md`。
- 已生成中文样本指标汇总报告，覆盖 Source Discovery、Lead Extraction、Lead Grading、Deep Enrichment、Lead Cleanup。
- 报告明确声明：
  - 不输出最终 Go/No-Go 结论。
  - 不修改业务数据。
  - 不自动调整 Agent 开关。
  - 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。

### TDD 记录

- RED：
  - 先新增 `apps/agents/tests/test_phase4_metrics.py`。
  - 执行 `cd apps/agents && PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_phase4_metrics.py -q`。
  - 初始失败符合预期：`ModuleNotFoundError: No module named 'app.services.phase4_metrics'`。
- GREEN：
  - 新增 `apps/agents/app/services/phase4_metrics.py`。
  - 新增 `apps/agents/scripts/generate_phase4_sample_metrics.py`。
  - 生成 `docs/reports/phase-4/phase4-sample-metrics.md`。
  - 聚焦测试通过：`3 passed in 0.01s`。
- REFACTOR：
  - 指标数据集中在服务层，脚本只负责定位仓库根目录、渲染报告和写入文件。
  - 文件内容测试确保报告产物与服务渲染结果完全一致，避免手工漂移。

### 验证结果

- 报告生成：
  - 命令：`PYTHONPATH=$PWD/apps/agents /opt/miniconda3/envs/booking-room/bin/python apps/agents/scripts/generate_phase4_sample_metrics.py`
  - 结果：已生成 `docs/reports/phase-4/phase4-sample-metrics.md`。
- 聚焦测试：
  - 命令：`cd apps/agents && PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_phase4_metrics.py -q`
  - 结果：`3 passed in 0.01s`。
- 相关回归：
  - 命令：`cd apps/agents && PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_phase4_metrics.py tests/test_extraction_grading_report_generation.py tests/test_source_discovery_report_generation.py tests/test_extraction_grading_hard_rules.py tests/test_lead_extraction_grading_api.py tests/test_observability_snapshot.py -q`
  - 结果：`24 passed in 1.53s`。
- `apps/agents` 全量测试：
  - 命令：`cd apps/agents && PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest -q`
  - 结果：`111 passed in 1.31s`。
- 服务启动探测：
  - 命令：`cd apps/agents && AGENTS_API_KEY=agents-test-key AGENTS_DATABASE_URL=sqlite+pysqlite:///:memory: PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 18124`
  - 结果：应用 startup 完成，但端口绑定失败：`ERROR: [Errno 1] error while attempting to bind on address ('127.0.0.1', 18124): operation not permitted`。
  - 结论：当前沙箱禁止 bind 本地端口，本 Story 使用服务测试、脚本测试和报告生成替代真实 socket 级验证。

### Git 与 worktree 限制记录

- 当前环境此前执行 `git fetch --prune origin` 返回：`error: cannot open '.git/FETCH_HEAD': Operation not permitted`。
- 因 `.git` 写入受限，本 Story 未执行拉取最新代码、创建 git 分支或创建 worktree。
- 当前 Story 按既有工作区继续推进，未执行锁操作、分支切换或 destructive git 操作。

## 文件清单

- 新增：`apps/agents/app/services/phase4_metrics.py`
- 新增：`apps/agents/scripts/generate_phase4_sample_metrics.py`
- 新增：`apps/agents/tests/test_phase4_metrics.py`
- 新增：`docs/reports/phase-4/phase4-sample-metrics.md`
- 修改：`docs/stories/phase-4-small-run/P4-E7-S2-phase4-sample-metrics.md`

## 两轮独立评审记录

### 第一轮独立评审：指标覆盖与非目标边界复核

评审维度：

- 是否覆盖五类 Agent 的全部验收指标。
- 是否明确区分 Source Discovery、Lead Extraction、Lead Grading、Deep Enrichment、Lead Cleanup。
- 是否避免输出最终 Go/No-Go 结论。
- 是否不修改业务数据、不自动调整 Agent 开关。
- 是否具备可重复生成和可测试的报告产物。

结论：

- 通过。报告覆盖全部验收指标，并将最终结论保留给 P4-E7-S4。

发现项：

- 无新增实质阻塞问题。

修正结果：

- 无需修正。
- 聚焦测试通过：`3 passed in 0.01s`。
- 相关回归通过：`24 passed in 1.53s`。

### 第二轮独立评审：回归、来源口径与流程复核

评审维度：

- 指标来源是否可追溯到既有 shadow 报告或第四阶段设计文档。
- Deep Enrichment 与 Lead Cleanup 是否未被误写为最终结论。
- 是否未触碰 `apps/api` 现有 LLM Agent 行为。
- 是否未引入业务表写入、自动触达、自动晋级、自动归并或自动恢复 Invalid。
- 是否完成全量测试和环境限制记录。

结论：

- 通过。P4-E7-S2 的代码、脚本、报告和测试均符合当前 Story 范围；第二轮未发现新增实质阻塞问题，当前 Story 可收口。

发现项：

- 当前沙箱仍禁止本地端口绑定，真实 `uvicorn` socket 级启动验证失败，错误为 `operation not permitted`。
- 当前 `.git/FETCH_HEAD` 写入受限，无法执行拉取最新代码或创建分支/worktree。

修正结果：

- 已记录端口绑定和 git/worktree 环境限制。
- `apps/agents` 全量测试通过：`111 passed in 1.31s`。
- 报告生成脚本通过，产物与服务渲染内容一致。
