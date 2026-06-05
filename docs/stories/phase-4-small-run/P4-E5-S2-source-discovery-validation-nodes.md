# Story P4-E5-S2：实现来源归一化、风险分级、去重、证据校验节点

状态：已实现  
Sprint：Sprint 5  
优先级：P0  
Epic：P4-E5

## 用户故事

作为 Source Discovery shadow_run 的质量负责人，我希望 LangGraph 中有明确的来源归一化、风险分级、去重和证据校验节点，以便对照结果可解释且不会放过 Forbidden 来源。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 在 Source Discovery graph 中实现质量与合规校验节点，并将节点执行摘要写入 run audit。

**建议文件：**

- Modify: `apps/agents/app/graphs/source_discovery.py`
- Modify: `apps/agents/app/schemas/source_discovery.py`
- Test: `apps/agents/tests/test_source_discovery_validation_nodes.py`

**验收标准：**

- 来源 URL 归一化规则可测试。
- 重复 URL 或等价来源可被识别并标记。
- 风险分级覆盖 allowed、watch、high、forbidden 或项目约定等价级别。
- 缺少证据的候选不得进入有效候选列表。
- `audit_json.executed_nodes` 能体现关键节点执行结果摘要。

**非目标：**

- 不写业务表。
- 不做样本报告。
- 不切换现有 Source Discovery 入口。

## Codex 提示词

```text
请执行 P4-E5-S2：实现来源归一化、风险分级、去重、证据校验节点。
要求使用 TDD；Forbidden 误放必须为 0；shadow_run 不写业务表；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- Source Discovery 第四阶段只 shadow_run。
- Forbidden、High 风险、非公开数据不得被误放。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。

## 实施记录

### 实现内容

- 增强 `apps/agents/app/graphs/source_discovery.py` 的 Source Discovery 质量节点：
  - `normalize_source_candidates`：
    - URL 自动补齐 `https://`。
    - scheme 与 host 小写。
    - 去除 `www.` 前缀。
    - 去除 query、fragment 和末尾 `/`。
  - `classify_channel_risk`：
    - `official_website`、`marketplace` 归为 `low`。
    - `public_directory`、`unknown` 归为 `medium`。
    - `public_social` 归为 `high`，输出候选必须 `needs_manual_review`。
    - 登录墙、验证码、private 相关来源归为 `forbidden`，不得进入有效候选。
  - `dedupe_candidates`：
    - 按 `normalized_url` 去重。
    - 重复或等价来源写入 `blocked_items`，`reason=duplicate_source`。
  - `validate_source_evidence`：
    - 缺 URL、缺证据摘要、Forbidden 来源均写入 `blocked_items`。
    - Forbidden 误放为有效候选为 0。
  - `output_shadow_candidates`：
    - 继续只输出 `shadow_source_candidates`。
    - 不写 `lead_source_candidates` 或 core 业务表。
- 增加节点执行摘要：
  - graph output audit 中写入 `node_summaries`。
  - `apps/agents/app/api/agent_runs.py` 中对 Source Discovery 的持久化 `audit_json.executed_nodes` 写入结构化节点摘要。
  - 响应 envelope 的 `audit.executed_nodes` 继续保持字符串列表，兼容既有 `AgentRunAudit` 合同。
- 更新既有 Source Discovery 测试：
  - `blocked_items` 现在可能同时包含重复、缺证据、Forbidden，不再依赖固定顺序。
  - `blocked_item_count` 反映新增重复标记后的真实数量。

### TDD 记录

- RED 1：新增 `apps/agents/tests/test_source_discovery_validation_nodes.py`。
  - 初次运行失败，暴露 URL 归一化未去掉 `www.`、query、fragment，导致等价 URL 未识别为重复。
  - 初次运行失败，暴露持久化 `audit_json.executed_nodes` 仍是字符串列表，缺少节点执行摘要。
- GREEN 1：增强 URL 归一化、风险分级、重复标记、缺证据/Forbidden 拦截和 `node_summaries`。
- GREEN 2：新增 `_source_discovery_persisted_audit(...)`，让 Source Discovery 持久化 audit 使用结构化节点摘要，同时保留响应 envelope 兼容。
- 回归修正：
  - 旧测试从“第一个 blocked item 必须是 forbidden”调整为“blocked items 中必须包含 forbidden”。
  - 旧 summary 计数从 1 调整为 2，因为新增 duplicate 标记后 blocked items 包含 duplicate + forbidden。

### 验证结果

- P4-E5-S2 聚焦测试：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_source_discovery_validation_nodes.py -q`
  - 结果：2 passed
- Source Discovery 聚焦回归：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/test_source_discovery_validation_nodes.py tests/test_source_discovery_graph.py tests/test_source_discovery_api.py -q`
  - 结果：9 passed
- `apps/agents` 全量测试：
  - `PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest -q`
  - 结果：68 passed

### 服务联调说明

- 已通过 `apps/agents` FastAPI TestClient 验证 `/agent-runs/source-discovery` 的 shadow_run、状态写入、输出摘要和持久化 audit。
- 已尝试启动真实 `apps/agents` 服务：
  - 命令使用 `uvicorn app.main:app --host 127.0.0.1 --port 18114`。
  - 当前沙箱返回 `ERROR: [Errno 1] error while attempting to bind on address ('127.0.0.1', 18114): operation not permitted`。
  - 因环境禁止 bind 本地端口，本 Story 未能完成真实 socket 级联调；已记录为验证限制。
- 未调用真实搜索引擎、真实 LLM 或生产数据库。

## 文件清单

- 修改：`apps/agents/app/graphs/source_discovery.py`
- 修改：`apps/agents/app/api/agent_runs.py`
- 新增：`apps/agents/tests/test_source_discovery_validation_nodes.py`
- 修改：`apps/agents/tests/test_source_discovery_graph.py`
- 修改：`apps/agents/tests/test_source_discovery_api.py`
- 修改：`docs/stories/phase-4-small-run/P4-E5-S2-source-discovery-validation-nodes.md`

## 两轮独立评审记录

### 第一轮独立评审：质量节点与合规边界复核

评审维度：

- 来源 URL 归一化规则是否可测试。
- 重复 URL 或等价来源是否被识别并标记。
- 风险分级是否覆盖 low / medium / high / forbidden。
- 缺少证据的候选是否不得进入有效候选列表。
- Forbidden 来源是否不会误放为有效候选。
- shadow_run 是否不写 `lead_source_candidates` 或 core 业务表。

结论：

- 初版存在两个实质缺口，修正后满足 Story 验收标准。

发现项：

- URL 归一化未去掉 `www.`、query、fragment，导致 `HTTPS://WWW.Dealer.Example.RU/?utm_source=ad#contact` 与 `https://dealer.example.ru` 未被识别为等价来源。
- `blocked_items` 原先只记录无效/Forbidden，不记录重复来源，无法解释重复率。

修正结果：

- 增强 `normalize_url(...)`。
- 在 `dedupe_candidates` 中将重复来源写入 `blocked_items`，`reason=duplicate_source`。
- P4-E5-S2 聚焦测试通过。

### 第二轮独立评审：审计摘要、回归与可运维性复核

评审维度：

- `audit_json.executed_nodes` 是否体现关键节点执行结果摘要。
- 响应 envelope 是否保持兼容。
- Source Discovery API、graph 和 P4-E5-S1 既有合同是否被破坏。
- `apps/agents` 全量测试是否通过。
- 是否满足服务联调要求。

结论：

- 代码、聚焦回归和 `apps/agents` 全量测试通过；真实 socket 级服务联调因当前环境禁止端口绑定未完成。

发现项：

- 持久化 `audit_json.executed_nodes` 原先是字符串列表，不能体现节点执行摘要。
- `uvicorn` 绑定 `127.0.0.1:18114` 失败，错误为 `operation not permitted`。该问题来自当前执行环境限制，不是应用代码测试失败。

修正结果：

- 新增 Source Discovery 专用持久化 audit 组装逻辑，`audit_json.executed_nodes` 写入 `{node,status,summary}`。
- 响应 envelope 仍保持字符串 `executed_nodes`，不破坏统一响应 schema。
- 已记录验证限制。
- 第二轮未发现新增实质阻塞问题，当前 Story 可收口。
