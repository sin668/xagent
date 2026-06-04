# Story E7-S2：触达与 SLA 仪表盘

## 基本信息

- Epic：E7 数据洞察与 ROI
- Sprint：Sprint 6 MVP 管理后台与试运行
- 优先级：P0
- 状态：Done
- 负责人建议：前端工程 + 后端工程 + 客服负责人

## 用户故事

作为管理者，我希望看到触达回复和 SLA 超时，以便发现承接瓶颈。

## 业务价值

避免线索交付后无人跟进。

## 依赖

- E4-S2 触达记录

## 任务清单

- [x] 统计已触达数、回复数、回复率。
- [x] 定义 B 级 48 小时 SLA。
- [x] 定义 C 级 24 小时 SLA。
- [x] 展示超时数量和待处理队列。
- [x] 支持按负责人、等级、渠道过滤。
- [x] 生成 SLA 风险提醒。

## 验收标准

- 展示已触达数、回复数、回复率。
- 展示 B 级 48 小时 SLA 和 C 级 24 小时 SLA。
- 展示超时数量和待处理队列。

## 非目标

- 不做销售绩效奖金计算。

## QA / 风控检查

- [x] 勿扰客户不计入待触达 SLA。
- [x] C 级线索需区分合规复核等待时间。

## 指标口径

- 已触达数：`OutreachRecord.status` 属于 `sent/replied/rejected/no_response/bad_contact` 的记录数。
- 回复数：`OutreachRecord.status = replied` 的记录数。
- 回复率：`replied_count / sent_count`，无已触达记录时为 `0`。
- SLA 计时起点：客户 `updated_at`，代表线索进入当前承接队列或最近状态更新时间。
- B 级 SLA：48 小时。
- C 级 SLA：24 小时。
- 待处理队列：B/C 级、非勿扰、状态为可交付/跟进中的客户。
- SLA 风险：`overdue` 与 `compliance_waiting` 计入风险提醒。
- C 级合规等待：C 级线索未通过合规复核时展示为 `compliance_waiting`，与普通超时区分。
- 过滤：支持按负责人 `owner`、等级 `grade`、触达渠道 `channel` 过滤；渠道过滤同时作用于触达统计和待处理队列。

## 实现记录

- 后端新增 `GET /dashboard/outreach-sla`。
- 管理后台新增触达与 SLA 卡片，展示已触达、回复、回复率、SLA 风险和风险队列。
- Admin service 新增 `buildOutreachSlaDashboardView`、`buildOutreachSlaQuery`、`fetchOutreachSlaDashboard`。

## 验收结果

- 通过：展示已触达数、回复数、回复率。
- 通过：展示 B 级 48 小时、C 级 24 小时 SLA。
- 通过：展示超时数量、合规等待数量和待处理队列。
- 通过：勿扰客户不计入待触达 SLA。
- 通过：C 级合规等待与普通超时区分。
- 通过：支持按负责人、等级、渠道过滤。
