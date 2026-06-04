# Story P2-E4-S2：移动端来源候选队列页面

状态：Done  
Sprint：Sprint 3  
优先级：P1  
Epic：P2-E4

## 用户故事

作为第二阶段小范围运行的研发执行者，我希望完成“移动端来源候选队列页面”，以便系统可以按 BMAD 已冻结方案推进真实 LLM、来源发现、审核、抽取、审计和联调闭环。

## 上下文来源

- `docs/product/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行方案与产品技术设计.md`
- `_bmad-output/brainstorming/brainstorming-session-2026-06-02-第二阶段小范围运行-LLM来源发现Agent.md`
- `docs/superpowers/plans/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行Codex推进计划.md`
- `docs/AI协同开发执行标准.md`
- `AGENTS.md`

## Story 定义

**目标：** 实现移动端来源候选列表页，对齐原型 `source-candidates.html`。

**Files:**

- Modify: `apps/mobile/src/pages.json`
- Create: `apps/mobile/src/pages/sources/index.vue`
- Create: `apps/mobile/src/styles/sourceCandidates.css`
- Test: `apps/mobile/tests/sourceCandidatesPage.test.mjs`

**Codex 提示词：**

```text
请执行 P2-E4-S2：移动端来源候选队列页面。

要求：
1. 使用 superpowers:test-driven-development。
2. 页面参考 prototypes/mvp-mobile-agent/pages/source-candidates.html。
3. 展示 Low/Medium/High/Forbidden 风险分布。
4. 支持按风险、审核状态、国家、城市、平台筛选。
5. 列表卡片展示 URL/domain、风险等级、证据摘要、是否可抽取。
6. 页面必须通过 sourceCandidates service 调真实 API。
7. 运行移动端页面/service 测试。
8. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p2-e4-s2-执行结果.md。
不要执行下一个 Story。
```

**验收标准：**

- 页面可渲染真实 API 数据。
- 风险标签可见。

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

- 新增移动端来源候选队列页面：`apps/mobile/src/pages/sources/index.vue`。
- 新增独立页面样式：`apps/mobile/src/styles/sourceCandidates.css`。
- 更新页面注册：
  - `apps/mobile/src/pages.json` 增加 `pages/sources/index`。
  - `apps/mobile/pages.json` 增加 `src/pages/sources/index`，避免 H5 根配置与源码配置不一致。
- 更新底部导航：`apps/mobile/src/services/bottomTabs.js` 增加“来源”一级入口，并同步更新 `apps/mobile/tests/bottomTabs.test.mjs`。
- 新增页面契约测试：`apps/mobile/tests/sourceCandidatesPage.test.mjs`。

### 验收结果

- 页面参考原型 `prototypes/mvp-mobile-agent/pages/source-candidates.html`，包含来源审核标题、风险概览、风险筛选、风险分布、候选来源列表和底部导航。
- 页面通过 `sourceCandidatesService.listSourceCandidates()` 调用真实 API `/lead-source-candidates`，未使用 seed/mock 数据作为最终数据源。
- 支持按 `riskLevel`、`reviewStatus`、`country`、`city`、`platform` 筛选。
- 展示 Low/Medium/High/Forbidden 风险分布。
- 列表卡片展示 `sourceUrl`、`normalizedDomain`、`riskLevel`、`evidenceNote`、`approvedForExtraction`。
- 页面未包含自动私信、自动加好友、批量触达动作。

### TDD 记录

- RED：先创建 `apps/mobile/tests/sourceCandidatesPage.test.mjs`，运行 `node --test apps/mobile/tests/sourceCandidatesPage.test.mjs`，结果 `0/5 passed`，失败原因符合预期：页面未注册、页面和样式文件缺失。
- GREEN：补齐页面、样式、页面注册和底部导航后，运行 `node --test apps/mobile/tests/sourceCandidatesPage.test.mjs`，结果 `5/5 passed`。

### 验证命令

- `node --test apps/mobile/tests/sourceCandidatesPage.test.mjs`：`5/5 passed`。
- `npm --prefix apps/mobile test`：`58/58 passed`。
- `npm --prefix apps/mobile run build:h5`：通过，输出 `DONE Build complete.`。

### 构建异常处理

首次执行 `npm --prefix apps/mobile run build:h5` 失败，原因为 npm optional dependency 缺失：`Cannot find module @rollup/rollup-darwin-x64`。执行 `npm --prefix apps/mobile install` 后补齐依赖，再次构建通过。

### 第一轮独立多维度评审

- 结论：通过，无实质阻塞问题。
- 功能完整性：页面覆盖来源候选池、风险概览、筛选、风险分布和候选列表。
- API 对接：页面使用 `sourceCandidatesService.listSourceCandidates()`，符合真实 API 对接要求。
- 风控合规：页面只展示候选来源和可抽取状态，不提供触达、私信、加好友或绕过风险动作。
- 可测试性：新增页面契约测试覆盖页面注册、真实 service 调用、筛选字段、展示字段和禁止触达动作。
- 发现项：底部导航原先无“来源”入口，已作为本 Story 范围内必要导航修正。
- 修正结果：已更新 `bottomTabs.js` 和对应测试。

### 第二轮独立多维度评审

- 结论：通过，连续两轮未发现新增实质阻塞问题。
- 回归风险：移动端完整测试 `58/58 passed`，新增导航未破坏现有首页、线索、AI、洞察入口测试。
- 编译风险：H5 构建通过，确认 `.vue` 页面可被 uni-app 编译。
- 数据边界：页面 API 失败时显示错误态，不回退到 seed 数据，避免误判为真实来源。
- 合规边界：High/Forbidden 未在页面提供自动触达或自动放行动作；审核详情动作留给后续 Story。
- 修正结果：无需新增修正。

### 归档

- `_bmad-output/implementation-artifacts/codex-p2-e4-s2-执行结果.md`
