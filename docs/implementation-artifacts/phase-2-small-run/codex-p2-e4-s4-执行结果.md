# P2-E4-S4 移动端 Agent 手动调用页面和任务状态展示执行结果

## 基本信息

- Story：`docs/stories/phase-2-small-run/P2-E4-S4-mobile-agent-run-page.md`
- 状态：已完成
- 执行日期：2026-06-02
- 执行原则：每次只执行一个 Story；不做锁操作；不做 git 操作；使用 TDD；完成前执行验证；完成后执行两轮独立多维度评审。

## 交付内容

- 新增：`apps/mobile/src/pages/agent-run/index.vue`
- 新增：`apps/mobile/tests/agentRunPage.test.mjs`
- 修改：`apps/mobile/src/services/agentTasks.js`
- 修改：`apps/mobile/src/pages.json`
- 修改：`apps/mobile/pages.json`
- 修改：`apps/mobile/src/styles/sourceCandidates.css`

## 功能说明

移动端新增“启动 Agent”页面，对齐原型 `prototypes/mvp-mobile-agent/pages/agent-run.html`：

- 支持选择 `SOURCE_DISCOVERY` 和 `LEAD_EXTRACTION`。
- 支持填写国家、城市、渠道策略、Prompt Template、运行上限。
- 支持手动创建并启动任务。
- 启动后展示 `agentTaskRunId`、状态、输出数量、阻断数量、重复数量、失败原因、模型与 Prompt 审计信息。
- 支持刷新最近一次任务状态。
- 页面展示安全边界：不触达、自动私信禁用、登录采集禁用、High 抽取需人工审核、Forbidden 阻断。

## Service 契约

- `SOURCE_DISCOVERY`：调用 `agentTasksService.startSourceDiscovery()`，后端契约为 `POST /agent-tasks/source-discovery/run`。
- `LEAD_EXTRACTION`：调用 `agentTasksService.startLeadExtraction()`，后端契约为 `POST /agent-tasks/lead-extraction/run`。
- 状态查询：调用 `agentTasksService.getAgentTaskRun()`，后端契约为 `GET /agent-task-runs/{id}`。

## TDD 记录

### RED

先创建 `apps/mobile/tests/agentRunPage.test.mjs`，运行：

```bash
node --test apps/mobile/tests/agentRunPage.test.mjs
```

结果：`0/5 passed`。

失败原因符合预期：

- `apps/mobile/src/pages/agent-run/index.vue` 不存在。
- 两份页面配置尚未注册 Agent 手动调用页面。
- `agentTasksService.startLeadExtraction()` 尚不存在。

### GREEN

补齐页面、页面配置、service 契约和样式后，再次运行：

```bash
node --test apps/mobile/tests/agentRunPage.test.mjs
```

结果：`5/5 passed`。

## 验证结果

### 目标测试

```bash
node --test apps/mobile/tests/agentRunPage.test.mjs
```

结果：`5/5 passed`。

### 移动端完整测试

```bash
npm --prefix apps/mobile test
```

结果：`69/69 passed`。

### H5 构建

```bash
npm --prefix apps/mobile run build:h5
```

结果：通过，输出 `DONE Build complete.`。

## 验收对照

- 可以从移动端手动启动任务：通过，页面支持启动 `SOURCE_DISCOVERY` 和 `LEAD_EXTRACTION`。
- 任务状态可见：通过，页面展示 `agentTaskRunId`、状态、输出数量、失败原因和模型审计信息。
- 不提供自动触达动作：通过，页面无自动私信、自动加好友、批量触达能力。
- 风控边界可见：通过，页面展示不触达、登录采集禁用、High 人工审核、Forbidden 阻断。

## 第一轮独立多维度评审

- 结论：通过，无实质阻塞问题。
- 功能完整性：页面覆盖任务参数、启动动作、状态展示和安全边界。
- API 对接：任务启动和状态查询均通过 `agentTasksService`。
- 合规安全：页面只启动 Agent 作业，不提供任何客户触达动作。
- 测试覆盖：新增测试覆盖页面注册、任务类型、表单字段、service 调用、安全边界和 `LEAD_EXTRACTION` 启动契约。
- 发现项：移动端 Agent service 缺少 `LEAD_EXTRACTION` 启动契约。
- 修正结果：已新增 `startLeadExtraction()`，对接 `/agent-tasks/lead-extraction/run`。

## 第二轮独立多维度评审

- 结论：通过，连续两轮未发现新增实质阻塞问题。
- 回归风险：移动端完整测试 `69/69 passed`。
- 编译风险：H5 构建通过。
- 合规边界：页面不包含自动社交私信、自动加好友、登录后批量采集、反爬规避或自动触达动作。
- 范围控制：未执行下一 Story；未实现调度、Redis lock、重试或端到端验收。
- 修正结果：无需新增修正。

## 后续建议

下一 Story 可进入 `P2-E4-S5-mobile-h5-integration-verification.md`，完成移动端前后端联调和 H5 可用性验证。但本次执行未进入下一 Story。
