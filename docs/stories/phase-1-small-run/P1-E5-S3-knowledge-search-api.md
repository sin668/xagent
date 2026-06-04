# Story P1-E5-S3：实现知识检索 API

状态：Done  
Sprint：Sprint 3  
优先级：P1  
Epic：P1-E5 知识库 RAG

## 用户故事

作为 Agent 服务，我希望根据任务类型检索相关知识条目，以便给 LLM 提供上下文。

## 业务价值

提高抽取、分级和话术生成的一致性。

## 依赖

- P1-E5-S1

## 实现范围

- 支持按 collection、country、language、channel、query 检索。
- 支持向量检索和关键词 fallback。
- 只返回 approved 条目。

## 数据/API 影响

- 新增 `/knowledge/search` API 或 service。

## 验收标准

- 查询 channel_sop 只返回 approved SOP。
- 查询 faq/script_template 可按语言过滤。
- pgvector 不可用时给出明确错误或使用关键词 fallback。

## 非目标

- 不实现多模型 rerank。

## 风控检查

- 不返回 deprecated 或未审核合规规则。
