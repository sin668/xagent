# E7-S1 渠道与线索仪表盘执行结果

## Story

- `docs/stories/sprint-6-admin-qa/E7-S1-channel-lead-dashboard.md`
- 状态：Done

## 实现范围

- 后端新增渠道线索仪表盘：
  - `GET /dashboard/channel-leads`
  - 支持 `date_from` / `date_to`
  - 输出 summary 与渠道明细
- 指标：
  - 采集数量
  - B 级数量
  - C 级数量
  - B/C 汇总
  - Invalid/Watch 无效数
  - 无效率
  - 风险状态
  - 投放建议
- 管理后台新增：
  - `apps/admin` Vue3 基础结构
  - 渠道产出表格
  - 管理后台 service/view model
  - API fetch 契约封装

## 合规边界

- 未实现自动社交触达。
- High 渠道仅显示为 `researching`。
- Forbidden 渠道显示为 `blocked`。
- High/Forbidden 的 `investment_recommendation` 固定为 `blocked`，不进入可投放建议。

## 验证结果

- `PYTHONPATH=apps/api pytest -q apps/api/tests/test_channel_lead_dashboard_api.py`：`2 passed, 35 warnings`
- `npm --prefix apps/admin run test`：`4 passed`
- `npm --prefix apps/admin run check:syntax`：通过
- `PYTHONPATH=apps/api pytest -q apps/api/tests/test_channel_lead_dashboard_api.py apps/api/tests/test_channel_risk_api.py apps/api/tests/test_feishu_sync_service.py apps/api/tests/test_customer_dnc_api.py apps/api/tests/test_compliance_review_api.py`：`19 passed, 114 warnings`
- `python -m compileall apps/api/app`：通过
- `npm --prefix apps/mobile run test`：`28 passed`

## 两轮评审

### 第一轮

- 结论：发现日期参数校验边界问题，已修复。
- 修正：API 查询参数使用 `date | None`，服务层兼容 `date` 与字符串。
- 复测：后端专项测试通过，Python 编译通过。

### 第二轮

- 结论：未发现新增实质阻塞问题。
- 补强：新增 admin `fetchChannelLeadDashboard` API 契约封装，避免后续页面联调重复拼接 URL。

## 文件清单

- `apps/api/app/api/dashboard.py`
- `apps/api/app/main.py`
- `apps/api/app/schemas/dashboard.py`
- `apps/api/app/services/dashboard.py`
- `apps/api/tests/test_channel_lead_dashboard_api.py`
- `apps/admin/package.json`
- `apps/admin/index.html`
- `apps/admin/src/main.js`
- `apps/admin/src/App.vue`
- `apps/admin/src/data/channelDashboardSeed.js`
- `apps/admin/src/services/channelDashboard.js`
- `apps/admin/src/styles/admin.css`
- `apps/admin/tests/channelDashboard.test.mjs`
- `docs/stories/sprint-6-admin-qa/E7-S1-channel-lead-dashboard.md`
- `docs/stories/sprint-6-admin-qa/E7-S1-channel-lead-dashboard.validation.md`
- `_bmad-output/implementation-artifacts/E7-S1-channel-lead-dashboard-执行结果.md`
