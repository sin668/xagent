# Story P3-E4-S1：实现清洗建议列表、详情和筛选 API

状态：实现完成，真实 PostgreSQL API 查询联调待复跑
Sprint：Sprint 4
优先级：P0
Epic：P3-E4

## 用户故事

作为第三阶段小范围运行的研发执行者，我希望完成“实现清洗建议列表、详情和筛选 API”，以便系统可以按 BMAD 已冻结方案推进线索完善、客户晋级、客户承接、清洗治理和 LangGraph 局部试点闭环。

## 上下文来源

- `docs/brainstorm/brainstorming-session-2026-06-04-第三阶段小范围运行-客户管理工作台.md`
- `docs/product/2026-06-04-海外车辆采购AI获客系统-第三阶段小范围运行方案与产品技术设计.md`
- `docs/architecture/2026-06-03-LLM-Agent服务编排选型分析.md`
- `prototypes/mvp-mobile-agent/design-brief.md`
- `docs/AI协同开发执行标准.md`
- `agents.md`

## Story 定义

**目标：** 运营可以查看 Watch/Invalid/重复线索的清洗建议队列。

**Files:**

- Create: `apps/api/app/api/lead_cleanup.py`
- Create: `apps/api/app/services/lead_cleanup.py`
- Test: `apps/api/tests/test_lead_cleanup_query_api.py`

**Codex 提示词：**

```text
请执行 P3-E4-S1：实现清洗建议列表、详情和筛选 API。

要求：
1. 使用 superpowers:test-driven-development。
2. 严格依据第三阶段方案和本 Story 验收标准实现。
3. 保持 raw/staging/core/audit 分层，不让 AI 直接污染 core 数据。
4. 所有关键动作必须保留来源证据、操作人、时间和审计记录。
5. 不自动社交私信、不自动加好友、不自动发送触达消息。
6. 运行本 Story 对应测试，并按需执行相关联调验证。
7. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p3-e4-s1-执行结果.md。
8. 不要执行下一个 Story。
```

**验收标准：**

- `GET /lead-cleanup/suggestions` 支持 suggestion_type、review_status、confidence、lead 等筛选。
- 详情返回 reason、evidence_json、recommended_action、target_lead_id。
- 默认只展示 pending 建议。

**非目标：**

- 不执行归并。

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

- `_bmad-output/implementation-artifacts/codex-p3-e4-s1-执行结果.md`

验收结果：

- 已新增 `GET /lead-cleanup/suggestions`。
- 已新增 `GET /lead-cleanup/suggestions/{suggestion_id}`。
- 列表接口支持 `suggestion_type`、`review_status`、`confidence`、`max_confidence`、`lead`、`limit` 筛选。
- 默认只展示 pending 建议。
- 详情返回 `reason`、`evidence_json`、`recommended_action`、`target_lead_id`。
- 未实现 approve/reject/execute 路由，符合本 Story 非目标“不执行归并”。
- 已运行当前 Story 测试、清洗模型测试、第三阶段模型契约测试和编译检查。
- 真实 PostgreSQL 连接验证因当前沙箱网络权限被阻断，错误为 `PermissionError: [Errno 1] Operation not permitted`，需在外部环境复跑。
