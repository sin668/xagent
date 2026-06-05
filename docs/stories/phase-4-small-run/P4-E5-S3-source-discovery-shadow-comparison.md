# Story P4-E5-S3：实现 shadow 输出与现有来源发现结果对照

状态：已实现  
Sprint：Sprint 5  
优先级：P1  
Epic：P4-E5

## 用户故事

作为产品和技术评审者，我希望 Source Discovery 的 LangGraph shadow 输出能与现有来源发现结果对照，以便判断新图是否具备进入 active_run 的条件。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 建立 Source Discovery shadow 对照逻辑，比较 URL 有效率、重复率、风险分级一致率和证据完整率。

**建议文件：**

- Create: `apps/agents/app/services/source_discovery_comparison.py`
- Create/Modify: `apps/api/app/services/` 或对照导出脚本
- Test: `apps/agents/tests/test_source_discovery_shadow_comparison.py`

**验收标准：**

- 能输入现有链路结果和 shadow_run 输出并生成对照摘要。
- 对照摘要包含新增、缺失、风险分级差异、证据差异。
- Forbidden 误放必须单独标记为阻塞风险。
- 对照逻辑不写 `lead_source_candidates`。

**非目标：**

- 不生成最终 30-50 条样本报告。
- 不切换生产入口。
- 不自动采纳 shadow 输出。

## Codex 提示词

```text
请执行 P4-E5-S3：实现 Source Discovery shadow 输出与现有来源发现结果对照。
要求使用 TDD；对照必须标出 Forbidden 误放、风险分级差异和证据差异；不得写业务表；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- Source Discovery 第四阶段只 shadow_run。
- shadow 输出只用于对照，不自动进入业务候选表。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。

## 实施记录

### 实现内容

- 新增 `apps/agents/app/services/source_discovery_comparison.py`。
- 实现 `SourceDiscoveryShadowComparisonService.compare(...)`：
  - 输入现有来源发现结果列表和 Source Discovery shadow output。
  - 基于归一化 URL 进行对照。
  - 输出统一摘要 `phase4.source_discovery.shadow_comparison.v1`。
  - 统计 `existing_count`、`shadow_count`、`matched_count`、`added_count`、`missing_count`、`risk_difference_count`、`evidence_difference_count`、`forbidden_leak_count`。
  - 输出新增来源 `added`。
  - 输出现有链路有但 shadow 缺失的来源 `missing`。
  - 输出风险分级差异 `risk_differences`。
  - 输出证据完整性差异 `evidence_differences`。
  - 将 Forbidden 来源出现在 shadow 有效候选中标记为 `blocking_risks`，`risk_type=forbidden_leak`。
- 对照服务保持纯函数式：
  - 不依赖数据库 session。
  - 不写 `lead_source_candidates`。
  - 不自动采纳 shadow 输出。
  - 不切换现有 Source Discovery 生产入口。
- 对照前会检查 shadow output audit：
  - `writes_core_tables=True` 时拒绝。
  - `written_tables` 包含 `lead_source_candidates` 时拒绝。

### TDD 记录

- RED 1：新增 `apps/agents/tests/test_source_discovery_shadow_comparison.py`。
  - 初次运行因缺少 `app.services.source_discovery_comparison` 导入失败。
- GREEN 1：新增 `SourceDiscoveryShadowComparisonService`。
  - 实现新增、缺失、风险差异、证据差异和 Forbidden 误放阻塞风险。
  - 实现 shadow output 只读边界校验。
- 聚焦测试通过后，执行 Source Discovery 相关回归和 `apps/agents` 全量测试。

### 验证结果

- P4-E5-S3 聚焦测试：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_source_discovery_shadow_comparison.py -q`
  - 结果：3 passed
- Source Discovery 相关回归：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_source_discovery_shadow_comparison.py tests/test_source_discovery_validation_nodes.py tests/test_source_discovery_graph.py tests/test_source_discovery_api.py tests/test_api_contract.py -q`
  - 结果：16 passed
- `apps/agents` 全量测试：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest -q`
  - 结果：71 passed

### 服务联调说明

- 本 Story 实现的是离线/服务内对照逻辑，不新增 HTTP API，不生成最终样本报告。
- 已通过纯服务测试验证现有链路结果与 shadow 输出的对照摘要。
- 已通过 Source Discovery API/graph 回归验证 shadow output 仍不写业务表。
- 已尝试启动真实 `apps/agents` 服务：
  - 命令使用 `uvicorn app.main:app --host 127.0.0.1 --port 18115`。
  - 当前沙箱返回 `ERROR: [Errno 1] error while attempting to bind on address ('127.0.0.1', 18115): operation not permitted`。
  - 因环境禁止 bind 本地端口，本 Story 未能完成真实 socket 级联调；已记录为验证限制。
- 未调用真实搜索引擎、真实 LLM 或生产数据库。

## 文件清单

- 新增：`apps/agents/app/services/source_discovery_comparison.py`
- 新增：`apps/agents/tests/test_source_discovery_shadow_comparison.py`
- 修改：`docs/stories/phase-4-small-run/P4-E5-S3-source-discovery-shadow-comparison.md`

## 两轮独立评审记录

### 第一轮独立评审：对照摘要与风险边界复核

评审维度：

- 是否能输入现有链路结果和 shadow_run 输出并生成对照摘要。
- 摘要是否包含新增、缺失、风险分级差异和证据差异。
- Forbidden 误放是否单独标记为阻塞风险。
- 对照逻辑是否不写 `lead_source_candidates`。
- 是否不自动采纳 shadow 输出。

结论：

- 通过。当前实现满足 P4-E5-S3 验收标准。

发现项：

- 无新增实质阻塞问题。

修正结果：

- 无需修正。
- P4-E5-S3 聚焦测试 3 passed。

### 第二轮独立评审：回归、服务边界与非目标复核

评审维度：

- 是否破坏 Source Discovery graph/API 既有合同。
- 是否破坏 API contract 中 shadow 输出和业务表禁写边界。
- 是否误生成最终 30-50 条样本报告。
- 是否切换生产 Source Discovery 入口。
- 是否满足完成前验证要求。

结论：

- 代码、聚焦回归和 `apps/agents` 全量测试通过；真实 socket 级服务联调因当前环境禁止端口绑定未完成。

发现项：

- `uvicorn` 绑定 `127.0.0.1:18115` 失败，错误为 `operation not permitted`。该问题来自当前执行环境限制，不是应用代码测试失败。

修正结果：

- 已记录验证限制。
- 已用纯服务测试、Source Discovery graph/API 回归、API contract 测试和 `apps/agents` 全量测试作为替代验证证据。
- 第二轮未发现新增实质阻塞问题，当前 Story 可收口。
