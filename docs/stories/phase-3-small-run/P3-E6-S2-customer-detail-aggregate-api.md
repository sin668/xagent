# Story P3-E6-S2：实现客户详情聚合 API

状态：实现完成，真实 PostgreSQL API 联调待外部环境复跑
Sprint：Sprint 6
优先级：P0
Epic：P3-E6

## 用户故事

作为第三阶段小范围运行的研发执行者，我希望完成“实现客户详情聚合 API”，以便系统可以按 BMAD 已冻结方案推进线索完善、客户晋级、客户承接、清洗治理和 LangGraph 局部试点闭环。

## 上下文来源

- `docs/brainstorm/brainstorming-session-2026-06-04-第三阶段小范围运行-客户管理工作台.md`
- `docs/product/2026-06-04-海外车辆采购AI获客系统-第三阶段小范围运行方案与产品技术设计.md`
- `docs/architecture/2026-06-03-LLM-Agent服务编排选型分析.md`
- `prototypes/mvp-mobile-agent/design-brief.md`
- `docs/AI协同开发执行标准.md`
- `agents.md`

## Story 定义

**目标：** 客户详情聚合客户主档、联系方式、来源证据、意向车型、触达历史、跟进记录和合规状态。

**Files:**

- Modify: `apps/api/app/api/customers.py`
- Modify: `apps/api/app/services/customers.py`
- Test: `apps/api/tests/test_customer_detail_aggregate_api.py`

**Codex 提示词：**

```text
请执行 P3-E6-S2：实现客户详情聚合 API。

要求：
1. 使用 superpowers:test-driven-development。
2. 严格依据第三阶段方案和本 Story 验收标准实现。
3. 保持 raw/staging/core/audit 分层，不让 AI 直接污染 core 数据。
4. 所有关键动作必须保留来源证据、操作人、时间和审计记录。
5. 不自动社交私信、不自动加好友、不自动发送触达消息。
6. 运行本 Story 对应测试，并按需执行相关联调验证。
7. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p3-e6-s2-执行结果.md。
8. 不要执行下一个 Story。
```

**验收标准：**

- `GET /customers/{id}` 返回完整聚合信息。
- 显示待补全/待确认字段。
- 勿扰状态和 C 级合规状态明确返回。
- 来源证据可追溯到 lead_sources/enrichment。

**非目标：**

- 不生成触达草稿。

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

执行时间：2026-06-04
执行者：Codex
执行方式：`superpowers:executing-plans` + `superpowers:test-driven-development`

### 实现内容

- 更新 `apps/api/app/schemas/customer.py`，新增 `CustomerDetailResponse`。
- 更新 `apps/api/app/services/customers.py`，新增 `get_customer_detail` 和客户详情聚合序列化方法。
- 更新 `apps/api/app/api/customers.py`，将 `GET /customers/{id}` 响应模型切换为客户详情聚合响应。
- 新增 `apps/api/tests/test_customer_detail_aggregate_api.py`，覆盖详情聚合、待补全字段、勿扰状态、C级合规状态和来源追溯。

### 验收结果

- `GET /customers/{id}` 已返回完整聚合信息。
- 已显示待补全字段：从 `customers.missing_fields` 拆分为 `pending_fields`。
- 勿扰状态明确返回：`do_not_contact.enabled/reason/marked_by/marked_at`。
- C 级合规状态明确返回：`compliance_status.requires_review/latest_status/latest_reason/latest_risk_note`。
- 来源证据可追溯到 `lead_sources` 和联系方式证据：`source_traceability`、`sources`、`contacts.evidence_note`。
- 未生成触达草稿，符合非目标。

### 测试记录

- 红灯验证：`python -m pytest tests/test_customer_detail_aggregate_api.py -q`，失败原因为 `ImportError: cannot import name 'CustomerDetailResponse'`。
- 绿灯验证：`python -m pytest tests/test_customer_detail_aggregate_api.py -q`，结果 `4 passed in 2.52s`。
- 离线关联回归：`python -m pytest tests/test_customer_detail_aggregate_api.py tests/test_customers_workbench_list_api.py tests/test_customer_assignment_status.py tests/test_promote_staging_lead_to_customer_phase3.py -q`，结果 `25 passed in 2.69s`。
- 编译检查：`python -m compileall app/api app/services app/schemas app/models`，退出码 0。
- 真实 PostgreSQL API 联调：当前沙箱网络对真实 PostgreSQL 连接受限，需在外部环境复跑。

### 两轮独立评审

第一轮评审：

- 结论：通过。
- 发现项：详情接口必须覆盖客户详情页所需的七类信息，不能只返回列表摘要。
- 修正结果：`CustomerDetailResponse` 聚合客户画像、联系方式、来源证据、意向车型、触达历史、跟进记录、合规状态。

第二轮评审：

- 结论：通过，真实 PostgreSQL API 联调待外部环境复跑。
- 发现项：勿扰客户和 C 级客户必须在详情中给出硬边界提示。
- 修正结果：勿扰客户 `next_action` 返回“勿扰客户，不得触达”；C 级客户通过 `compliance_status.requires_review=true` 和最新合规状态明确提示。
