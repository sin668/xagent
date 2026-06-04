# Story P2-E4-S1：移动端来源候选 service 和 API adapter

状态：Done  
Sprint：Sprint 3  
优先级：P1  
Epic：P2-E4

## 用户故事

作为第二阶段小范围运行的研发执行者，我希望完成“移动端来源候选 service 和 API adapter”，以便系统可以按 BMAD 已冻结方案推进真实 LLM、来源发现、审核、抽取、审计和联调闭环。

## 上下文来源

- `docs/product/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行方案与产品技术设计.md`
- `_bmad-output/brainstorming/brainstorming-session-2026-06-02-第二阶段小范围运行-LLM来源发现Agent.md`
- `docs/superpowers/plans/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行Codex推进计划.md`
- `docs/AI协同开发执行标准.md`
- `AGENTS.md`

## Story 定义

**目标：** 在移动端封装来源候选和 Agent 调用 API。

**Files:**

- Create: `apps/mobile/src/services/sourceCandidates.js`
- Create: `apps/mobile/src/services/agentTasks.js`
- Test: `apps/mobile/tests/sourceCandidates.test.mjs`
- Test: `apps/mobile/tests/agentTasks.test.mjs`

**Codex 提示词：**

```text
请执行 P2-E4-S1：移动端来源候选 service 和 API adapter。

要求：
1. 使用 superpowers:test-driven-development。
2. 对接真实 API，不使用 seed 作为最终数据源。
3. sourceCandidates.js 支持列表、详情、审核动作。
4. agentTasks.js 支持启动 SOURCE_DISCOVERY 和查询任务状态。
5. 使用现有 apps/mobile/src/services/apiClient.js 风格。
6. 运行 npm --prefix apps/mobile test 或项目已有移动端测试命令。
7. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p2-e4-s1-执行结果.md。
不要执行下一个 Story。
```

**验收标准：**

- 移动端 service 测试通过。
- API adapter 字段与后端 schema 对齐。

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

执行日期：2026-06-02

已完成：

- 新增 `apps/mobile/src/services/sourceCandidates.js`。
- 新增 `apps/mobile/src/services/agentTasks.js`。
- 新增 `apps/mobile/tests/sourceCandidates.test.mjs`。
- 新增 `apps/mobile/tests/agentTasks.test.mjs`。

接口封装：

- `sourceCandidates.js`：
  - `listSourceCandidates(filters)` 对接 `GET /lead-source-candidates`。
  - `getSourceCandidate(candidateId)` 对接 `GET /lead-source-candidates/{candidate_id}`。
  - `reviewSourceCandidate(candidateId, payload)` 对接 `POST /lead-source-candidates/{candidate_id}/review-actions`。
  - 字段从后端 snake_case 映射到移动端 camelCase。
  - 保留风险等级、审核状态、抽取准入、证据链接、LLM 输出摘要、审计任务 id 等字段。
- `agentTasks.js`：
  - `startSourceDiscovery(payload)` 对接 `POST /agent-tasks/source-discovery/run`。
  - `getAgentTaskRun(taskRunId)` 对接 `GET /agent-task-runs/{id}`。
  - 字段从后端任务返回结构映射为移动端可展示结构。

未执行：

- 未实现移动端来源候选队列页面。
- 未实现移动端来源详情页面。
- 未实现移动端 Agent 手动调用页面。
- 未新增自动触达、私信、加好友或短信逻辑。
- 未执行 P2-E4-S2 或其他后续 Story。

## TDD 记录

RED：

```bash
node --test apps/mobile/tests/sourceCandidates.test.mjs apps/mobile/tests/agentTasks.test.mjs
```

结果：

```text
Error [ERR_MODULE_NOT_FOUND]: Cannot find module 'apps/mobile/src/services/sourceCandidates.js'
Error [ERR_MODULE_NOT_FOUND]: Cannot find module 'apps/mobile/src/services/agentTasks.js'
```

失败原因符合预期：移动端来源候选和 Agent 任务 service 尚未创建。

GREEN：

- 新增 `sourceCandidates.js`，通过 `apiClient` 对接真实后端来源候选 API，不使用 seed 数据。
- 新增 `agentTasks.js`，通过 `apiClient` 对接 Source Discovery 手动启动和任务状态查询 API。
- 新增两个目标测试文件，验证 endpoint、query 参数、payload 字段和映射结果。

## 验证结果

目标测试：

```bash
node --test apps/mobile/tests/sourceCandidates.test.mjs apps/mobile/tests/agentTasks.test.mjs
```

结果：

```text
7 passed
```

移动端完整测试：

```bash
npm --prefix apps/mobile test
```

结果：

```text
53 passed
```

语法验证：

```bash
node --check apps/mobile/src/services/sourceCandidates.js && node --check apps/mobile/src/services/agentTasks.js && node --check apps/mobile/tests/sourceCandidates.test.mjs && node --check apps/mobile/tests/agentTasks.test.mjs
```

结果：通过，退出码 0。

环境说明：

- 当前 shell 直接运行的 `node` 版本为 v18.17.0。
- 已使用当前移动端项目可用的 `npm --prefix apps/mobile test` 完成验证。
- 已尝试执行 `source ~/.nvm/nvm.sh && nvm use v22.22.0`，当前 shell 报错 `no such file or directory: /Users/linhuanbin/.nvm/nvm.sh`，因此本 Story 未能在 Node v22.22.0 下复验。
- 后续端到端联调阶段应先确认 nvm 初始化路径或直接使用项目指定 Node v22.22.0 runtime 后复验。

## 两轮独立评审记录

### 第一轮评审：API adapter 契约和后端 schema 对齐

结论：通过。

发现项：

- `sourceCandidates.js` 已对接后端真实 API 路径，不依赖 seed 作为最终数据源。
- 列表筛选字段与后端 `GET /lead-source-candidates` 对齐。
- 详情字段保留 `evidence_links`、`created_by_task_run_id`、`llm_output_summary`。
- 审核动作 payload 使用后端要求的 `action/reviewer_id/review_note`。
- `agentTasks.js` 启动 Source Discovery 时使用后端 schema：`country/cities/channel_strategy/keywords/limit`。

修正结果：

- 已统一移动端输出为 camelCase，便于后续页面直接使用。

### 第二轮评审：风险边界、触达隔离和回归风险

结论：通过。

发现项：

- 当前 Story 只新增 service/API adapter，不新增页面和触达动作。
- adapter 未包含自动私信、加好友、短信或批量触达接口。
- High/Forbidden 风险字段被保留给页面显示和审核判断。
- 目标测试 7 条通过，移动端完整测试 53 条通过。
- 新增文件语法检查通过。

修正结果：

- 第二轮未发现新增实质阻塞问题，无需追加业务代码修正。
