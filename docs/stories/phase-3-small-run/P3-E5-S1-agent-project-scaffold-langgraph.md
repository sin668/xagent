# Story P3-E5-S1：新建独立 Agent 项目并接入 LangGraph 基础结构

状态：实现完成
Sprint：Sprint 5
优先级：P0
Epic：P3-E5

## 用户故事

作为第三阶段小范围运行的研发执行者，我希望完成“新建独立 Agent 项目并接入 LangGraph 基础结构”，以便系统可以按 BMAD 已冻结方案推进线索完善、客户晋级、客户承接、清洗治理和 LangGraph 局部试点闭环。

## 上下文来源

- `docs/brainstorm/brainstorming-session-2026-06-04-第三阶段小范围运行-客户管理工作台.md`
- `docs/product/2026-06-04-海外车辆采购AI获客系统-第三阶段小范围运行方案与产品技术设计.md`
- `docs/architecture/2026-06-03-LLM-Agent服务编排选型分析.md`
- `prototypes/mvp-mobile-agent/design-brief.md`
- `docs/AI协同开发执行标准.md`
- `agents.md`

## Story 定义

**目标：** 创建 `apps/agents` 或 `apps/agent-runtime`，隔离 LangGraph 局部试点。

**Files:**

- Create: `apps/agents/pyproject.toml`
- Create: `apps/agents/app/graphs/__init__.py`
- Create: `apps/agents/app/schemas/__init__.py`
- Create: `apps/agents/app/tools/__init__.py`
- Create: `apps/agents/tests/`

**Codex 提示词：**

```text
请执行 P3-E5-S1：新建独立 Agent 项目并接入 LangGraph 基础结构。

要求：
1. 使用 superpowers:test-driven-development。
2. 严格依据第三阶段方案和本 Story 验收标准实现。
3. 保持 raw/staging/core/audit 分层，不让 AI 直接污染 core 数据。
4. 所有关键动作必须保留来源证据、操作人、时间和审计记录。
5. 不自动社交私信、不自动加好友、不自动发送触达消息。
6. 运行本 Story 对应测试，并按需执行相关联调验证。
7. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p3-e5-s1-执行结果.md。
8. 不要执行下一个 Story。
```

**验收标准：**

- 项目可安装并运行基础测试。
- 引入 LangGraph 依赖。
- 不影响 `apps/api` 现有启动。
- 文档说明 Agent 项目不直接写 core 表。

**非目标：**

- 不实现具体 graph。

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

- `_bmad-output/implementation-artifacts/codex-p3-e5-s1-执行结果.md`

验收结果：

- 已创建独立 Agent 项目目录 `apps/agents`。
- 已创建 `apps/agents/pyproject.toml`，声明 `langgraph`、`pydantic` 和 `pytest` 依赖。
- 已创建 `apps/agents/app/graphs/__init__.py`、`apps/agents/app/schemas/__init__.py`、`apps/agents/app/tools/__init__.py`。
- 已创建 `apps/agents/app/adapters/__init__.py`，用于后续与 `apps/api` 服务契约对接。
- 已创建 `apps/agents/tests/` 和基础测试 `tests/test_project_scaffold.py`。
- 已创建 `apps/agents/README.md`，明确 Agent 项目不直接写 core 表，不自动触达、不自动归并、不自动恢复 Invalid。
- 已提供 `build_placeholder_graph` 占位契约，明确当前不实现具体 graph。
- 已验证 `apps/agents` 基础测试可运行。
- 已验证当前环境可导入 `langgraph`。
- 已使用可写 `PYTHONUSERBASE=/private/tmp/xagent-agents-userbase` 完成本地 editable 安装验证。
- 已运行 `apps/api` 轻量回归和编译检查，确认不影响现有 API 启动相关导入。
