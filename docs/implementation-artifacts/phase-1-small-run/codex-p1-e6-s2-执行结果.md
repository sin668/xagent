# P1-E6-S2 执行结果

Story：`docs/stories/phase-1-small-run/P1-E6-S2-channel-quality-metrics.md`  
执行人：Codex  
执行日期：2026-05-29  
状态：已完成本地实现、TDD、定向回归、编译检查、两轮复核和 Story 状态回写

## 1. 执行说明

本 Story 按 `docs/AI协同开发执行标准.md`、第一阶段实施推进计划和 superpowers TDD 规范执行。用户已明确要求不执行 Story lock 操作，因此本 Story 未执行任何锁命令。

## 2. 修改文件

- `apps/api/app/services/dashboard.py`
- `apps/api/app/schemas/dashboard.py`
- `apps/api/app/api/dashboard.py`
- `apps/api/tests/test_channel_quality_metrics.py`
- `docs/stories/phase-1-small-run/P1-E6-S2-channel-quality-metrics.md`
- `_bmad-output/implementation-artifacts/codex-p1-e6-s2-执行结果.md`

## 3. 实现内容

### 3.1 渠道质量指标

新增 `DashboardService.channel_quality_metrics` 和纯聚合口径 `channel_quality_from_records`，按渠道输出：

- 候选 URL 数
- staging 线索数
- core 客户数
- A/B/C/Invalid/Watch 数
- B/C 级占比
- Invalid/Watch 数
- 联系方式完整率
- 证据完整率
- 重复数和重复率
- High 二次复核要求数、通过数、通过率
- 风险事件数和建议暂停数
- 渠道质量结论

### 3.2 API

新增：

```text
GET /dashboard/channel-quality
```

支持查询参数：

- `date_from`
- `date_to`
- `channel`
- `risk_level`

### 3.3 风控口径

- High 渠道默认结论为 `policy_research`。
- Forbidden 渠道默认结论为 `forbidden`。
- 出现建议暂停风险事件时，渠道结论为 `pause_or_review`。
- 渠道质量指标仅用于调整配额，不得绕过 High/Forbidden、二次复核、勿扰和合规复核规则。

## 4. 验收结果

| 验收项 | 结论 | 证据 |
|---|---|---|
| 统计各渠道候选 | 通过 | `candidate_url_count` |
| 统计各渠道 staging | 通过 | `staging_lead_count` |
| 统计各渠道 core | 通过 | `core_customer_count` |
| 统计 B/C 比例 | 通过 | `bc_grade_count` + `bc_rate` |
| 统计 Invalid/Watch | 通过 | `invalid_watch_count` |
| 展示联系方式完整率 | 通过 | `contact_completeness_rate` |
| 展示证据完整率 | 通过 | `evidence_completeness_rate` |
| 展示重复率 | 通过 | `duplicate_count` + `duplicate_rate` |
| 区分 Low/Medium/High/Quality 渠道 | 通过 | `risk_category` + `quality_conclusion` |
| 展示 High 二次复核通过率 | 通过 | `high_secondary_review_pass_rate` |
| 风险事件与渠道指标关联展示 | 通过 | `risk_event_count` + `pause_suggested_count` |
| 不做自动预算优化 | 通过 | 仅输出指标和结论，不改配额或预算 |

## 5. TDD 记录

### 5.1 RED

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_channel_quality_metrics.py -q
```

结果：

```text
AttributeError: type object 'DashboardService' has no attribute 'channel_quality_from_records'
```

并确认 API 合约缺失：

```text
assert '@router.get("/channel-quality"' in api_file.read_text(...)
```

### 5.2 实现后测试

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_channel_quality_metrics.py -q
```

结果：

```text
2 passed
```

## 6. 回归验证

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/dashboard.py apps/api/app/schemas/dashboard.py apps/api/app/api/dashboard.py
```

结果：通过。

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_channel_quality_metrics.py apps/api/tests/test_phase_one_funnel_dashboard.py -q
```

结果：

```text
5 passed
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

### 7.1 第一轮：渠道边界和 High 风险筛选评审

结论：通过，发现一个渠道兼容性问题。

发现项：

- `channel-quality` 可能需要展示 VK/Facebook 这类只出现在风险事件或渠道规则里的 High/Forbidden 渠道，但 `SourcePlatform` 枚举没有这些值。
- 直接用 `SourcePlatform(channel)` 会导致这类渠道筛选时报错。

修正结果：

- 新增 `source_platform_filter_value`。
- 当渠道不属于 `SourcePlatform` 时，候选/staging/core 查询返回空集合，但风险事件仍按字符串渠道过滤。
- API `channel` 参数允许 `vkontakte` 和 `facebook`。

### 7.2 第二轮：指标口径和风控关联评审

结论：通过，无新增实质阻塞问题。

发现项：

- 重复率应基于重复 key 的超额数量或已标记 duplicate 的数量，不能只看是否有 dedupe_key。
- High 二次复核通过率必须明确分母和分子。
- 风险事件必须能影响渠道质量结论。

修正结果：

- `duplicate_count` 使用 `max(duplicate_review_count, duplicate_key_excess)`。
- High 二次复核通过率使用 `approved high staging / high secondary required candidates`。
- `pause_suggested_count > 0` 时渠道结论为 `pause_or_review`。

## 8. 残留风险

- 本次 Story 未新增数据库表或 migration。
- 当前 Codex 沙箱无法连接真实 PostgreSQL，因此 `/dashboard/channel-quality` 的真实库端到端接口验证需在可出网环境复验。
- 渠道质量结论为运营辅助判断，不做自动预算优化或自动配额调整。

## 9. 下一步建议

继续执行：

`docs/stories/phase-1-small-run/P1-E6-S3-risk-event-dashboard.md`
