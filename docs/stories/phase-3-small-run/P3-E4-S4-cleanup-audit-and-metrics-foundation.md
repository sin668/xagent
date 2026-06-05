# Story P3-E4-S4：清洗审计和基础指标口径

状态：实现完成，真实 PostgreSQL 指标查询待复跑
Sprint：Sprint 4
优先级：P1
Epic：P3-E4

## 用户故事

作为第三阶段小范围运行的研发执行者，我希望完成“清洗审计和基础指标口径”，以便系统可以按 BMAD 已冻结方案推进线索完善、客户晋级、客户承接、清洗治理和 LangGraph 局部试点闭环。

## 上下文来源

- `docs/brainstorm/brainstorming-session-2026-06-04-第三阶段小范围运行-客户管理工作台.md`
- `docs/product/2026-06-04-海外车辆采购AI获客系统-第三阶段小范围运行方案与产品技术设计.md`
- `docs/architecture/2026-06-03-LLM-Agent服务编排选型分析.md`
- `prototypes/mvp-mobile-agent/design-brief.md`
- `docs/AI协同开发执行标准.md`
- `agents.md`

## Story 定义

**目标：** 记录清洗建议生成、确认、执行事件，并提供重复率、恢复率、确认无效率等基础口径。

**Files:**

- Modify: `apps/api/app/services/lead_cleanup.py`
- Create/Modify: `apps/api/app/services/phase3_metrics.py`
- Test: `apps/api/tests/test_lead_cleanup_audit_metrics.py`

**Codex 提示词：**

```text
请执行 P3-E4-S4：清洗审计和基础指标口径。

要求：
1. 使用 superpowers:test-driven-development。
2. 严格依据第三阶段方案和本 Story 验收标准实现。
3. 保持 raw/staging/core/audit 分层，不让 AI 直接污染 core 数据。
4. 所有关键动作必须保留来源证据、操作人、时间和审计记录。
5. 不自动社交私信、不自动加好友、不自动发送触达消息。
6. 运行本 Story 对应测试，并按需执行相关联调验证。
7. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p3-e4-s4-执行结果.md。
8. 不要执行下一个 Story。
```

**验收标准：**

- 记录 lead_cleanup_suggestion_created/approved/executed。
- 可统计清洗建议采纳率、重复归并率、Watch 恢复率、Invalid 确认率。
- 指标不把自动建议等同于已执行清洗。

**非目标：**

- 不做管理后台页面。

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

- `_bmad-output/implementation-artifacts/codex-p3-e4-s4-执行结果.md`

验收结果：

- 已新增 `LeadCleanupSuggestionService.audit_suggestion_created`，记录 `lead_cleanup_suggestion_created`。
- 既有 approve/reject 继续记录 `lead_cleanup_suggestion_approved` / `lead_cleanup_suggestion_rejected`。
- 既有 execute 继续记录 `lead_cleanup_suggestion_executed`。
- 已新增 `apps/api/app/services/phase3_metrics.py`，提供 `Phase3CleanupMetricsService.cleanup_metrics`。
- 已支持统计清洗建议生成数、确认数、执行数、拒绝数、待处理数。
- 已支持统计清洗建议采纳率、执行率、重复归并率、Watch 恢复率、Invalid 确认率。
- 指标口径明确以 `executed` 才计入重复归并、Watch 恢复和 Invalid 确认，不把自动建议或仅 approved 建议等同于已执行清洗。
- 未新增管理后台页面。
- 未新增自动社交私信、自动加好友、自动触达客户能力。
- 已运行当前 Story 测试、清洗建议查询/审核/执行/模型/第三阶段契约关联测试和编译检查。
- 真实 PostgreSQL 连接验证因当前沙箱网络权限被阻断，错误为 `PermissionError: [Errno 1] Operation not permitted`，需在外部环境复跑。
