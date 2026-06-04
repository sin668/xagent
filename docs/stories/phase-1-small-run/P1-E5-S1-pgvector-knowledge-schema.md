# Story P1-E5-S1：创建 PostgreSQL + pgvector 知识库表

状态：Done  
Sprint：Sprint 3  
优先级：P1  
Epic：P1-E5 知识库 RAG

## 用户故事

作为 AI 负责人，我希望知识库和业务数据统一放在 PostgreSQL 中，以便 Agent 可检索已审核知识。

## 业务价值

为 LLM 抽取、分级、话术和合规提示提供可控上下文。

## 依赖

- P1-E1-S1

## 实现范围

- 新增 `knowledge_collections`、`knowledge_items`、`knowledge_embeddings`。
- 支持 status、review_status、version、source_ref。
- 配置 pgvector embedding 字段。

## 数据/API 影响

- 新增知识库 CRUD API。

## 验收标准

- 只有 approved 知识可被生产检索。
- deprecated 知识不得进入 RAG。
- embedding 写入失败不影响结构化知识保存，但要记录错误。

## 非目标

- 不做复杂知识图谱。

## 风控检查

- 合规规则不可仅作为语义建议，仍需结构化规则执行。
