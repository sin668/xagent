# Story P3-E6-S4：实现客户跟进记录 CRUD API

状态：实现完成，真实 PostgreSQL API 联调待外部环境复跑
Sprint：Sprint 6
优先级：P1
Epic：P3-E6

## 用户故事

作为第三阶段小范围运行的研发执行者，我希望完成“实现客户跟进记录 CRUD API”，以便系统可以按 BMAD 已冻结方案推进线索完善、客户晋级、客户承接、清洗治理和 LangGraph 局部试点闭环。

## 上下文来源

- `docs/brainstorm/brainstorming-session-2026-06-04-第三阶段小范围运行-客户管理工作台.md`
- `docs/product/2026-06-04-海外车辆采购AI获客系统-第三阶段小范围运行方案与产品技术设计.md`
- `docs/architecture/2026-06-03-LLM-Agent服务编排选型分析.md`
- `prototypes/mvp-mobile-agent/design-brief.md`
- `docs/AI协同开发执行标准.md`
- `agents.md`

## Story 定义

**目标：** 客服/销售可记录人工触达、客户反馈、下一步动作和下一次跟进时间。

**Files:**

- Create/Modify: `apps/api/app/api/customer_followups.py`
- Create: `apps/api/app/services/customer_followups.py`
- Test: `apps/api/tests/test_customer_followups_api.py`

**Codex 提示词：**

```text
请执行 P3-E6-S4：实现客户跟进记录 CRUD API。

要求：
1. 使用 superpowers:test-driven-development。
2. 严格依据第三阶段方案和本 Story 验收标准实现。
3. 保持 raw/staging/core/audit 分层，不让 AI 直接污染 core 数据。
4. 所有关键动作必须保留来源证据、操作人、时间和审计记录。
5. 不自动社交私信、不自动加好友、不自动发送触达消息。
6. 运行本 Story 对应测试，并按需执行相关联调验证。
7. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p3-e6-s4-执行结果.md。
8. 不要执行下一个 Story。
```

**验收标准：**

- 支持新增/查询跟进记录。
- 记录 owner/team/followup_type/content/customer_feedback/next_action/next_followup_at。
- 标记勿扰时立即生效并阻断后续主动触达。
- 不得自动发送任何消息。

**非目标：**

- 不替代 outreach_records。

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

- 新增 `apps/api/app/services/customer_followups.py`，实现客户跟进记录查询和新增服务。
- 新增 `apps/api/app/api/customer_followups.py`，提供客户跟进记录 API。
- 更新 `apps/api/app/main.py`，挂载客户跟进记录路由。
- 新增 `apps/api/tests/test_customer_followups_api.py`，覆盖路由、查询、新增、字段保留、勿扰即时生效和不自动发送消息。

### 验收结果

- 支持查询：`GET /customers/{customer_id}/followups`。
- 支持新增：`POST /customers/{customer_id}/followups`。
- 已记录 `owner_id`、`team`、`followup_type`、`content`、`customer_feedback`、`next_action`、`next_followup_at`。
- `triggered_dnc=true` 时立即将客户标记为勿扰并阻断后续主动跟进。
- 未自动发送任何消息。
- 未替代 `outreach_records`，符合非目标。

### 测试记录

- 红灯验证：`python -m pytest tests/test_customer_followups_api.py -q`，失败原因为 `ModuleNotFoundError: No module named 'app.services.customer_followups'`。
- 绿灯验证：`python -m pytest tests/test_customer_followups_api.py -q`，结果 `5 passed in 5.37s`。
- 离线关联回归：`python -m pytest tests/test_customer_followups_api.py tests/test_customer_vehicle_intents_api.py tests/test_customer_intents_followups_models.py tests/test_customer_detail_aggregate_api.py tests/test_customers_workbench_list_api.py tests/test_customer_assignment_status.py -q`，结果 `36 passed in 2.17s`。
- 编译检查：`python -m compileall app/api app/services app/schemas app/models`，退出码 0。
- 真实 PostgreSQL API 联调：当前沙箱网络对真实 PostgreSQL 连接受限，需在外部环境复跑。

### 两轮独立评审

第一轮评审：

- 结论：通过。
- 发现项：跟进记录必须保留人工动作字段，不得与自动触达混淆。
- 修正结果：新增记录只写 `customer_followups`，保留 owner/team/type/content/feedback/next_action/next_followup_at，不写发送时间或触达发送字段。

第二轮评审：

- 结论：通过，真实 PostgreSQL API 联调待外部环境复跑。
- 发现项：标记勿扰必须立即生效并阻断后续主动跟进。
- 修正结果：`triggered_dnc=true` 时同步更新 `customers.do_not_contact=true`、`status=do_not_contact`、原因和操作人；后续新增跟进会被拒绝。
