# Story P3-E5-S4：实现 Lead Cleanup LangGraph 图流程

状态：实现完成
Sprint：Sprint 5
优先级：P1
Epic：P3-E5

## 用户故事

作为第三阶段小范围运行的研发执行者，我希望完成“实现 Lead Cleanup LangGraph 图流程”，以便系统可以按 BMAD 已冻结方案推进线索完善、客户晋级、客户承接、清洗治理和 LangGraph 局部试点闭环。

## 上下文来源

- `docs/brainstorm/brainstorming-session-2026-06-04-第三阶段小范围运行-客户管理工作台.md`
- `docs/product/2026-06-04-海外车辆采购AI获客系统-第三阶段小范围运行方案与产品技术设计.md`
- `docs/architecture/2026-06-03-LLM-Agent服务编排选型分析.md`
- `prototypes/mvp-mobile-agent/design-brief.md`
- `docs/AI协同开发执行标准.md`
- `agents.md`

## Story 定义

**目标：** 用 LangGraph 表达 Watch/Invalid 清洗建议生成流程。

**Files:**

- Create: `apps/agents/app/graphs/lead_cleanup.py`
- Create: `apps/agents/app/tools/duplicate_detector.py`
- Test: `apps/agents/tests/test_lead_cleanup_graph.py`

**Codex 提示词：**

```text
请执行 P3-E5-S4：实现 Lead Cleanup LangGraph 图流程。

要求：
1. 使用 superpowers:test-driven-development。
2. 严格依据第三阶段方案和本 Story 验收标准实现。
3. 保持 raw/staging/core/audit 分层，不让 AI 直接污染 core 数据。
4. 所有关键动作必须保留来源证据、操作人、时间和审计记录。
5. 不自动社交私信、不自动加好友、不自动发送触达消息。
6. 运行本 Story 对应测试，并按需执行相关联调验证。
7. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p3-e5-s4-执行结果.md。
8. 不要执行下一个 Story。
```

**验收标准：**

- 图节点包含 load_watch_invalid、detect_duplicates、classify_invalid_reason、find_restore_candidates、write_cleanup_suggestions、wait_human_review。
- 输出 suggestion_type 和 evidence_json。
- 不自动删除、不自动执行、不自动恢复 Invalid。

**非目标：**

- 不实现 apps/api 执行建议。

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

- 新增 `apps/agents/app/graphs/lead_cleanup.py`，实现 Lead Cleanup 图流程。
- 新增 `apps/agents/app/tools/duplicate_detector.py`，实现基础强重复与疑似重复检测。
- 新增 `apps/agents/tests/test_lead_cleanup_graph.py`，覆盖节点顺序、重复建议、Invalid 分类、Watch 恢复候选和自动执行禁用。

### 验收结果

- 已包含节点：`load_watch_invalid`、`detect_duplicates`、`classify_invalid_reason`、`find_restore_candidates`、`write_cleanup_suggestions`、`wait_human_review`。
- 输出建议结构包含 `suggestion_type` 和 `evidence_json`。
- 清洗建议全部为 `review_status=pending`，等待人工复核。
- 审计中明确 `writes_core_tables=false`、`auto_execute_cleanup=false`、`auto_delete_leads=false`、`auto_restore_invalid=false`。
- 未实现 `apps/api` 执行建议，符合本 Story 非目标。

### 测试记录

- 红灯验证：`python -m pytest tests/test_lead_cleanup_graph.py -q`，失败原因为 `ModuleNotFoundError: No module named 'app.graphs.lead_cleanup'`，确认测试覆盖缺失实现。
- 绿灯验证：`python -m pytest tests/test_lead_cleanup_graph.py -q`，结果 `5 passed in 0.03s`。
- Agent 全量测试：`python -m pytest -q`，结果 `15 passed in 0.08s`。
- Agent 编译检查：`python -m compileall app`，退出码 0。
- API 轻量回归：`python -m pytest tests/test_lead_cleanup_audit_metrics.py tests/test_agent_scheduler.py tests/test_agent_thread_runner.py -q`，结果 `10 passed in 0.65s`。
- API 编译检查：`python -m compileall app/api app/services app/schemas app/models`，退出码 0。

### 两轮独立评审

第一轮评审：

- 结论：通过。
- 发现项：需确认 Agent 图不直接写 `customers`、`lead_sources`、`contact_methods`。
- 修正结果：`write_cleanup_suggestions` 通过 `ApiContractBoundary.validate_output_table("lead_cleanup_suggestions")` 校验输出表，并在审计中记录 `writes_core_tables=false`。

第二轮评审：

- 结论：通过。
- 发现项：需确认 Watch/Invalid 清洗不会自动执行、自动删除或自动恢复。
- 修正结果：`load_watch_invalid` 禁止 `auto_execute_cleanup`、`delete_leads`、`restore_invalid`，输出建议保持 `pending`，审计中记录三类自动动作均为 `false`。
