# Story P1-E6-S1：实现每日运行漏斗指标

状态：Done  
Sprint：Sprint 4  
优先级：P1  
Epic：P1-E6 指标看板

## 用户故事

作为业务负责人，我希望看到每日候选 URL、staging 线索和 core 有效线索，以便判断小范围运行是否达标。

## 业务价值

支撑 Go/No-Go 主指标：有效线索数量。

## 依赖

- P1-E1-S2
- P1-E1-S4
- P1-E3-S3

## 实现范围

- 统计 candidate_urls、staging_leads、core customers。
- 支持按日期、渠道、风险等级过滤。
- 管理后台展示漏斗。

## 数据/API 影响

- 新增 `/dashboard/phase-one-funnel` API。

## 验收标准

- 能展示每日候选线索约 100 的完成情况。
- 能展示 core 有效线索数量。
- 能按渠道查看贡献。

## 非目标

- 不做完整 BI。

## 风控检查

- High 只读结果不得计入可触达有效线索。
