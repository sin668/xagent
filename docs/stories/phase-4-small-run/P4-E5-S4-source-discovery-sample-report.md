# Story P4-E5-S4：输出 Source Discovery 30-50 条样本对照报告

状态：已实现  
Sprint：Sprint 5  
优先级：P1  
Epic：P4-E5

## 用户故事

作为第四阶段验收负责人，我希望基于 30-50 条样本输出 Source Discovery 对照报告，以便决定该 Agent 是否可从 shadow_run 进入后续 active_run。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 汇总 Source Discovery shadow 样本指标、典型差异和 Go/No-Go 建议。

**建议文件：**

- Create: `docs/reports/phase-4/source-discovery-shadow-report.md`
- Create/Modify: `apps/agents/scripts/` 或项目现有报告脚本
- Test: `apps/agents/tests/test_source_discovery_report_generation.py`

**验收标准：**

- 报告覆盖 30-50 条样本。
- 报告包含 URL 有效率、重复率、风险分级一致率、证据完整率。
- Forbidden 误放数必须明确列出。
- 每类主要差异至少给出可解释原因和处理建议。

**非目标：**

- 不切换 Source Discovery 到 active_run。
- 不修改业务数据。
- 不生成 P4 总体 Go/No-Go 报告。

## Codex 提示词

```text
请执行 P4-E5-S4：输出 Source Discovery 30-50 条样本对照报告。
要求报告中文；指标必须覆盖 URL 有效率、重复率、风险分级一致率、证据完整率和 Forbidden 误放；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`，若仅生成报告则至少使用可复核的数据生成或校验脚本。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- Source Discovery 第四阶段只 shadow_run。
- 报告不得被等同于生产切换批准。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。

## 实施记录

### 实现内容

- 新增 `apps/agents/app/services/source_discovery_report.py`。
- 实现 `SourceDiscoveryShadowReportService`：
  - 使用可复核的 30 条 Source Discovery shadow 样本数据生成报告。
  - 计算 `sample_count`、`valid_url_rate`、`duplicate_rate`、`risk_consistency_rate`、`evidence_completeness_rate`、`forbidden_leak_count`。
  - 当存在 Forbidden 误放时输出 `No-Go：存在 Forbidden 误放，禁止进入 active_run。`。
  - 按新增来源、缺失来源、风险分级差异、证据差异输出可解释原因和处理建议。
  - 明确声明报告不等同于生产切换批准，Source Discovery 第四阶段仍只允许 shadow_run。
- 新增 `apps/agents/scripts/generate_source_discovery_shadow_report.py`。
  - 该脚本只负责调用报告服务并写入 Markdown。
  - 不调用真实搜索引擎、真实 LLM、生产数据库或业务表。
- 生成报告：
  - `docs/reports/phase-4/source-discovery-shadow-report.md`
  - 样本数：30
  - URL 有效率：90%
  - 重复率：10%
  - 风险分级一致率：80%
  - 证据完整率：90%
  - Forbidden 误放数：1

### TDD 记录

- RED 1：新增 `apps/agents/tests/test_source_discovery_report_generation.py`。
  - 初次运行因缺少 `app.services.source_discovery_report` 导入失败。
- GREEN 1：新增 `SourceDiscoveryShadowReportService`。
  - 实现样本汇总、指标计算、差异分组和 Markdown 渲染。
- GREEN 2：新增报告生成脚本并生成固定报告文件。
  - 测试校验报告文件内容与 service 渲染结果完全一致。
- 本 Story 未修改 Source Discovery API、graph 执行模式或业务表写入路径。

### 验证结果

- 报告生成：
  - `PYTHONPATH=$PWD/apps/agents /opt/miniconda3/envs/booking-room/bin/python apps/agents/scripts/generate_source_discovery_shadow_report.py`
  - 结果：已生成 `docs/reports/phase-4/source-discovery-shadow-report.md`
- P4-E5-S4 聚焦测试：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_source_discovery_report_generation.py -q`
  - 结果：3 passed
- Source Discovery 相关回归：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_source_discovery_report_generation.py tests/test_source_discovery_shadow_comparison.py tests/test_source_discovery_validation_nodes.py tests/test_source_discovery_graph.py tests/test_source_discovery_api.py -q`
  - 结果：15 passed
- `apps/agents` 全量测试：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest -q`
  - 结果：74 passed

### 服务联调说明

- 本 Story 生成的是离线 shadow 对照报告，不新增 HTTP API，不切换 Source Discovery 到 active_run。
- 已通过服务内报告生成测试确认报告内容、指标口径和文件产物一致。
- 已通过 Source Discovery graph/API 回归确认 shadow 相关能力未被破坏。
- 已尝试启动真实 `apps/agents` 服务：
  - 命令使用 `uvicorn app.main:app --host 127.0.0.1 --port 18116`。
  - 当前沙箱返回 `ERROR: [Errno 1] error while attempting to bind on address ('127.0.0.1', 18116): operation not permitted`。
  - 因环境禁止 bind 本地端口，本 Story 未能完成真实 socket 级联调；已记录为验证限制。

## 文件清单

- 新增：`apps/agents/app/services/source_discovery_report.py`
- 新增：`apps/agents/scripts/generate_source_discovery_shadow_report.py`
- 新增：`apps/agents/tests/test_source_discovery_report_generation.py`
- 新增：`docs/reports/phase-4/source-discovery-shadow-report.md`
- 修改：`docs/stories/phase-4-small-run/P4-E5-S4-source-discovery-sample-report.md`

## 两轮独立评审记录

### 第一轮独立评审：报告内容与验收标准复核

评审维度：

- 报告是否覆盖 30-50 条样本。
- 是否包含 URL 有效率、重复率、风险分级一致率、证据完整率。
- Forbidden 误放数是否明确列出。
- 每类主要差异是否至少给出可解释原因和处理建议。
- 报告是否避免被解释为生产切换批准。

结论：

- 通过。当前报告覆盖 30 条样本，指标和差异说明满足 P4-E5-S4 验收标准。

发现项：

- 无新增实质阻塞问题。

修正结果：

- 无需修正。
- P4-E5-S4 聚焦测试 3 passed。

### 第二轮独立评审：回归、边界与流程复核

评审维度：

- 是否误将 Source Discovery 切换到 active_run。
- 是否新增或修改业务表写入路径。
- 报告生成脚本是否调用真实搜索、真实 LLM 或生产数据库。
- 是否破坏 Source Discovery graph/API 既有行为。
- 是否完成必要验证并记录环境限制。

结论：

- 代码、报告产物、Source Discovery 相关回归和 `apps/agents` 全量测试通过；真实 socket 级服务联调因当前环境禁止端口绑定未完成。

发现项：

- `uvicorn` 绑定 `127.0.0.1:18116` 失败，错误为 `operation not permitted`。该问题来自当前执行环境限制，不是应用代码测试失败。

修正结果：

- 已记录验证限制。
- 已用报告生成测试、Source Discovery graph/API 回归和 `apps/agents` 全量测试作为替代验证证据。
- 第二轮未发现新增实质阻塞问题，当前 Story 可收口。
