# Story P1-E4-S5：实现 Agent 失败案例记录

状态：Done  
Sprint：Sprint 3  
优先级：P1  
Epic：P1-E4 Agent 任务流

## 用户故事

作为 AI/Agent 操作人员，我希望任务失败、schema 错误、无证据输出和风险阻断被记录，以便优化 prompt 和渠道策略。

## 业务价值

建立质量反馈闭环。

## 依赖

- P1-E1-S5
- P1-E4-S3
- P1-E4-S4

## 实现范围

- 记录 failed_cases。
- 分类失败原因：fetch_failed、schema_invalid、missing_evidence、risk_blocked、duplicate、llm_suspected_fabrication。
- 支持后台查询。

## 数据/API 影响

- 新增 failed_cases 表或复用 knowledge failed_cases 集合。

## 验收标准

- schema 校验失败必须有失败记录。
- 疑似编造必须有风险事件或失败案例。
- 失败案例可用于后续知识库 RAG。

## 非目标

- 不自动修复 prompt。

## 风控检查

- 失败记录不能把无效线索推进触达队列。
