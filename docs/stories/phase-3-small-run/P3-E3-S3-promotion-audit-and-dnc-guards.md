# Story P3-E3-S3：客户晋级审计和勿扰硬门禁

状态：实现完成，真实 PostgreSQL 写库联调待复跑
Sprint：Sprint 3
优先级：P0
Epic：P3-E3

## 用户故事

作为第三阶段小范围运行的研发执行者，我希望完成“客户晋级审计和勿扰硬门禁”，以便系统可以按 BMAD 已冻结方案推进线索完善、客户晋级、客户承接、清洗治理和 LangGraph 局部试点闭环。

## 上下文来源

- `docs/brainstorm/brainstorming-session-2026-06-04-第三阶段小范围运行-客户管理工作台.md`
- `docs/product/2026-06-04-海外车辆采购AI获客系统-第三阶段小范围运行方案与产品技术设计.md`
- `docs/architecture/2026-06-03-LLM-Agent服务编排选型分析.md`
- `prototypes/mvp-mobile-agent/design-brief.md`
- `docs/AI协同开发执行标准.md`
- `agents.md`

## Story 定义

**目标：** 确保客户晋级、字段来源和勿扰校验完整审计。

**Files:**

- Modify: `apps/api/app/services/customer_promotion.py`
- Modify: `apps/api/app/models/audit_risk_log.py` 或相关审计服务
- Test: `apps/api/tests/test_customer_promotion_audit_dnc.py`

**Codex 提示词：**

```text
请执行 P3-E3-S3：客户晋级审计和勿扰硬门禁。

要求：
1. 使用 superpowers:test-driven-development。
2. 严格依据第三阶段方案和本 Story 验收标准实现。
3. 保持 raw/staging/core/audit 分层，不让 AI 直接污染 core 数据。
4. 所有关键动作必须保留来源证据、操作人、时间和审计记录。
5. 不自动社交私信、不自动加好友、不自动发送触达消息。
6. 运行本 Story 对应测试，并按需执行相关联调验证。
7. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p3-e3-s3-执行结果.md。
8. 不要执行下一个 Story。
```

**验收标准：**

- 晋级记录包含 reviewer、review_note、accepted_fields。
- 勿扰线索晋级被阻断。
- 审计事件 `lead_promoted_to_customer` 被记录。
- 禁止通过手动准入绕过硬门禁。

**非目标：**

- 不实现前端页面。

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

- `_bmad-output/implementation-artifacts/codex-p3-e3-s3-执行结果.md`

验收结果：

- 晋级审计事件已统一为 `lead_promoted_to_customer`。
- 晋级审计记录已包含 reviewer、review_note、accepted_fields_json。
- 勿扰客户名称匹配已支持 `customers.normalized_name` 和 `lower(customers.name)`。
- 勿扰联系方式匹配已支持 `lower(contact_methods.value)`，避免大小写绕过。
- 手动准入无法通过 accepted_fields 绕过勿扰硬门禁。
- 已运行当前 Story 测试、客户晋级回归测试、线索退出和深挖触发相关回归测试。
- 真实 PostgreSQL 连接验证因当前沙箱网络权限被阻断，错误为 `PermissionError: [Errno 1] Operation not permitted`，需在外部环境复跑。
