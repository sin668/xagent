# 海外车辆采购 AI 获客系统 Story 文件索引

创建日期：2026-05-26

本目录按照已确认的 BMAD Sprint 规划拆分 Story 文件，用于后续排期、派工、研发、运营执行和验收。

## 执行原则

- 第一阶段市场为俄罗斯。
- 主攻客户为当地车商/二级经销商。
- 车辆品类为二手车、准新车、库存车。
- PoC 使用飞书表格跑通业务闭环。
- MVP 使用移动端优先工作台、管理后台、FastAPI、PostgreSQL 和飞书单向同步。
- AI 负责去重、补全信息、初筛、打标签和话术草稿，不直接替代人工触达和业务判断。
- 禁止自动社交私信、自动加好友、登录后批量采集、反爬规避和无审计 AI 决策。

## Sprint 目录

| Sprint | 目录 | 阶段目标 |
|---|---|---|
| Sprint 0 | `sprint-0-poc-prep` | 搭建 PoC 运营底座 |
| Sprint 1 | `sprint-1-poc-collection` | 完成首批采集与 AI 清洗 |
| Sprint 2 | `sprint-2-poc-outreach-retro` | 完成人工触达和 PoC 复盘 |
| Sprint 3 | `sprint-3-mvp-data` | 搭建 MVP 数据底座 |
| Sprint 4 | `sprint-4-mobile-workbench` | 实现移动端线索工作台 |
| Sprint 5 | `sprint-5-business-loop` | 打通触达、车源、合规复核 |
| Sprint 6 | `sprint-6-admin-qa` | 完成管理后台、仪表盘和试运行 |
| Backlog | `backlog` | MVP 后续增强 |

## 质量门

每个 Story 进入 Done 前必须确认：

- 来源证据已保留。
- AI 输入、输出、模型、时间和执行结果可追踪。
- High/Forbidden 渠道未进入自动任务。
- 勿扰客户不会再次进入触达队列。
- C 级线索报价或合同前保留合规复核节点。
- 客服、出口销售或管理者能理解并使用交付物。

