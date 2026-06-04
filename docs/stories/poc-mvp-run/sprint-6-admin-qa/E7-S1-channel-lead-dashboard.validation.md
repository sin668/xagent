# E7-S1 Validation：渠道与线索仪表盘

Story：`docs/stories/sprint-6-admin-qa/E7-S1-channel-lead-dashboard.md`

## TDD 记录

- Red：`PYTHONPATH=apps/api pytest -q apps/api/tests/test_channel_lead_dashboard_api.py`
  - 初始失败：`/dashboard/channel-leads` 返回 404。
- Red：`node --test apps/admin/tests/channelDashboard.test.mjs`
  - 初始失败：`apps/admin/src/services/channelDashboard.js` 不存在。
- Green：补齐后端 dashboard API/service/schema、Vue3 管理后台基础页面和 admin service 后，专项测试通过。
- 补强 Red/Green：新增 `fetchChannelLeadDashboard` API 契约测试，先失败于缺少 export，补实现后通过。

## 验收清单

- [x] 建立渠道统计接口。
- [x] 展示每个渠道采集数量。
- [x] 展示每个渠道 B/C 级线索数。
- [x] 展示每个渠道无效率。
- [x] 标记高风险渠道为研究中或阻断。
- [x] 支持按日期区间过滤。
- [x] 指标口径清晰并写回 Story。
- [x] High/Forbidden 渠道不展示为可投放建议。

## 验证命令

- `PYTHONPATH=apps/api pytest -q apps/api/tests/test_channel_lead_dashboard_api.py`
  - 结果：`2 passed, 35 warnings`
- `npm --prefix apps/admin run test`
  - 结果：`4 passed`
- `npm --prefix apps/admin run check:syntax`
  - 结果：通过
- `PYTHONPATH=apps/api pytest -q apps/api/tests/test_channel_lead_dashboard_api.py apps/api/tests/test_channel_risk_api.py apps/api/tests/test_feishu_sync_service.py apps/api/tests/test_customer_dnc_api.py apps/api/tests/test_compliance_review_api.py`
  - 结果：`19 passed, 114 warnings`
- `python -m compileall apps/api/app`
  - 结果：通过
- `npm --prefix apps/mobile run test`
  - 结果：`28 passed`

## 两轮独立评审

### 第一轮评审

- 结论：发现 1 个接口边界问题，修复后复测通过。
- 发现项：日期过滤参数以字符串传入服务层，非法日期会形成服务层异常，不够符合后台查询 API 的输入校验边界。
- 修正结果：API 层改为 `date | None` 查询参数，由 FastAPI/Pydantic 负责请求校验；服务层同时兼容 `date` 与字符串输入。
- 复测：后端专项测试与 `compileall` 通过。

### 第二轮评审

- 结论：未发现新增实质阻塞问题。
- 复核点：采集数量、B/C 口径、无效率、日期过滤、High/Forbidden 风险状态、投放建议阻断、后台 view model 与后端 API 契约。
- 修正结果：补充 `fetchChannelLeadDashboard` 契约封装并通过 admin 测试，作为非阻塞可维护性增强。

## 残留风险

- 管理后台当前以 seed 数据渲染首屏，已提供 API fetch 契约；接真实 API 可在 E8-S1/E8-S3 或联调 Story 中继续推进。
- 现有测试仍有 `datetime.utcnow()` 弃用警告，属于既有技术债，不影响 E7-S1 验收。
