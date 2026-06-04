# Story P1-E5-S2：导入第一阶段知识集合

状态：Done  
Sprint：Sprint 3  
优先级：P1  
Epic：P1-E5 知识库 RAG

## 用户故事

作为线索运营，我希望关键词、渠道 SOP、FAQ、话术模板、合规规则和失败案例进入知识库，以便 Agent 使用统一上下文。

## 业务价值

减少散落文档和 prompt 漂移。

## 依赖

- P1-E5-S1
- 现有 docs/poc 文档

## 实现范围

- 从现有 markdown/Excel/seed 数据导入 knowledge_items。
- 建立 collection：channel_sop、faq、script_template、keyword_library、vehicle_knowledge、compliance_rules、failed_cases。
- 设置初始 review_status。

## 数据/API 影响

- 新增导入脚本或管理后台导入入口。

## 验收标准

- 至少导入渠道 SOP、俄罗斯关键词库、FAQ/话术、失败案例。
- 每条知识有 collection、title、body、language、country、source_ref。
- 未审核知识不得进入生产 Agent。

## 非目标

- 不要求一次性导入所有历史文档。

## 风控检查

- 触达话术必须保留禁止承诺点和拒绝联系路径。
