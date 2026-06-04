# P1-E6-S4 执行结果

## 基本信息

- Story：`docs/stories/phase-1-small-run/P1-E6-S4-llm-cost-review-efficiency.md`
- 状态：Done
- 执行目标：实现 LLM 成本与人工复核效率统计

## 修改文件

- `apps/api/app/models/ai_audit_log.py`
- `apps/api/app/services/audit_risk.py`
- `apps/api/app/services/dashboard.py`
- `apps/api/app/services/sync_audit_dashboard.py`
- `apps/api/app/services/llm_lead_extraction.py`
- `apps/api/app/services/llm_lead_grading.py`
- `apps/api/app/schemas/dashboard.py`
- `apps/api/app/schemas/sync.py`
- `apps/api/alembic/versions/20260529_0019_llm_cost_review_efficiency.py`
- `apps/api/tests/test_llm_cost_review_efficiency.py`
- `docs/stories/phase-1-small-run/P1-E6-S4-llm-cost-review-efficiency.md`

## 实现内容

- 扩展 `ai_audit_logs` 模型与迁移，新增：
  - `channel_name`
  - `input_tokens`
  - `output_tokens`
  - `total_tokens`
  - `cost_amount`
  - `cost_currency`
- 扩展 `record_ai_audit`，可写入 token 与成本字段。
- 把 LLM 抽取/分级审计补上 `channel_name`，便于 ROI 与后台按渠道过滤。
- 扩展 `/dashboard/roi-metrics`：
  - 保留原有 ROI 总成本统计
  - 新增 LLM 调用次数、失败率、token 数、LLM 成本总额
  - 新增 staging 复核平均耗时
  - 新增 AI 单条有效线索成本
- 扩展同步审计看板中的 AI 日志字段，便于后台观察。

## 测试与验证

- `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_cost_review_efficiency.py -q`
- `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_cost_review_efficiency.py apps/api/tests/test_audit_risk_logs_foundation.py -q`
- `/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/models/ai_audit_log.py apps/api/app/services/audit_risk.py apps/api/app/services/dashboard.py apps/api/app/schemas/dashboard.py apps/api/app/services/sync_audit_dashboard.py apps/api/app/schemas/sync.py apps/api/alembic/versions/20260529_0019_llm_cost_review_efficiency.py`
- `cd apps/api && /opt/miniconda3/envs/booking-room/bin/python -m alembic heads`

### 结果

- `test_llm_cost_review_efficiency.py`：2 passed
- 相关纯契约测试：7 passed
- `py_compile`：通过
- `alembic heads`：`20260529_0019 (head)`

## 验收结果

- 已按日期和渠道查看 LLM 成本与复核效率。通过。
- 已看到人工复核平均耗时。通过。
- 已看到每条 core 有效线索平均 AI 成本。通过。
- 已扩展 ai_audit_logs 成本字段。通过。

## 风控检查

- 成本指标未包含 prompt 原文。通过。
- 新增字段仅用于审计与统计，不影响触达逻辑。通过。

## 两轮评审记录

### 第一轮：规格符合性

- 结论：通过。
- 发现项：
  - `ai_audit_logs` 需要补字段迁移，否则指标只能停留在内存层。
- 修正：
  - 新增 0019 迁移并同步模型与审计写入接口。

### 第二轮：代码质量与回归

- 结论：通过。
- 发现项：
  - 初版把原有 `reply_count` 误接到 AI 审计上，会破坏旧 ROI 口径。
- 修正：
  - 恢复 `reply_count` 的外联回复口径，并补纯测试覆盖。

## 残留风险

- `apps/api/tests/test_roi_metrics_api.py` 仍依赖真实 PostgreSQL，当前沙箱连接 `8.129.17.71:5432` 会被 `PermissionError` 拦截，因此未完成真实库回归。

## 下一步

- 继续执行 `docs/stories/phase-1-small-run/` 下下一条未完成 Story。
