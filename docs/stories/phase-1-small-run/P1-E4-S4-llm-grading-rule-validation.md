# Story P1-E4-S4：实现 LLM 分级与规则校验任务

状态：Done  
Sprint：Sprint 3  
优先级：P0  
Epic：P1-E4 Agent 任务流

## 用户故事

作为线索运营，我希望系统给出 A/B/C/Invalid/Watch 建议并执行规则校验，以便更快筛选有效线索。

## 业务价值

提升复核优先级排序，减少无效线索进入人工队列。

## 依赖

- P1-E4-S3
- P1-E2-S2

## 实现范围

- 调用 lead grading prompt。
- 结合规则校验渠道风险、联系方式、证据、勿扰、C 级复核。
- 更新 staging_leads 推荐等级和 queue_status。

## 数据/API 影响

- 新增 grading service。
- 写入 ai_audit_logs 和 rule validation result。

## 验收标准

- Invalid/Watch queue_status 必须为 not_eligible。
- High 未二次复核 queue_status 必须为 blocked 或 needs_secondary_verification。
- C 级 requires_compliance_review=true。
- 推荐原因必须引用证据。

## 非目标

- 不做黑箱评分模型。

## 风控检查

- LLM 推荐不得覆盖硬规则阻断。
