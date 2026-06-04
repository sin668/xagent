# Story P2-E4-S3：移动端来源详情与审核动作页面

状态：Done  
Sprint：Sprint 3  
优先级：P1  
Epic：P2-E4

## 用户故事

作为第二阶段小范围运行的研发执行者，我希望完成“移动端来源详情与审核动作页面”，以便系统可以按 BMAD 已冻结方案推进真实 LLM、来源发现、审核、抽取、审计和联调闭环。

## 上下文来源

- `docs/product/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行方案与产品技术设计.md`
- `_bmad-output/brainstorming/brainstorming-session-2026-06-02-第二阶段小范围运行-LLM来源发现Agent.md`
- `docs/superpowers/plans/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行Codex推进计划.md`
- `docs/AI协同开发执行标准.md`
- `AGENTS.md`

## Story 定义

**目标：** 实现来源详情、证据、LLM 摘要、审计和审核动作。

**Files:**

- Create: `apps/mobile/src/pages/sources/detail.vue`
- Test: `apps/mobile/tests/sourceDetailPage.test.mjs`

**Codex 提示词：**

```text
请执行 P2-E4-S3：移动端来源详情与审核动作页面。

要求：
1. 使用 superpowers:test-driven-development。
2. 页面参考 prototypes/mvp-mobile-agent/pages/source-detail.html。
3. 展示 URL/domain、风险、审核状态、approved_for_extraction、证据摘要、LLM 输出摘要、agent_task_run_id。
4. 支持通过进入只读抽取、驳回、标记高风险、暂停渠道、添加备注。
5. 页面必须明确：审核通过只代表允许抽取，不代表允许触达。
6. Forbidden 不显示通过按钮或点击后被后端阻断并提示。
7. 运行移动端页面/service 测试。
8. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p2-e4-s3-执行结果.md。
不要执行下一个 Story。
```

**验收标准：**

- 审核动作调用真实 API。
- 风险边界在页面可见。

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

- 新增移动端来源详情与审核动作页面：`apps/mobile/src/pages/sources/detail.vue`。
- 更新页面注册：
  - `apps/mobile/src/pages.json` 增加 `pages/sources/detail`。
  - `apps/mobile/pages.json` 增加 `src/pages/sources/detail`。
- 复用并扩展来源页面样式：`apps/mobile/src/styles/sourceCandidates.css`。
- 新增页面契约测试：`apps/mobile/tests/sourceDetailPage.test.mjs`。

### 验收结果

- 页面参考原型 `prototypes/mvp-mobile-agent/pages/source-detail.html`。
- 页面通过 `sourceCandidatesService.getSourceCandidate()` 调用真实详情 API。
- 页面通过 `sourceCandidatesService.reviewSourceCandidate()` 调用真实审核动作 API。
- 展示 `sourceUrl`、`normalizedDomain`、`riskLevel`、`reviewStatus`、`approvedForExtraction`、`evidenceNote`、`llmOutputSummary`、`createdByTaskRunId`、`auditTaskRunId`。
- 支持五类审核动作：`approve_for_extraction`、`reject`、`mark_high_risk`、`pause_channel`、`add_review_note`。
- 页面明确展示“审核通过只代表允许抽取，不代表允许触达”。
- Forbidden 来源不展示“只读抽取”通过按钮；即使前端触发，也在提交前阻断，并提示 Forbidden 不得进入自动抽取。
- 未新增自动私信、自动加好友、批量触达、登录后采集或反爬规避动作。

### TDD 记录

- RED：先创建 `apps/mobile/tests/sourceDetailPage.test.mjs`，运行 `node --test apps/mobile/tests/sourceDetailPage.test.mjs`，结果 `1/6 passed`，失败原因符合预期：详情页未注册、详情页文件缺失。
- GREEN：补齐详情页、页面注册和样式后，运行 `node --test apps/mobile/tests/sourceDetailPage.test.mjs`，结果 `6/6 passed`。

### 验证命令

- `node --test apps/mobile/tests/sourceDetailPage.test.mjs`：`6/6 passed`。
- `npm --prefix apps/mobile test`：`64/64 passed`。
- `npm --prefix apps/mobile run build:h5`：通过，输出 `DONE Build complete.`。

### 第一轮独立多维度评审

- 结论：通过，无实质阻塞问题。
- 功能完整性：详情页覆盖来源 URL/domain、风险、审核状态、可抽取状态、证据、LLM 摘要和审计字段。
- API 对接：详情加载和审核动作均通过 `sourceCandidatesService`，未使用 seed/mock 数据作为最终数据源。
- 风险边界：Forbidden 不展示通过按钮；审核通过文案明确只允许抽取，不允许触达。
- 测试覆盖：页面契约测试覆盖注册、列表跳转、真实 service 调用、展示字段、五类审核动作和 Forbidden 约束。
- 发现项：详情页需要同步注册到源码和根部两份 `pages.json`，否则 H5 路由可能不可达。
- 修正结果：已同步更新两份页面配置。

### 第二轮独立多维度评审

- 结论：通过，连续两轮未发现新增实质阻塞问题。
- 回归风险：移动端完整测试 `64/64 passed`，新增页面未破坏已有 service、底部导航、来源队列和其他移动端页面测试。
- 编译风险：H5 构建通过，确认新增 `.vue` 页面和样式可被 uni-app 编译。
- 合规边界：页面没有任何自动触达能力；五类动作仅为来源审核动作，并保留后端风险闸门。
- 范围控制：未实现下一 Story 的 Agent 手动调用页面或任务状态展示。
- 修正结果：无需新增修正。

### 归档

- `_bmad-output/implementation-artifacts/codex-p2-e4-s3-执行结果.md`
