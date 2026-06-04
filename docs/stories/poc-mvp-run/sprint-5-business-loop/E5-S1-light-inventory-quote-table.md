# Story E5-S1：维护轻量车源/报价表

## 基本信息

- Epic：E5 车源/报价匹配
- Sprint：Sprint 5 MVP 业务闭环
- 优先级：P0
- 状态：Done
- 负责人建议：出口销售 + 后端工程

## 用户故事

作为出口销售，我希望系统里有可用车源和报价信息，以便客户回复后快速匹配。

## 业务价值

避免“有客户但无内容可回”的断点。

## 依赖

- E0-S1 创建飞书五张表
- E1-S2 飞书到 PostgreSQL 单向同步

## 任务清单

- [x] 设计轻量车源/报价数据结构。
- [x] 支持品牌、车型、年份、里程、车况、配置、价格、可出口状态、图片/视频、有效期。
- [x] 同步或录入轻量车源数据。
- [x] 对过期车源给出明显提示。
- [x] 标注价格确认状态。
- [x] 防止 AI 将未经确认价格当成承诺输出。

## 验收标准

- 车源字段包含品牌、车型、年份、里程、车况、配置、价格、可出口状态、图片/视频、有效期。
- 过期车源有明显提示。
- 未经确认的价格不能被 AI 当成承诺输出。

## 非目标

- MVP 不接 ERP/库存系统。

## QA / 风控检查

- [x] 未确认价格不得外发。
- [x] 过期车源不得推荐为优先报价。

## 交付说明

- 后端新增轻量车源 API：`POST /inventory/items`、`GET /inventory/items`、`GET /inventory/items/{external_id}/ai-quote-safety`。
- PostgreSQL `inventory_items` 新增 `configuration`、`media_urls`、`valid_until`，覆盖配置、图片/视频和有效期。
- 服务层统一计算 `is_expired`、`can_ai_quote`、`priority_recommendable`、`risk_flags` 和 AI 报价阻断原因。
- 移动端新增 `pages/inventory/index`，对齐 MVP 原型的车源匹配页面，展示车源、价格状态、有效期和 AI 报价阻断提示。
- MVP 不接 ERP/库存系统；当前支持 API 录入和后续飞书同步承接。
