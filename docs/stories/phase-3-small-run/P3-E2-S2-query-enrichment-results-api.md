# Story P3-E2-S2：实现线索补全结果和字段候选查询 API

状态：实现完成，真实 PostgreSQL API 查询联调待复跑
Sprint：Sprint 2
优先级：P0
Epic：P3-E2

## 用户故事

作为第三阶段小范围运行的研发执行者，我希望完成“实现线索补全结果和字段候选查询 API”，以便系统可以按 BMAD 已冻结方案推进线索完善、客户晋级、客户承接、清洗治理和 LangGraph 局部试点闭环。

## 上下文来源

- `docs/brainstorm/brainstorming-session-2026-06-04-第三阶段小范围运行-客户管理工作台.md`
- `docs/product/2026-06-04-海外车辆采购AI获客系统-第三阶段小范围运行方案与产品技术设计.md`
- `docs/architecture/2026-06-03-LLM-Agent服务编排选型分析.md`
- `prototypes/mvp-mobile-agent/design-brief.md`
- `docs/AI协同开发执行标准.md`
- `agents.md`

## Story 定义

**目标：** 移动端线索详情可查询补全批次、字段候选、证据、缺失字段和推荐动作。

**Files:**

- Modify: `apps/api/app/api/lead_enrichment.py`
- Modify: `apps/api/app/services/lead_enrichment.py`
- Test: `apps/api/tests/test_lead_enrichment_query_api.py`

**Codex 提示词：**

```text
请执行 P3-E2-S2：实现线索补全结果和字段候选查询 API。

要求：
1. 使用 superpowers:test-driven-development。
2. 严格依据第三阶段方案和本 Story 验收标准实现。
3. 保持 raw/staging/core/audit 分层，不让 AI 直接污染 core 数据。
4. 所有关键动作必须保留来源证据、操作人、时间和审计记录。
5. 不自动社交私信、不自动加好友、不自动发送触达消息。
6. 运行本 Story 对应测试，并按需执行相关联调验证。
7. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p3-e2-s2-执行结果.md。
8. 不要执行下一个 Story。
```

**验收标准：**

- `GET /staging-leads/{id}/enrichment-results` 返回补全批次和字段候选。
- 返回字段包含 source_type、source_url、evidence_note、confidence_score、review_status。
- Unknown/null/[] 不被编造成事实。

**非目标：**

- 不实现字段采纳动作。

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

- `_bmad-output/implementation-artifacts/codex-p3-e2-s2-执行结果.md`

实现完成项：

- 已更新 `apps/api/app/api/lead_enrichment.py`。
- 已更新 `apps/api/app/services/lead_enrichment.py`。
- 已更新 `apps/api/app/schemas/lead_enrichment.py`。
- 已创建 `apps/api/tests/test_lead_enrichment_query_api.py`。

验收结果：

- 单 Story 测试通过：`python -m pytest tests/test_lead_enrichment_query_api.py -q`，结果 `4 passed`。
- 相关回归通过：`python -m pytest tests/test_lead_enrichment_run_api.py tests/test_lead_enrichment_query_api.py tests/test_lead_enrichment_result_model.py tests/test_lead_enrichment_field_candidate_model.py -q`，结果 `24 passed`。
- 语法编译通过：`python -m compileall app/api app/services app/schemas`。
- OpenAPI 验证通过，确认存在 `GET /staging-leads/{lead_id}/enrichment-results`。
- 当前沙箱网络阻断 `.env` 中真实 PostgreSQL 连接，错误为 `PermissionError: [Errno 1] Operation not permitted`；本机无 `psql`、`pg_ctl`、`initdb`、`docker` 可替代验证，因此真实 PostgreSQL API 查询联调待外部环境复跑。

两轮评审结论：

- 第一轮评审：通过，补全批次、字段候选、证据字段、缺失值原样返回和只读查询边界均满足；真实库联调为环境限制项。
- 第二轮评审：通过，API/service/schema 与现有 FastAPI + SQLAlchemy 模式一致，未新增字段采纳、拒绝或自动触达动作；未发现新增实质阻塞问题。
