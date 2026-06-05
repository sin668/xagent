# Story P3-E3-S4：实现客户分配和状态流转基础服务

状态：实现完成，真实 PostgreSQL 写库联调待复跑
Sprint：Sprint 3
优先级：P1
Epic：P3-E3

## 用户故事

作为第三阶段小范围运行的研发执行者，我希望完成“实现客户分配和状态流转基础服务”，以便系统可以按 BMAD 已冻结方案推进线索完善、客户晋级、客户承接、清洗治理和 LangGraph 局部试点闭环。

## 上下文来源

- `docs/brainstorm/brainstorming-session-2026-06-04-第三阶段小范围运行-客户管理工作台.md`
- `docs/product/2026-06-04-海外车辆采购AI获客系统-第三阶段小范围运行方案与产品技术设计.md`
- `docs/architecture/2026-06-03-LLM-Agent服务编排选型分析.md`
- `prototypes/mvp-mobile-agent/design-brief.md`
- `docs/AI协同开发执行标准.md`
- `agents.md`

## Story 定义

**目标：** 客户晋级后可分配负责人，并按待分配、待首次触达、已触达待回复等状态推进。

**Files:**

- Modify: `apps/api/app/models/customer.py` 或新增 assignment 字段/表
- Create: `apps/api/app/services/customer_status.py`
- Test: `apps/api/tests/test_customer_assignment_status.py`

**Codex 提示词：**

```text
请执行 P3-E3-S4：实现客户分配和状态流转基础服务。

要求：
1. 使用 superpowers:test-driven-development。
2. 严格依据第三阶段方案和本 Story 验收标准实现。
3. 保持 raw/staging/core/audit 分层，不让 AI 直接污染 core 数据。
4. 所有关键动作必须保留来源证据、操作人、时间和审计记录。
5. 不自动社交私信、不自动加好友、不自动发送触达消息。
6. 运行本 Story 对应测试，并按需执行相关联调验证。
7. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p3-e3-s4-执行结果.md。
8. 不要执行下一个 Story。
```

**验收标准：**

- 支持 assign owner/team。
- 支持客户状态流转校验。
- Watch/Invalid 不进入客户工作台。
- C 级报价/合同前状态动作可触发合规要求。

**非目标：**

- 不实现完整 CRM 商机。

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

- `_bmad-output/implementation-artifacts/codex-p3-e3-s4-执行结果.md`

验收结果：

- 已新增 `customers.owner_team` 字段和 migration。
- 已新增 `CustomerAssignmentStatusService`，支持 owner/team 分配。
- 已支持客户状态流转校验。
- 已支持客户工作台过滤 Watch/Invalid/勿扰客户。
- 已支持 C 级客户进入报价状态前触发合规复核要求，并记录阻断审计。
- 已记录 `customer_assigned`、`customer_status_changed`、`customer_compliance_review_requested` 审计事件。
- 已运行当前 Story 测试、客户晋级/勿扰/模型契约关联回归测试和编译检查。
- 真实 PostgreSQL 连接验证因当前沙箱网络权限被阻断，错误为 `PermissionError: [Errno 1] Operation not permitted`，需在外部环境复跑。
