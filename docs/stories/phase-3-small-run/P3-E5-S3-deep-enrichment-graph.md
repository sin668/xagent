# Story P3-E5-S3：实现 Deep Enrichment LangGraph 图流程

状态：实现完成
Sprint：Sprint 5
优先级：P1
Epic：P3-E5

## 用户故事

作为第三阶段小范围运行的研发执行者，我希望完成“实现 Deep Enrichment LangGraph 图流程”，以便系统可以按 BMAD 已冻结方案推进线索完善、客户晋级、客户承接、清洗治理和 LangGraph 局部试点闭环。

## 上下文来源

- `docs/brainstorm/brainstorming-session-2026-06-04-第三阶段小范围运行-客户管理工作台.md`
- `docs/product/2026-06-04-海外车辆采购AI获客系统-第三阶段小范围运行方案与产品技术设计.md`
- `docs/architecture/2026-06-03-LLM-Agent服务编排选型分析.md`
- `prototypes/mvp-mobile-agent/design-brief.md`
- `docs/AI协同开发执行标准.md`
- `agents.md`

## Story 定义

**目标：** 用 LangGraph 表达人工触发深挖线索的多步骤流程。

**Files:**

- Create: `apps/agents/app/graphs/deep_enrichment.py`
- Create: `apps/agents/app/tools/public_search.py`
- Create: `apps/agents/app/tools/evidence_validator.py`
- Test: `apps/agents/tests/test_deep_enrichment_graph.py`

**Codex 提示词：**

```text
请执行 P3-E5-S3：实现 Deep Enrichment LangGraph 图流程。

要求：
1. 使用 superpowers:test-driven-development。
2. 严格依据第三阶段方案和本 Story 验收标准实现。
3. 保持 raw/staging/core/audit 分层，不让 AI 直接污染 core 数据。
4. 所有关键动作必须保留来源证据、操作人、时间和审计记录。
5. 不自动社交私信、不自动加好友、不自动发送触达消息。
6. 运行本 Story 对应测试，并按需执行相关联调验证。
7. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p3-e5-s3-执行结果.md。
8. 不要执行下一个 Story。
```

**验收标准：**

- 图节点包含 load_lead、build_keywords、search_public_sources、read_public_pages、extract_candidates、validate_evidence、write_enrichment_candidates、recommend_action。
- 单元测试使用 mock LLM/search。
- 输出不直接写 customers。
- 缺失字段输出 Unknown/null/[]。

**非目标：**

- 不接真实网络搜索作为必需测试。

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作。
- 不做 git 操作。
- 代码实现 Story 必须使用 `superpowers:test-driven-development`。
- 调试异常必须使用 `superpowers:systematic-debugging`。
- 完成前必须使用 `superpowers:verification-before-completion`。
- 完成后必须执行两轮独立多维度评审，并记录结论、发现项和修正结果。
- 必须执行必要的前后端真实联调，不允许只验证 seed 静态页面。
- 所有过程、结果、注解和文档使用中文。


## 通用风控边界

- 不自动社交私信。
- 不自动加好友。
- 不登录后批量采集。
- 不反爬规避。
- 不抓取非公开数据。
- High 来源未审核不得进入自动触达。
- Forbidden 来源不得作为客户晋级关键来源。
- Invalid 和 Watch 不进入触达队列。
- 勿扰客户不得再次进入触达队列。
- C 级客户报价、合同、付款、物流、清关、交付周期等动作前必须合规复核。
- 所有 AI 输出必须保存来源证据、prompt 版本、模型和审计记录。
- Agent 不得自动晋级客户、自动归并客户、自动恢复 Invalid、自动触达客户。

## 执行记录

执行结果文件：

- `_bmad-output/implementation-artifacts/codex-p3-e5-s3-执行结果.md`

验收结果：

- 已创建 `apps/agents/app/graphs/deep_enrichment.py`。
- 已创建 `apps/agents/app/tools/public_search.py`。
- 已创建 `apps/agents/app/tools/evidence_validator.py`。
- 已创建 `apps/agents/tests/test_deep_enrichment_graph.py`。
- Deep Enrichment 图节点包含 `load_lead`、`build_keywords`、`search_public_sources`、`read_public_pages`、`extract_candidates`、`validate_evidence`、`write_enrichment_candidates`、`recommend_action`。
- 单元测试使用 mock search 和 mock LLM extractor，不依赖真实网络搜索。
- 输出使用 `DeepEnrichmentAgentOutput`，只写入 `lead_enrichment_field_candidates` 协议，不直接写 `customers`。
- 缺失字段候选支持 `Unknown` 和 `[]`，并且 `Unknown/null/[]` 不会被视为已补全字段。
- 已阻断 `auto_dm`、`friend_request`、`login_collection`、`anti_scraping_bypass` 等违规动作。
- 已运行当前 Story 测试、`apps/agents` 全量测试、Agent 编译检查、`apps/api` 轻量回归和 API 编译检查。
