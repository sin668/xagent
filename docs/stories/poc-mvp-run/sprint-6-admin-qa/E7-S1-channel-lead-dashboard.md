# Story E7-S1：渠道与线索仪表盘

## 基本信息

- Epic：E7 数据洞察与 ROI
- Sprint：Sprint 6 MVP 管理后台与试运行
- 优先级：P0
- 状态：Done
- 负责人建议：前端工程 + 后端工程 + 管理者

## 用户故事

作为管理者，我希望看到不同渠道的线索数量和有效率，以便决定投入方向。

## 业务价值

让渠道投入基于数据。

## 依赖

- E1-S2 飞书到 PostgreSQL 单向同步

## 任务清单

- [x] 建立渠道统计接口。
- [x] 展示每个渠道采集数量。
- [x] 展示每个渠道 B/C 级线索数。
- [x] 展示每个渠道无效率。
- [x] 标记高风险渠道为研究中或阻断。
- [x] 支持按日期区间过滤。

## 验收标准

- 展示每个渠道采集数量。
- 展示每个渠道 B/C 级线索数。
- 展示每个渠道无效率。
- 高风险渠道显示研究中或阻断状态。

## 非目标

- 不做复杂 BI 自定义报表。

## QA / 风控检查

- [x] 指标口径清晰。
- [x] High/Forbidden 渠道不展示为可投放建议。

## 指标口径

- 采集数量：按 `lead_sources` 中符合日期区间的来源记录数统计。
- B/C 级线索数：按来源关联客户的 `Customer.grade` 分别统计 B、C，并汇总为 `bc_grade_count`。
- 无效数：`Invalid` 与 `Watch` 线索合并计入无效样本。
- 无效率：`invalid_count / candidate_count`，无候选时为 `0`。
- 日期区间：按 `LeadSource.collected_at` 过滤，支持 `date_from` 与 `date_to`。
- 风险状态：`Low/Medium` 为 `active`，`High` 为 `researching`，`Forbidden` 为 `blocked`。
- 投放建议：`High/Forbidden` 固定为 `blocked`，不得展示为可投放建议。

## 实现记录

- 后端新增 `GET /dashboard/channel-leads`，返回总览 summary 与渠道明细。
- 管理后台新增 `apps/admin` Vue3 雏形，首屏对齐原型 `admin-dashboard.html` 的渠道产出表格。
- 后台 service 封装 `buildChannelDashboardView`、`buildDateRangeQuery` 与 `fetchChannelLeadDashboard`，明确 API 契约。

## 验收结果

- 通过：展示每个渠道采集数量。
- 通过：展示每个渠道 B/C 级线索数。
- 通过：展示每个渠道无效率。
- 通过：High 渠道显示为研究中，Forbidden 渠道显示为已阻断。
- 通过：High/Forbidden 渠道 `investment_recommendation` 固定为 `blocked`。
- 通过：支持按日期区间过滤渠道统计。
