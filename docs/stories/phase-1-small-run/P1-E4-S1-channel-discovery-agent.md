# Story P1-E4-S1：实现渠道发现 Agent 任务

状态：Done  
Sprint：Sprint 3  
优先级：P0  
Epic：P1-E4 Agent 任务流

## 用户故事

作为线索运营，我希望 Agent 根据渠道计划自动生成候选 URL，以便每天稳定发现候选线索。

## 业务价值

支撑每日 100 条候选线索目标。

## 依赖

- P1-E1-S2
- P1-E2-S1

## 实现范围

- 根据 channel_plan 生成 search_task。
- 支持关键词、城市、渠道类型。
- 输出候选 URL 和发现理由。
- 写入 collection_tasks 和 candidate_urls。

## 数据/API 影响

- 新增 run channel discovery API 或脚本入口。

## 验收标准

- 不超过 channel_plan daily_url_limit。
- Forbidden 计划不执行。
- High 计划只生成 public_discovery_only 候选。
- 所有候选 URL 幂等写入。

## 非目标

- 不实现登录平台检索。
- 不绕过搜索引擎限制。

## 风控检查

- 不生成私信、加好友、入群任务。
