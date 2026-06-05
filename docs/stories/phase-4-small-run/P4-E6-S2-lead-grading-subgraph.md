# Story P4-E6-S2：实现 Lead Grading 子图

状态：已实现  
Sprint：Sprint 6  
优先级：P0  
Epic：P4-E6

## 用户故事

作为 Agent 服务开发者，我希望在 `apps/agents` 中实现 Lead Grading 子图，以便对抽取结果进行可解释的等级、状态和合规分流。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 创建 Lead Grading LangGraph 子图，基于结构化线索、证据和硬规则输出等级建议与解释。

**建议文件：**

- Create: `apps/agents/app/graphs/lead_grading.py`
- Create: `apps/agents/app/schemas/lead_grading.py`
- Test: `apps/agents/tests/test_lead_grading_subgraph.py`

**验收标准：**

- 子图输出等级、状态分流、原因和触发规则。
- High/Forbidden、勿扰、C 级合规复核、Invalid/Watch 等硬规则不得被绕过。
- 等级差异必须包含可解释原因。
- 输出用于 shadow_run，不自动晋级客户。

**非目标：**

- 不实现 Lead Extraction。
- 不实现组合 API。
- 不写业务表。

## Codex 提示词

```text
请执行 P4-E6-S2：实现 Lead Grading 子图。
要求使用 TDD；硬规则必须优先于 LLM 判断；不得自动晋级客户；完成后执行两轮独立评审。
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

- 新增 `apps/agents/app/schemas/lead_grading.py`。
  - 定义 `LeadGradingAgentOutput` 和 `LeadGradingSuggestion`。
  - 输出 schema 版本为 `phase4.agent.lead_grading.v1`。
  - `recommended_grade` 支持 `A/B/C/Watch/Invalid`。
  - `status_route` 支持 `ready_for_manual_review`、`needs_compliance_review`、`needs_manual_risk_review`、`risk_blocked`。
  - schema 层禁止 `auto_promote_customer=True`，错误信息为 `Lead Grading 不允许自动晋级客户。`。
- 新增 `apps/agents/app/graphs/lead_grading.py`。
  - 使用 LangGraph `StateGraph` 实现 Lead Grading 子图。
  - 固定节点序列：
    - `load_extracted_lead`
    - `score_lead_signals`
    - `apply_hard_rules`
    - `explain_grade_delta`
    - `output_shadow_grading`
  - 基于结构化抽取结果计算基础分级信号：
    - 联系方式完整性
    - 出口意向
    - 车型兴趣
    - 公司名称与官网可核验
  - 在 `apply_hard_rules` 节点执行硬规则覆盖，优先级高于基础评分：
    - `forbidden_source` -> `Invalid` / `risk_blocked`
    - `do_not_contact` -> `Invalid` / `risk_blocked`
    - `existing_invalid` -> `Invalid` / `risk_blocked`
    - `high_risk_source` -> `Watch` / `needs_manual_risk_review`
    - `existing_watch` -> `Watch` / `needs_manual_risk_review`
    - `c_level_compliance_review` -> `C` / `needs_compliance_review`
    - `contact_missing` -> `C` / `needs_compliance_review`
  - 输出等级差异解释 `grade_delta_from_existing`。
  - 输出 audit 中明确 `writes_core_tables=False`。
- 修改 `apps/agents/app/adapters/api_contract.py`。
  - 允许 shadow 输出表标识 `shadow_lead_grading_suggestions`。
  - 不放开 `customers`、`staging_leads` 等 core 业务表。
- 修改 `apps/agents/tests/test_api_contract.py`。
  - 补充 `shadow_lead_grading_suggestions` 合同断言。
- 新增 `apps/agents/tests/test_lead_grading_subgraph.py`。
  - 覆盖节点序列、分级建议、状态分流、触发规则、等级差异解释、硬规则优先、shadow 禁写和 schema 自动晋级拦截。

### TDD 记录

- RED 1：新增 `apps/agents/tests/test_lead_grading_subgraph.py`。
  - 初次运行失败：`ModuleNotFoundError: No module named 'app.graphs.lead_grading'`。
- GREEN 1：新增 Lead Grading schema 和 LangGraph 子图。
  - 首次聚焦测试出现 2 个失败：分级原因文本包含句号，与测试期望的稳定中文短语不一致。
- 修正 1：将 `reasons` 调整为稳定短语，例如 `联系方式完整`、`出口意向明确`、`联系方式缺失`。
- GREEN 2：第二次聚焦测试出现 1 个失败：实现额外输出 `company_website_present` 解释信号，测试期望过窄。
- 修正 2：保留 `company_website_present`，并同步测试合同，因为该信号属于可解释分级的一部分，不违反 Story。
- GREEN 3：P4-E6-S2 聚焦测试通过。

### 验证结果

- P4-E6-S2 红阶段测试：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_lead_grading_subgraph.py -q`
  - 结果：失败，缺少 `app.graphs.lead_grading`，符合 RED 预期。
- P4-E6-S2 聚焦测试：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_lead_grading_subgraph.py -q`
  - 结果：11 passed
- 相关回归：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_lead_grading_subgraph.py tests/test_lead_extraction_subgraph.py tests/test_api_contract.py tests/test_source_discovery_graph.py tests/test_source_discovery_api.py tests/test_source_discovery_validation_nodes.py -q`
  - 结果：29 passed
- `apps/agents` 全量测试：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest -q`
  - 结果：90 passed

### 服务联调说明

- 本 Story 仅实现 Lead Grading 子图和 schema，不新增 HTTP API。
- Lead Extraction/Grading 组合 API 属于后续 Story，不在本 Story 实现范围内。
- 已通过服务内 LangGraph 测试确认：
  - 只能 `shadow_run`。
  - 硬规则优先于基础评分。
  - 不自动晋级客户。
  - 不写 `customers`、`staging_leads` 等业务表。
  - 输出 audit 中 `writes_core_tables=False`。
  - 输出表标识为 `shadow_lead_grading_suggestions`。
- 已尝试启动真实 `apps/agents` 服务：
  - 命令使用 `uvicorn app.main:app --host 127.0.0.1 --port 18118`。
  - 当前沙箱返回 `ERROR: [Errno 1] error while attempting to bind on address ('127.0.0.1', 18118): operation not permitted`。
  - 因环境禁止 bind 本地端口，本 Story 未能完成真实 socket 级联调；已记录为验证限制。

### Git 与 worktree 限制记录

- 按总体目标尝试执行 `git fetch --prune origin`。
- 当前环境返回：`error: cannot open '.git/FETCH_HEAD': Operation not permitted`。
- 因 `.git` 写入受限，本轮无法完成拉取最新代码、创建 git 分支或创建 worktree。
- 当前 Story 按既有工作区继续推进，未执行分支切换、worktree 创建或锁操作。

## 文件清单

- 新增：`apps/agents/app/graphs/lead_grading.py`
- 新增：`apps/agents/app/schemas/lead_grading.py`
- 新增：`apps/agents/tests/test_lead_grading_subgraph.py`
- 修改：`apps/agents/app/adapters/api_contract.py`
- 修改：`apps/agents/tests/test_api_contract.py`
- 修改：`docs/stories/phase-4-small-run/P4-E6-S2-lead-grading-subgraph.md`

## 两轮独立评审记录

### 第一轮独立评审：需求覆盖与硬规则复核

评审维度：

- 是否只实现当前 P4-E6-S2 Story。
- 子图是否输出等级、状态分流、原因和触发规则。
- High/Forbidden、勿扰、C 级合规复核、Invalid/Watch 等硬规则是否优先于基础评分。
- 等级差异是否包含可解释原因。
- 输出是否用于 shadow_run 且不自动晋级客户。

结论：

- 通过。当前实现满足 P4-E6-S2 验收标准，未实现 Lead Extraction、组合 API 或业务表写入。

发现项：

- 初次 GREEN 后发现 `reasons` 文本不够稳定，后续对照报告按原因聚合时会增加噪音。
- 第二次 GREEN 后发现测试未包含 `company_website_present` 解释信号，测试合同偏窄。

修正结果：

- 已将 `reasons` 调整为稳定中文短语。
- 已保留并测试 `company_website_present`，增强分级解释完整性。
- P4-E6-S2 聚焦测试已通过：11 passed。

### 第二轮独立评审：架构合同、回归与流程复核

评审维度：

- 是否保持 `apps/api` 与 `apps/agents` HTTP 服务边界。
- 是否只在 `apps/agents` 增加 LangGraph 子图，不改 `apps/api` 现有 LLM Agent。
- 是否误放开 core 业务表写入。
- 是否破坏 Lead Extraction 和 Source Discovery 既有 shadow 合同。
- 是否完成 TDD、验证和环境限制记录。

结论：

- 代码、聚焦测试、合同/相关回归和 `apps/agents` 全量测试通过；真实 socket 级服务联调因当前环境禁止端口绑定未完成。

发现项：

- `uvicorn` 绑定 `127.0.0.1:18118` 失败，错误为 `operation not permitted`。
- `git fetch --prune origin` 因 `.git/FETCH_HEAD` 写入权限失败，无法拉取最新代码或创建后续分支/worktree。

修正结果：

- 已记录端口绑定和 git/worktree 环境限制。
- 相关回归通过：29 passed。
- `apps/agents` 全量测试通过：90 passed。
- 第二轮未发现新增实质阻塞问题，当前 Story 可收口。
