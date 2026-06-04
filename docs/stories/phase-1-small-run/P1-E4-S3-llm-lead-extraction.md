# Story P1-E4-S3：实现 LLM 线索抽取任务

状态：Done  
Sprint：Sprint 3  
优先级：P0  
Epic：P1-E4 Agent 任务流

## 用户故事

作为线索运营，我希望 LLM 从公开文本中抽取结构化客户信息，以便进入 staging 复核。

## 业务价值

减少俄语网页人工阅读和整理成本。

## 依赖

- P1-E1-S4
- P1-E1-S5
- P1-E4-S2

## 实现范围

- 调用 lead extraction prompt。
- 输出符合 schema 的 JSON。
- 写入 staging_leads。
- 写入 ai_audit_logs。

## 数据/API 影响

- 新增 LLM extraction service。

## 验收标准

- 输出包含客户名称、国家、城市、客户类型、联系方式、经营信号、来源证据。
- 缺失字段为 Unknown/null/[]。
- 不允许编造联系方式。
- 输出 JSON schema 校验失败时不得写入 staging，需记录失败案例。

## 非目标

- 不做自动触达。

## 风控检查

- 每条抽取结果必须关联 source_url 和 evidence_note。
