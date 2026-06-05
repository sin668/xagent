# Story P3-E6-S1：实现客户工作台列表 API

状态：实现完成，真实 PostgreSQL API 联调待外部环境复跑
Sprint：Sprint 6
优先级：P0
Epic：P3-E6

## 用户故事

作为第三阶段小范围运行的研发执行者，我希望完成“实现客户工作台列表 API”，以便系统可以按 BMAD 已冻结方案推进线索完善、客户晋级、客户承接、清洗治理和 LangGraph 局部试点闭环。

## 上下文来源

- `docs/brainstorm/brainstorming-session-2026-06-04-第三阶段小范围运行-客户管理工作台.md`
- `docs/product/2026-06-04-海外车辆采购AI获客系统-第三阶段小范围运行方案与产品技术设计.md`
- `docs/architecture/2026-06-03-LLM-Agent服务编排选型分析.md`
- `prototypes/mvp-mobile-agent/design-brief.md`
- `docs/AI协同开发执行标准.md`
- `agents.md`

## Story 定义

**目标：** 客户工作台按下一步动作优先级展示已晋级客户。

**Files:**

- Create/Modify: `apps/api/app/api/customers.py`
- Create/Modify: `apps/api/app/services/customers.py`
- Test: `apps/api/tests/test_customers_workbench_list_api.py`

**Codex 提示词：**

```text
请执行 P3-E6-S1：实现客户工作台列表 API。

要求：
1. 使用 superpowers:test-driven-development。
2. 严格依据第三阶段方案和本 Story 验收标准实现。
3. 保持 raw/staging/core/audit 分层，不让 AI 直接污染 core 数据。
4. 所有关键动作必须保留来源证据、操作人、时间和审计记录。
5. 不自动社交私信、不自动加好友、不自动发送触达消息。
6. 运行本 Story 对应测试，并按需执行相关联调验证。
7. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p3-e6-s1-执行结果.md。
8. 不要执行下一个 Story。
```

**验收标准：**

- `GET /customers` 支持状态、等级、负责人、国家、城市筛选。
- 默认按今日待跟进、C级待合规、已回复待销售、待首次触达、待补全排序。
- Watch/Invalid 不出现。
- 返回联系方式摘要、来源完整度、意向车型摘要、下一步动作。

**非目标：**

- 不实现移动端页面。

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

- 新增 `apps/api/app/services/customers.py`，实现客户工作台列表查询、筛选、默认优先级排序和摘要聚合。
- 更新 `apps/api/app/api/customers.py`，让 `GET /customers` 支持 `status`、`grade`、`owner`、`country`、`city`、`limit` 筛选，并返回工作台增强字段。
- 更新 `apps/api/app/schemas/customer.py`，为 `CustomerSummary` 增加联系方式摘要、来源完整度、完善度评分、跟进状态、意向车型摘要和下一步动作字段。
- 新增 `apps/api/tests/test_customers_workbench_list_api.py`，覆盖筛选、Watch/Invalid/勿扰排除、默认下一步动作排序和摘要字段。

### 验收结果

- `GET /customers` 已支持状态、等级、负责人、国家、城市筛选。
- 默认排序已按下一步动作优先级：今日待跟进、C级待合规、已回复待销售、待首次触达、待补全客户信息、销售跟进中、暂停/低优先级。
- Watch/Invalid/勿扰客户不进入客户工作台列表。
- 返回字段已包含联系方式摘要、来源完整度、完善度评分、跟进状态、意向车型摘要和下一步动作。
- 未实现移动端页面，符合本 Story 非目标。

### 测试记录

- 红灯验证：`python -m pytest tests/test_customers_workbench_list_api.py -q`，失败原因为 `ModuleNotFoundError: No module named 'app.services.customers'`，确认缺少客户工作台 service。
- 绿灯验证：`python -m pytest tests/test_customers_workbench_list_api.py -q`，结果 `5 passed in 1.65s`。
- 离线关联回归：`python -m pytest tests/test_customers_workbench_list_api.py tests/test_customer_assignment_status.py tests/test_promote_staging_lead_to_customer_phase3.py -q`，结果 `21 passed in 1.55s`。
- 编译检查：`python -m compileall app/api app/services app/schemas app/models`，退出码 0。
- 真实 PostgreSQL API 回归：执行客户 DNC / outreach 相关 API 测试时，当前沙箱连接 `8.129.17.71:5432` 报 `PermissionError: [Errno 1] Operation not permitted`，需在允许数据库网络访问的外部环境复跑。

### 两轮独立评审

第一轮评审：

- 结论：通过。
- 发现项：需确认工作台列表不会展示 Watch/Invalid/勿扰客户。
- 修正结果：查询层过滤 `do_not_contact=false`、排除 `Watch/Invalid/DO_NOT_CONTACT` 状态，并在 service 层复用 `CustomerAssignmentStatusService.filter_workbench_customers` 做二次过滤。

第二轮评审：

- 结论：通过，真实 PostgreSQL API 联调待外部环境复跑。
- 发现项：需确认排序服务日常动作优先级，而不是静态更新时间。
- 修正结果：新增 `next_action` 和 `next_action_priority`，列表按今日待跟进、C级待合规、已回复待销售、待首次触达、待补全客户信息等优先级排序。
