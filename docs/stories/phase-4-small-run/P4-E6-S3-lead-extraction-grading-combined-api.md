# Story P4-E6-S3：实现组合 API /agent-runs/lead-extraction-grading

状态：已实现  
Sprint：Sprint 6  
优先级：P0  
Epic：P4-E6

## 用户故事

作为 `apps/api` 的调用方，我希望通过一个组合 API 触发 Lead Extraction 和 Lead Grading shadow_run，以便减少服务间编排复杂度，同时保留内部子图边界。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`
- `docs/brainstorm/brainstorming-session-2026-06-04-第四阶段小范围运行-LangGraph-Agent迁移.md`

## Story 定义

**目标：** 在 `apps/agents` 中实现 `POST /agent-runs/lead-extraction-grading`，内部编排 Lead Extraction 子图和 Lead Grading 子图。

**建议文件：**

- Modify: `apps/agents/app/api/agent_runs.py`
- Create/Modify: `apps/agents/app/graphs/lead_extraction_grading.py`
- Create/Modify: `apps/agents/app/schemas/lead_extraction_grading.py`
- Test: `apps/agents/tests/test_lead_extraction_grading_api.py`

**验收标准：**

- 外部优先暴露组合 API。
- 内部保留 Lead Extraction 和 Lead Grading 子图边界。
- API 明确标记为 `shadow_run`。
- 输出包含抽取结果、分级结果、硬规则摘要和差异解释字段。
- 不写 `staging_leads` 或客户主数据。

**非目标：**

- 不接入 `apps/api` active_run。
- 不切换生产入口。
- 不实现样本报告。

## Codex 提示词

```text
请执行 P4-E6-S3：实现组合 API /agent-runs/lead-extraction-grading。
要求使用 TDD；外部用组合 API，内部保留子图边界；shadow_run 不写 staging_leads；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- Lead Extraction/Grading 第四阶段只 shadow_run。
- High/Forbidden、勿扰、C 级合规复核、证据校验等硬规则不得被 LangGraph 绕过。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。

## 实施记录

### 实现内容

- 新增 `apps/agents/app/schemas/lead_extraction_grading.py`。
  - 定义 `LeadExtractionGradingAgentOutput` 和 `LeadExtractionGradingHardRuleSummary`。
  - 输出 schema 版本为 `phase4.agent.lead_extraction_grading.v1`。
  - 输出包含：
    - `extraction`：Lead Extraction 子图结果。
    - `grading`：Lead Grading 子图结果。
    - `hard_rule_summary`：硬规则是否触发、触发规则、风险标记。
    - `grade_delta_explanations`：等级差异解释字段。
    - `audit`：组合图审计摘要。
- 新增 `apps/agents/app/graphs/lead_extraction_grading.py`。
  - 实现组合编排 `LeadExtractionGradingGraphRunner`。
  - 内部依次调用：
    - `LeadExtractionGraphRunner`
    - `LeadGradingGraphRunner`
  - executed nodes 使用命名空间保留内部子图边界：
    - `lead_extraction.*`
    - `lead_grading.*`
  - 组合图只允许 `shadow_run`。
  - 组合图不复制抽取/分级逻辑，只负责编排和聚合输出。
- 修改 `apps/agents/app/api/agent_runs.py`。
  - 新增 `POST /agent-runs/lead-extraction-grading`。
  - 沿用现有 Agent Run 模式：
    - `create_run`
    - `mark_running`
    - graph run
    - `mark_succeeded` 或 `mark_failed`
  - `agent_type` 为 `lead_extraction_grading`。
  - 成功时持久化 `output_json`、`output_summary_json` 和 `audit_json`。
  - 失败时返回统一 `AgentRunResponse`，active 模式阻断归类为 `risk_blocked`。
- 新增 `apps/agents/tests/test_lead_extraction_grading_api.py`。
  - 覆盖 API Key、shadow 成功响应、run 持久化、硬规则摘要和 active 模式阻断。

### TDD 记录

- RED 1：新增 `apps/agents/tests/test_lead_extraction_grading_api.py`。
  - 初次运行 4 个用例失败，原因是 `/agent-runs/lead-extraction-grading` 尚不存在，返回 `404 Not Found`。
- GREEN 1：新增组合 schema、组合 graph，并在 `agent_runs.py` 注册 endpoint。
  - 复用 P4-E6-S1 的 Lead Extraction 子图。
  - 复用 P4-E6-S2 的 Lead Grading 子图。
  - 保留内部子图 executed nodes 命名空间。
- GREEN 2：P4-E6-S3 聚焦测试通过。

### 验证结果

- P4-E6-S3 红阶段测试：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_lead_extraction_grading_api.py -q`
  - 结果：4 failed，endpoint 返回 404，符合 RED 预期。
- P4-E6-S3 聚焦测试：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_lead_extraction_grading_api.py -q`
  - 结果：4 passed
- 相关回归：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_lead_extraction_grading_api.py tests/test_lead_extraction_subgraph.py tests/test_lead_grading_subgraph.py tests/test_api_contract.py tests/test_deep_enrichment_api.py tests/test_lead_cleanup_api.py tests/test_source_discovery_api.py -q`
  - 结果：33 passed
- `apps/agents` 全量测试：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest -q`
  - 结果：94 passed

### 服务联调说明

- 本 Story 在 `apps/agents` 内新增组合 HTTP API，未接入 `apps/api` active_run。
- `apps/api` 生产入口和现有 LLM Agent 保持不变。
- 已通过 FastAPI TestClient 验证 `POST /agent-runs/lead-extraction-grading`：
  - 需要 `X-Agents-Api-Key`。
  - 只允许 shadow_run 成功执行。
  - active 模式返回 `failed`，错误类型为 `risk_blocked`。
  - 输出包含抽取结果、分级结果、硬规则摘要和等级差异解释。
  - 持久化 `agent_service_runs`。
  - 不写 `staging_leads` 或 `customers`。
- 已尝试启动真实 `apps/agents` 服务：
  - 命令使用 `uvicorn app.main:app --host 127.0.0.1 --port 18119`。
  - 当前沙箱返回 `ERROR: [Errno 1] error while attempting to bind on address ('127.0.0.1', 18119): operation not permitted`。
  - 因环境禁止 bind 本地端口，本 Story 未能完成真实 socket 级联调；已记录为验证限制。

### Git 与 worktree 限制记录

- 按总体目标尝试执行 `git fetch --prune origin`。
- 当前环境返回：`error: cannot open '.git/FETCH_HEAD': Operation not permitted`。
- 因 `.git` 写入受限，本轮无法完成拉取最新代码、创建 git 分支或创建 worktree。
- 当前 Story 按既有工作区继续推进，未执行分支切换、worktree 创建或锁操作。

## 文件清单

- 新增：`apps/agents/app/graphs/lead_extraction_grading.py`
- 新增：`apps/agents/app/schemas/lead_extraction_grading.py`
- 新增：`apps/agents/tests/test_lead_extraction_grading_api.py`
- 修改：`apps/agents/app/api/agent_runs.py`
- 修改：`docs/stories/phase-4-small-run/P4-E6-S3-lead-extraction-grading-combined-api.md`

## 两轮独立评审记录

### 第一轮独立评审：需求覆盖与组合边界复核

评审维度：

- 是否外部优先暴露组合 API。
- 内部是否保留 Lead Extraction 和 Lead Grading 子图边界。
- API 是否明确标记并限制为 `shadow_run`。
- 输出是否包含抽取结果、分级结果、硬规则摘要和差异解释字段。
- 是否不写 `staging_leads` 或客户主数据。

结论：

- 通过。当前实现满足 P4-E6-S3 验收标准，未接入 `apps/api` active_run，未切换生产入口，未实现样本报告。

发现项：

- 无新增实质阻塞问题。

修正结果：

- 无需修正。
- P4-E6-S3 聚焦测试已通过：4 passed。

### 第二轮独立评审：架构合同、回归与流程复核

评审维度：

- 是否保持 `apps/api` 与 `apps/agents` HTTP 服务边界。
- 是否未修改 `apps/api` 现有 LLM Agent。
- 是否复用内部子图而非复制抽取/分级逻辑。
- 是否破坏 Deep Enrichment、Lead Cleanup、Source Discovery 既有 API。
- 是否完成 TDD、验证和环境限制记录。

结论：

- 代码、聚焦测试、相关 API 回归和 `apps/agents` 全量测试通过；真实 socket 级服务联调因当前环境禁止端口绑定未完成。

发现项：

- `uvicorn` 绑定 `127.0.0.1:18119` 失败，错误为 `operation not permitted`。
- `git fetch --prune origin` 因 `.git/FETCH_HEAD` 写入权限失败，无法拉取最新代码或创建后续分支/worktree。

修正结果：

- 已记录端口绑定和 git/worktree 环境限制。
- 相关回归通过：33 passed。
- `apps/agents` 全量测试通过：94 passed。
- 第二轮未发现新增实质阻塞问题，当前 Story 可收口。
