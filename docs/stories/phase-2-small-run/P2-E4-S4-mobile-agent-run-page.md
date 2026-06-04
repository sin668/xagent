# Story P2-E4-S4：移动端 Agent 手动调用页面和任务状态展示

状态：Done  
Sprint：Sprint 3  
优先级：P1  
Epic：P2-E4

## 用户故事

作为第二阶段小范围运行的研发执行者，我希望完成“移动端 Agent 手动调用页面和任务状态展示”，以便系统可以按 BMAD 已冻结方案推进真实 LLM、来源发现、审核、抽取、审计和联调闭环。

## 上下文来源

- `docs/product/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行方案与产品技术设计.md`
- `_bmad-output/brainstorming/brainstorming-session-2026-06-02-第二阶段小范围运行-LLM来源发现Agent.md`
- `docs/superpowers/plans/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行Codex推进计划.md`
- `docs/AI协同开发执行标准.md`
- `AGENTS.md`

## Story 定义

**目标：** 实现移动端手动启动 Agent 页面，对齐原型 `agent-run.html`。

**Files:**

- Create: `apps/mobile/src/pages/agent-run/index.vue`
- Test: `apps/mobile/tests/agentRunPage.test.mjs`

**Codex 提示词：**

```text
请执行 P2-E4-S4：移动端 Agent 手动调用页面和任务状态展示。

要求：
1. 使用 superpowers:test-driven-development。
2. 页面参考 prototypes/mvp-mobile-agent/pages/agent-run.html。
3. 支持选择 SOURCE_DISCOVERY 和 LEAD_EXTRACTION。
4. 支持填写国家、城市、渠道策略、prompt template、运行上限。
5. 启动后展示 agent_task_run_id、状态、输出数量、失败原因。
6. 不提供自动触达动作。
7. 运行移动端页面/service 测试。
8. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p2-e4-s4-执行结果.md。
不要执行下一个 Story。
```

**验收标准：**

- 可以从移动端手动启动任务。
- 任务状态可见。

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作。
- 不做 git 操作。
- 代码实现 Story 必须使用 `superpowers:test-driven-development`。
- 调试异常必须使用 `superpowers:systematic-debugging`。
- 完成前必须使用 `superpowers:verification-before-completion`。
- 完成后必须执行两轮独立多维度评审，并记录结论、发现项和修正结果。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- 不自动社交私信。
- 不自动加好友。
- 不登录后批量采集。
- 不反爬规避。
- 不抓取非公开数据。
- High 来源未审核不得进入自动抽取。
- Forbidden 来源不得进入自动抽取。
- Invalid 和 Watch 不进入触达队列。
- 勿扰客户不得再次进入触达队列。
- C 级线索报价、合同或实质交易前必须合规复核。
- 所有 AI 输出必须保存来源证据、prompt 版本、模型和审计记录。

## 实施结果

已完成。

### 本次变更

- 新增移动端 Agent 手动调用页面：`apps/mobile/src/pages/agent-run/index.vue`。
- 更新页面注册：
  - `apps/mobile/src/pages.json` 增加 `pages/agent-run/index`。
  - `apps/mobile/pages.json` 增加 `src/pages/agent-run/index`。
- 扩展移动端 Agent service：`apps/mobile/src/services/agentTasks.js` 新增 `startLeadExtraction()`，并为 `startSourceDiscovery()` 支持 `promptTemplateKey`。
- 复用并扩展移动端样式：`apps/mobile/src/styles/sourceCandidates.css`。
- 新增页面/service 契约测试：`apps/mobile/tests/agentRunPage.test.mjs`。

### 验收结果

- 页面参考原型 `prototypes/mvp-mobile-agent/pages/agent-run.html`。
- 支持选择 `SOURCE_DISCOVERY` 和 `LEAD_EXTRACTION`。
- 支持填写国家、城市、渠道策略、prompt template、运行上限。
- 启动后展示 `agentTaskRunId`、任务状态、输出数量、阻断数量、重复数量、失败原因、模型与 Prompt 审计信息。
- `SOURCE_DISCOVERY` 调用 `agentTasksService.startSourceDiscovery()`。
- `LEAD_EXTRACTION` 调用 `agentTasksService.startLeadExtraction()`，移动端契约为 `POST /agent-tasks/lead-extraction/run`。
- 支持调用 `agentTasksService.getAgentTaskRun()` 刷新任务状态。
- 页面展示安全边界：不触达、自动私信禁用、登录采集禁用、High 抽取需人工审核、Forbidden 阻断。
- 未提供自动触达动作。

### TDD 记录

- RED：先创建 `apps/mobile/tests/agentRunPage.test.mjs`，运行 `node --test apps/mobile/tests/agentRunPage.test.mjs`，结果 `0/5 passed`，失败原因符合预期：页面未注册、页面文件缺失、`startLeadExtraction()` 不存在。
- GREEN：补齐页面、页面注册、service 契约和样式后，运行 `node --test apps/mobile/tests/agentRunPage.test.mjs`，结果 `5/5 passed`。

### 验证命令

- `node --test apps/mobile/tests/agentRunPage.test.mjs`：`5/5 passed`。
- `npm --prefix apps/mobile test`：`69/69 passed`。
- `npm --prefix apps/mobile run build:h5`：通过，输出 `DONE Build complete.`。

### 第一轮独立多维度评审

- 结论：通过，无实质阻塞问题。
- 功能完整性：页面覆盖任务类型选择、参数填写、启动任务、状态展示和安全边界。
- API 对接：`SOURCE_DISCOVERY` 与 `LEAD_EXTRACTION` 均通过 `agentTasksService` 触发真实后端契约。
- 风控合规：页面明确“不触达”，未提供自动私信、自动加好友、批量触达能力。
- 测试覆盖：测试覆盖页面注册、表单字段、任务启动、状态查询、安全边界和 `LEAD_EXTRACTION` service 契约。
- 发现项：现有移动端 service 只有 `SOURCE_DISCOVERY`，缺少 `LEAD_EXTRACTION` 启动契约。
- 修正结果：已新增 `startLeadExtraction()`，对接 `/agent-tasks/lead-extraction/run`。

### 第二轮独立多维度评审

- 结论：通过，连续两轮未发现新增实质阻塞问题。
- 回归风险：移动端完整测试 `69/69 passed`，新增 service 参数未破坏既有 `SOURCE_DISCOVERY` 测试。
- 编译风险：H5 构建通过，新增页面可被 uni-app 编译。
- 合规边界：页面仅启动 Agent 任务并展示状态，不包含触达、登录采集、反爬规避动作。
- 范围控制：未执行下一 Story；未实现调度、Redis lock 或 E2E 验收内容。
- 修正结果：无需新增修正。

### 归档

- `_bmad-output/implementation-artifacts/codex-p2-e4-s4-执行结果.md`
