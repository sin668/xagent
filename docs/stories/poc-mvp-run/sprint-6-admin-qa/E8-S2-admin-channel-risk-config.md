# Story E8-S2：渠道风险配置后台

## 基本信息

- Epic：E8 管理后台
- Sprint：Sprint 6 MVP 管理后台与试运行
- 优先级：P0
- 状态：Done
- 负责人建议：前端工程 + 后端工程 + 合规/风控

## 用户故事

作为合规负责人，我希望在后台维护渠道风险规则。

## 业务价值

让风险规则可配置，而不是写死在代码里。

## 依赖

- E6-S1 渠道风险等级配置

## 任务清单

- [x] 实现渠道风险配置列表。
- [x] 支持查看所有渠道及风险等级。
- [x] 支持维护允许动作、禁止动作和政策来源。
- [x] 配置变更记录操作人和时间。
- [x] High/Forbidden 渠道被自动任务阻断。
- [x] 展示阻断原因。

## 验收标准

- 可查看所有渠道及风险等级。
- 可维护允许动作、禁止动作和政策来源。
- High/Forbidden 渠道被自动任务阻断。

## 非目标

- 不自动抓取平台政策更新。

## QA / 风控检查

- [x] 修改风险等级需留痕。
- [x] Forbidden 行为不能通过前端绕过。

## 实现记录

- 新增迁移 `20260528_0008_add_channel_risk_updated_by.py`，为 `channel_risk_rules` 增加 `updated_by` 字段。
- `PUT /channel-risks/{channel_name}` 支持维护允许动作、禁止动作、政策来源、备注、操作人，并返回 `updated_by` 与 `updated_at`。
- 服务层强制 High/Forbidden 渠道 `collection_allowed = false`、`ai_processing_allowed = false`，即使前端 payload 传入 `collection_allowed: true` 也不能绕过。
- `POST /channel-risks/evaluate-ai-task` 继续对 High/Forbidden 和命中禁止动作的任务返回阻断，并写入 AI 审计日志与阻断原因。
- 管理后台新增渠道风险配置区块，展示风险等级、允许动作、禁止动作、政策来源、变更人和阻断原因。

## 验收结果

- 通过：可查看所有渠道及风险等级。
- 通过：可维护允许动作、禁止动作和政策来源。
- 通过：配置变更记录操作人和时间。
- 通过：High/Forbidden 渠道被自动任务阻断。
- 通过：Forbidden 行为不能通过前端绕过。
