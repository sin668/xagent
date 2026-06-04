# P1-E6-S1 执行结果

Story：`docs/stories/phase-1-small-run/P1-E6-S1-daily-funnel-dashboard.md`  
执行人：Codex  
执行日期：2026-05-29  
状态：已完成本地实现、TDD、定向回归、编译检查、两轮复核和 Story 状态回写

## 1. 执行说明

本 Story 按 `docs/AI协同开发执行标准.md`、第一阶段实施推进计划和 superpowers TDD 规范执行。用户已明确要求不执行 Story lock 操作，因此本 Story 未执行任何锁命令。

## 2. 修改文件

- `apps/api/app/services/dashboard.py`
- `apps/api/app/schemas/dashboard.py`
- `apps/api/app/api/dashboard.py`
- `apps/api/tests/test_phase_one_funnel_dashboard.py`
- `docs/stories/phase-1-small-run/P1-E6-S1-daily-funnel-dashboard.md`
- `_bmad-output/implementation-artifacts/codex-p1-e6-s1-执行结果.md`

## 3. 实现内容

### 3.1 每日运行漏斗指标

新增 `DashboardService.phase_one_funnel_metrics` 和纯聚合口径 `phase_one_funnel_from_records`，统计：

- `candidate_url_count`
- `staging_lead_count`
- `core_customer_count`
- `core_valid_lead_count`
- `touchable_effective_lead_count`
- `high_readonly_excluded_count`
- `do_not_contact_excluded_count`
- `daily_candidate_target`
- `candidate_target_completion_rate`
- `candidate_target_met`

### 3.2 API

新增：

```text
GET /dashboard/phase-one-funnel
```

支持查询参数：

- `date_from`
- `date_to`
- `channel`
- `risk_level`
- `daily_candidate_target`

### 3.3 风控口径

- B/C 计入 `core_valid_lead_count`。
- High/Forbidden 来源只读或政策研究结果不计入 `touchable_effective_lead_count`。
- 勿扰客户不计入 `touchable_effective_lead_count`。
- 输出 `guardrail` 明示 High/Forbidden 不得计入可触达有效线索。

## 4. 验收结果

| 验收项 | 结论 | 证据 |
|---|---|---|
| 统计 candidate_urls | 通过 | `candidate_url_count` |
| 统计 staging_leads | 通过 | `staging_lead_count` |
| 统计 core customers | 通过 | `core_customer_count` |
| 展示每日候选线索约 100 的完成情况 | 通过 | `daily_candidate_target` + `candidate_target_completion_rate` + `candidate_target_met` |
| 展示 core 有效线索数量 | 通过 | `core_valid_lead_count` |
| 展示可触达有效线索数量 | 通过 | `touchable_effective_lead_count` |
| 支持日期过滤 | 通过 | `date_from` / `date_to` |
| 支持渠道过滤 | 通过 | `channel` |
| 支持风险等级过滤 | 通过 | `risk_level` |
| 能按渠道查看贡献 | 通过 | `channels` 明细 |
| High 只读结果不得计入可触达有效线索 | 通过 | `high_readonly_excluded_count` + 测试覆盖 |

## 5. TDD 记录

### 5.1 RED

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_phase_one_funnel_dashboard.py -q
```

结果：

```text
AttributeError: type object 'DashboardService' has no attribute 'phase_one_funnel_from_records'
```

并确认 API 合约缺失：

```text
assert '@router.get("/phase-one-funnel"' in api_file.read_text(...)
```

### 5.2 实现后测试

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_phase_one_funnel_dashboard.py -q
```

结果：

```text
3 passed
```

## 6. 回归验证

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/dashboard.py apps/api/app/schemas/dashboard.py apps/api/app/api/dashboard.py
```

结果：通过。

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_phase_one_funnel_dashboard.py apps/api/tests/test_rag_in_llm_prompts.py -q
```

结果：

```text
7 passed, 1 warning
```

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m alembic heads
```

结果：

```text
20260529_0018 (head)
```

## 7. 两轮独立评审

### 7.1 第一轮：漏斗口径和健壮性评审

结论：通过，发现一个非阻塞健壮性问题。

发现项：

- `source.collected_at` 的 fallback 写法会提前求值 `customer.created_at`，虽然真实模型存在该字段，但写法不够稳。

修正结果：

- 改为 `getattr(source, "collected_at", None) or getattr(customer, "created_at")`。
- 修正后重新执行编译和目标测试，结果通过。

### 7.2 第二轮：API 合约和风控口径评审

结论：通过，无新增实质阻塞问题。

发现项：

- API 需要明确查询参数和响应模型。
- High/Forbidden、勿扰客户必须从可触达有效线索中排除。
- 指标应支持按渠道和风险等级查看贡献。

修正结果：

- 新增 `PhaseOneFunnelDashboardResponse` 及子结构。
- 新增 `/dashboard/phase-one-funnel` 路由。
- `touchable_effective_lead_count` 明确排除 High/Forbidden 与勿扰客户，测试覆盖。

## 8. 残留风险

- 本次 Story 未新增数据库表或 migration。
- 当前 Codex 沙箱无法连接真实 PostgreSQL，因此 `/dashboard/phase-one-funnel` 的真实库端到端接口验证需在可出网环境复验。
- 目前指标为小范围运行漏斗，不替代完整 BI。

## 9. 下一步建议

继续执行：

`docs/stories/phase-1-small-run/P1-E6-S2-channel-quality-metrics.md`
