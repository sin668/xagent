# Story P1-E6-S4：实现 LLM 成本与人工复核效率统计

状态：Done  
Sprint：Sprint 4  
优先级：P2  
Epic：P1-E6 指标看板

## 用户故事

作为业务负责人，我希望看到每条有效线索的 LLM 成本和人工复核耗时，以便判断 ROI。

## 业务价值

避免只追数量导致成本失控。

## 依赖

- P1-E1-S5
- P1-E3-S3

## 实现范围

- 统计 LLM 调用次数、token/cost 字段、失败率。
- 统计 staging 创建到复核完成耗时。
- 计算每条 core 有效线索平均成本。

## 数据/API 影响

- 扩展 ai_audit_logs 成本字段。
- 新增 ROI 指标 API。

## 验收标准

- 能按日期和渠道查看 LLM 成本。
- 能查看人工复核平均耗时。
- 能计算每条 core 有效线索平均 AI 成本。

## 非目标

- 不做财务级成本核算。

## 风控检查

- 成本指标不得包含敏感 prompt 原文。

## 验收结果

- 已扩展 `/dashboard/roi-metrics` 为 AI 成本与复核效率统一指标接口。
- 已新增 LLM 调用次数、失败率、token 数、AI 成本总额、平均复核耗时和 AI 单条有效线索成本。
- 已扩展 `ai_audit_logs` schema，保留成本与 token 字段。
- 已保留原有 ROI 成本统计口径，不破坏现有指标。
