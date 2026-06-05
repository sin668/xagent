# Story P4-E6-S5：输出 Lead Extraction/Grading 30-50 条样本对照报告

状态：已实现  
Sprint：Sprint 6  
优先级：P1  
Epic：P4-E6

## 用户故事

作为第四阶段验收负责人，我希望基于 30-50 条样本输出 Lead Extraction/Grading 对照报告，以便判断抽取和分级组合图是否具备后续切换条件。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 汇总 Lead Extraction/Grading shadow 样本指标、硬规则一致性、等级差异和 Go/No-Go 建议。

**建议文件：**

- Create: `docs/reports/phase-4/lead-extraction-grading-shadow-report.md`
- Create/Modify: `apps/agents/scripts/` 或项目现有报告脚本
- Test: `apps/agents/tests/test_extraction_grading_report_generation.py`

**验收标准：**

- 报告覆盖 30-50 条样本。
- 报告包含 schema 通过率、证据命中率、联系方式反编造通过率、字段完整度。
- 报告包含等级一致率、硬规则一致率、C/Invalid/Watch 分流准确性。
- 硬规则不一致必须列为阻塞问题。
- 等级差异必须可解释。

**非目标：**

- 不切换 Lead Extraction/Grading 到 active_run。
- 不修改业务数据。
- 不生成 P4 总体 Go/No-Go 报告。

## Codex 提示词

```text
请执行 P4-E6-S5：输出 Lead Extraction/Grading 30-50 条样本对照报告。
要求报告中文；指标必须覆盖 schema、证据、联系方式反编造、等级一致率和硬规则一致率；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`，若仅生成报告则至少使用可复核的数据生成或校验脚本。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- Lead Extraction/Grading 第四阶段只 shadow_run。
- 报告不得被等同于生产切换批准。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。

## 实施记录

### 实现内容

- 新增 `apps/agents/app/services/extraction_grading_report.py`。
  - 实现 `LeadExtractionGradingShadowReportService`。
  - 使用 30 条可复核样本生成 Lead Extraction/Grading shadow 对照报告。
  - 从样本数据计算指标，而不是在 Markdown 中硬编码。
  - 统计指标包括：
    - `schema_pass_rate`
    - `evidence_hit_rate`
    - `contact_anti_fabrication_pass_rate`
    - `field_completeness_rate`
    - `grade_consistency_rate`
    - `hard_rule_consistency_rate`
    - `routing_accuracy_rate`
    - `hard_rule_mismatch_count`
  - 当存在硬规则不一致时输出 `No-Go：存在硬规则不一致，禁止进入 active_run。`。
  - 按等级差异、硬规则不一致、证据/联系方式差异输出可解释原因和处理建议。
- 新增 `apps/agents/scripts/generate_lead_extraction_grading_shadow_report.py`。
  - 该脚本只负责调用报告服务并写入 Markdown。
  - 不调用真实搜索引擎、真实 LLM、生产数据库或业务表。
- 新增报告：
  - `docs/reports/phase-4/lead-extraction-grading-shadow-report.md`
  - 样本数：30
  - schema 通过率：96.67%
  - 证据命中率：93.33%
  - 联系方式反编造通过率：90%
  - 字段完整度：87.5%
  - 等级一致率：80%
  - 硬规则一致率：96.67%
  - C/Invalid/Watch 分流准确性：96.67%
  - 硬规则不一致数：1

### TDD 记录

- RED 1：新增 `apps/agents/tests/test_extraction_grading_report_generation.py`。
  - 初次运行失败：`ModuleNotFoundError: No module named 'app.services.extraction_grading_report'`。
- GREEN 1：新增 `LeadExtractionGradingShadowReportService`。
  - 实现样本汇总、指标计算、差异分组和 Markdown 渲染。
- GREEN 2：新增报告生成脚本并生成固定报告文件。
  - 测试校验报告文件内容与 service 渲染结果完全一致。
- 本 Story 未修改 Lead Extraction/Grading API、graph 执行模式或业务表写入路径。

### 验证结果

- 报告生成：
  - `PYTHONPATH=$PWD/apps/agents /opt/miniconda3/envs/booking-room/bin/python apps/agents/scripts/generate_lead_extraction_grading_shadow_report.py`
  - 结果：已生成 `docs/reports/phase-4/lead-extraction-grading-shadow-report.md`
- P4-E6-S5 聚焦测试：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_extraction_grading_report_generation.py -q`
  - 结果：3 passed
- 相关回归：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_extraction_grading_report_generation.py tests/test_extraction_grading_hard_rules.py tests/test_lead_extraction_grading_api.py tests/test_lead_extraction_subgraph.py tests/test_lead_grading_subgraph.py tests/test_source_discovery_report_generation.py -q`
  - 结果：35 passed
- `apps/agents` 全量测试：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest -q`
  - 结果：106 passed

### 服务联调说明

- 本 Story 生成的是离线 shadow 对照报告，不新增 HTTP API，不切换 Lead Extraction/Grading 到 active_run。
- 已通过报告生成测试确认报告内容、指标口径和文件产物一致。
- 已通过 P4-E6 相关回归确认组合 API、硬规则校验和两个内部子图未被破坏。
- 已尝试启动真实 `apps/agents` 服务：
  - 命令使用 `uvicorn app.main:app --host 127.0.0.1 --port 18121`。
  - 当前沙箱返回 `ERROR: [Errno 1] error while attempting to bind on address ('127.0.0.1', 18121): operation not permitted`。
  - 因环境禁止 bind 本地端口，本 Story 未能完成真实 socket 级联调；已记录为验证限制。

### Git 与 worktree 限制记录

- 按总体目标尝试执行 `git fetch --prune origin`。
- 当前环境返回：`error: cannot open '.git/FETCH_HEAD': Operation not permitted`。
- 因 `.git` 写入受限，本轮无法完成拉取最新代码、创建 git 分支或创建 worktree。
- 当前 Story 按既有工作区继续推进，未执行分支切换、worktree 创建或锁操作。

## 文件清单

- 新增：`apps/agents/app/services/extraction_grading_report.py`
- 新增：`apps/agents/scripts/generate_lead_extraction_grading_shadow_report.py`
- 新增：`apps/agents/tests/test_extraction_grading_report_generation.py`
- 新增：`docs/reports/phase-4/lead-extraction-grading-shadow-report.md`
- 修改：`docs/stories/phase-4-small-run/P4-E6-S5-extraction-grading-sample-report.md`

## 两轮独立评审记录

### 第一轮独立评审：报告内容与验收标准复核

评审维度：

- 报告是否覆盖 30-50 条样本。
- 是否包含 schema 通过率、证据命中率、联系方式反编造通过率和字段完整度。
- 是否包含等级一致率、硬规则一致率、C/Invalid/Watch 分流准确性。
- 硬规则不一致是否列为阻塞问题。
- 等级差异是否可解释。
- 报告是否避免被解释为生产切换批准。

结论：

- 通过。当前报告覆盖 30 条样本，指标和差异说明满足 P4-E6-S5 验收标准。

发现项：

- 无新增实质阻塞问题。

修正结果：

- 无需修正。
- P4-E6-S5 聚焦测试 3 passed。

### 第二轮独立评审：回归、边界与流程复核

评审维度：

- 是否误将 Lead Extraction/Grading 切换到 active_run。
- 是否新增或修改业务表写入路径。
- 报告生成脚本是否调用真实搜索、真实 LLM 或生产数据库。
- 是否破坏 P4-E6 组合 API、硬规则校验和内部子图。
- 是否完成必要验证并记录环境限制。

结论：

- 代码、报告产物、P4-E6 相关回归和 `apps/agents` 全量测试通过；真实 socket 级服务联调因当前环境禁止端口绑定未完成。

发现项：

- `uvicorn` 绑定 `127.0.0.1:18121` 失败，错误为 `operation not permitted`。
- `git fetch --prune origin` 因 `.git/FETCH_HEAD` 写入权限失败，无法拉取最新代码或创建后续分支/worktree。

修正结果：

- 已记录端口绑定和 git/worktree 环境限制。
- 相关回归通过：35 passed。
- `apps/agents` 全量测试通过：106 passed。
- 第二轮未发现新增实质阻塞问题，当前 Story 可收口。
