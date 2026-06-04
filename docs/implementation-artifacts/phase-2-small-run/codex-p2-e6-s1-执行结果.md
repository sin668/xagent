# P2-E6-S1 第二阶段 dashboard API 执行结果

## 基本信息

- Story：`docs/stories/phase-2-small-run/P2-E6-S1-phase2-dashboard-api.md`
- 状态：已完成
- 执行日期：2026-06-03
- 执行原则：每次只执行一个 Story；不做锁操作；不做 git 操作；使用 TDD；完成前执行验证；完成后执行两轮独立多维度评审。

## 交付内容

- 新增：`apps/api/app/services/phase2_dashboard.py`
- 新增：`apps/api/app/api/phase2_dashboard.py`
- 新增：`apps/api/app/schemas/phase2_dashboard.py`
- 新增：`apps/api/tests/test_phase2_dashboard_api.py`
- 修改：`apps/api/app/main.py`
- 修改：`apps/api/app/services/dashboard.py`
- 修改：`docs/stories/phase-2-small-run/P2-E6-S1-phase2-dashboard-api.md`

## 功能说明

### API

新增：

```text
GET /dashboard/phase2
```

查询参数：

- `channel_prefix`：用于第二阶段小范围运行按渠道/测试前缀隔离统计。

### 指标范围

接口返回：

- 来源候选总量。
- Low/Medium/High/Forbidden 风险分布。
- 审核积压。
- 自动抽取成功数量。
- Agent 任务总量。
- 失败任务数量。
- 失败原因分布。
- LLM 成本和 token 使用。
- 风险事件总量。
- High/Forbidden 风险事件单独列表。
- 合规 guardrail。

### 追溯要求

- 失败原因项返回 `agent_task_run_ids`。
- LLM 成本项返回 `agent_task_run_id`。
- High/Forbidden 风险事件返回 `task_id`、风险等级、严重级别、阻断原因和创建时间。

### 附带修正

修正 `DashboardService.roi_metrics_from_records()` 的 `reply_count` 统计口径：

- 原逻辑：统计所有传入 outreach 回复。
- 修正后：仅统计匹配有效客户集合内的 outreach 回复。
- 目的：避免真实 PostgreSQL 中其他回复记录污染 ROI 指标。

## TDD 记录

### RED

先创建 `apps/api/tests/test_phase2_dashboard_api.py`，覆盖：

- `/dashboard/phase2` 返回来源、任务、成本、失败和风险指标。
- Low/Medium/High/Forbidden 风险分布。
- 审核积压。
- 自动抽取数量。
- 失败原因必须包含可追溯的 `agent_task_run_ids`。
- LLM 成本必须包含可追溯的 `agent_task_run_id`。
- High/Forbidden 风险事件必须单独返回。
- OpenAPI 注册 `/dashboard/phase2`。

首次运行发现测试隔离问题：

```text
duplicate key value violates unique constraint "uq_lead_source_candidates_dedupe_key"
```

根因：

- 测试清理条件使用大写前缀匹配 `normalized_domain`。
- 实际域名为小写，导致历史测试数据未清理。

修正测试隔离后，RED 符合预期：

```text
assert 404 == 200
assert '/dashboard/phase2' in openapi["paths"]
```

失败原因：接口尚未实现和注册。

### GREEN

新增 Phase2 dashboard service、schema、API 路由并注册到 `main.py` 后，目标测试通过：

```text
2 passed
```

## 调试记录

相关回归首次失败：

```text
test_roi_metrics_show_cost_per_effective_lead_reply_and_sales_opportunity
assert summary["reply_count"] == 1
E assert 4 == 1
```

根因：

- `roi_metrics_from_records()` 将所有传入 outreach 回复计入 `reply_count`。
- 真实 PostgreSQL 中存在其他回复记录时，未限定到匹配的 B/C 有效客户集合。

修正：

- 将 `reply_count` 改为只统计 `customer_id` 属于 matched effective customers 的 outreach 回复。

复验：

- 相关回归 `21 passed`。

## 验证结果

### 目标测试

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_phase2_dashboard_api.py
```

结果：`2 passed`。

### 相关后端回归

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_phase2_dashboard_api.py apps/api/tests/test_risk_event_dashboard.py apps/api/tests/test_roi_metrics_api.py apps/api/tests/test_sync_ai_audit_admin_api.py apps/api/tests/test_agent_task_run_model.py apps/api/tests/test_phase2_data_foundation.py
```

结果：`21 passed`。

### 语法检查

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/phase2_dashboard.py apps/api/app/api/phase2_dashboard.py apps/api/app/schemas/phase2_dashboard.py apps/api/app/main.py apps/api/app/services/dashboard.py
```

结果：通过。

## 验收对照

- 来源候选新增指标：通过。
- Low/Medium/High/Forbidden 分布：通过。
- 审核积压：通过。
- 自动抽取数量：通过。
- 失败原因：通过。
- LLM 成本：通过。
- 风险事件：通过。
- 成本和失败可追溯到 `agent_task_runs`：通过。
- High/Forbidden 风险事件单独返回：通过。
- API 可返回第二阶段核心指标：通过。
- 风险指标可单独展示：通过。

## 第一轮独立多维度评审

- 结论：通过，无实质阻塞问题。
- 功能完整性：Phase2 dashboard 已覆盖来源、风险、审核、抽取、任务、失败、成本和 High/Forbidden 风险事件。
- 追溯完整性：成本项和失败原因均保留 `agent_task_run_id`。
- 合规边界：接口只读展示指标，不执行采集、登录、触达或反爬规避。
- 测试覆盖：目标测试覆盖 API 响应、OpenAPI 注册、风险分布、积压、失败原因、成本和高风险事件。
- 发现项：ROI 回复统计被真实库其他回复污染。
- 修正结果：已限定 reply_count 到匹配有效客户集合，回归通过。

## 第二轮独立多维度评审

- 结论：通过，连续两轮未发现新增实质阻塞问题。
- 回归风险：dashboard、风险事件、ROI、同步审计、任务状态机和 Phase2 数据基础相关测试 `21 passed`。
- 数据边界：`channel_prefix` 可用于小范围运行隔离统计，避免后台看板误读其他阶段数据。
- 产品边界：本 Story 只实现 API，不进入管理后台页面开发，未执行下一 Story。
- 范围控制：未做锁操作；未做 git 操作；未执行 `P2-E6-S2`。
- 修正结果：无需新增修正。

## 后续建议

下一 Story 可进入 `P2-E6-S2`，实现管理后台第二阶段运行看板。但本次执行未进入下一 Story。
