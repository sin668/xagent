# Story P2-E6-S2：管理后台第二阶段运行看板

状态：Done  
Sprint：Sprint 5  
优先级：P2  
Epic：P2-E6

## 用户故事

作为第二阶段小范围运行的研发执行者，我希望完成“管理后台第二阶段运行看板”，以便系统可以按 BMAD 已冻结方案推进真实 LLM、来源发现、审核、抽取、审计和联调闭环。

## 上下文来源

- `docs/product/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行方案与产品技术设计.md`
- `_bmad-output/brainstorming/brainstorming-session-2026-06-02-第二阶段小范围运行-LLM来源发现Agent.md`
- `docs/superpowers/plans/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行Codex推进计划.md`
- `docs/AI协同开发执行标准.md`
- `AGENTS.md`

## Story 定义

**目标：** 对齐原型 `admin-phase2.html`，展示第二阶段运行指标。

**Files:**

- Create: `apps/admin/src/services/phase2Dashboard.js`
- Modify: `apps/admin/src/App.vue`
- Test: `apps/admin/tests/phase2Dashboard.test.mjs`

**Codex 提示词：**

```text
请执行 P2-E6-S2：管理后台第二阶段运行看板。

要求：
1. 使用 superpowers:test-driven-development。
2. 页面参考 prototypes/mvp-mobile-agent/pages/admin-phase2.html。
3. 展示来源新增、可抽取来源、High 待审、LLM 成本、任务流、暂停阈值。
4. 管理后台必须调用真实 API，不只使用 seed 数据。
5. 运行 npm --prefix apps/admin test 或项目已有后台测试命令。
6. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p2-e6-s2-执行结果.md。
不要执行下一个 Story。
```

**验收标准：**

- 后台可展示真实 API 指标。
- High/Forbidden 风险突出显示。

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

### 实现内容

- 新增 `apps/admin/src/services/phase2Dashboard.js`：
  - 对接真实 API：`GET /dashboard/phase2`。
  - 支持 `channel_prefix` 查询参数。
  - 将后端 snake_case 指标归一化为后台页面可直接消费的 view model。
  - 输出来源新增、可抽取来源、High 待审、LLM 成本、任务流、暂停阈值、LLM 任务成本和 High/Forbidden 风险事件。
- 新增 `apps/admin/tests/phase2Dashboard.test.mjs`：
  - 覆盖 Phase2 指标归一化。
  - 覆盖任务流、暂停阈值、High/Forbidden 风险突出显示。
  - 覆盖真实 API 路径 `/dashboard/phase2` 与 `channel_prefix` 查询参数。
- 修改 `apps/admin/src/App.vue`：
  - 新增“第二阶段”后台导航入口。
  - 新增第二阶段小范围运行看板。
  - 页面挂载时调用 `fetchPhase2Dashboard({ baseUrl: import.meta.env.VITE_API_BASE_URL || '' })` 获取真实 API 指标。
  - API 异常时展示错误态，不使用 seed 数据伪装真实结果。
- 修改 `apps/admin/src/styles/admin.css`：
  - 补齐 Phase2 指标卡、任务流、暂停阈值进度条、High/Forbidden 风险列表样式。
- 修改 `apps/admin/package.json`：
  - 将 `src/services/phase2Dashboard.js` 加入 `check:syntax`。

### TDD 记录

- RED：
  - 先创建 `apps/admin/tests/phase2Dashboard.test.mjs`。
  - 首次运行 `npm --prefix apps/admin test` 失败，原因是 `apps/admin/src/services/phase2Dashboard.js` 尚不存在。
  - 失败符合预期，证明测试覆盖新增服务能力。
- GREEN：
  - 创建 `phase2Dashboard.js` 后，`npm --prefix apps/admin test` 通过，21 个后台测试全部通过。
  - 随后接入 `App.vue` 页面真实 API 调用，并完成构建验证。

### 验证结果

执行环境：

- `conda activate booking-room`
- `nvm use v22.22.0`
- Node：`v22.22.0 darwin-arm64`
- Python：`/opt/miniconda3/envs/booking-room/bin/python`，版本 `3.12.11`

验证命令与结果：

- `npm --prefix apps/admin test`
  - 结果：`21 passed`
- `npm --prefix apps/admin run check:syntax`
  - 结果：通过，包含 `src/services/phase2Dashboard.js`
- `npm --prefix apps/admin run build`
  - 结果：通过，Vite 构建成功
- `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_phase2_dashboard_api.py`
  - 结果：`2 passed`
  - 说明：使用真实 PostgreSQL 连接完成后端 `/dashboard/phase2` 回归验证。

### 验收结论

- 后台可展示真实 API 指标：通过。
- High/Forbidden 风险突出显示：通过。
- 页面参考 `prototypes/mvp-mobile-agent/pages/admin-phase2.html` 的核心结构：通过，已覆盖指标卡、端到端任务流、Agent Task Runs、暂停阈值、High/Forbidden 风险事件。
- 管理后台不只使用 seed 数据：通过，Phase2 看板通过 `fetchPhase2Dashboard` 调用真实 `/dashboard/phase2` API；接口异常时展示错误态。
- 未执行下一个 Story：通过。
- 未做锁操作：通过。
- 未做 git 操作：通过。

### 调试记录

- 首次构建在 Node 18/x64 环境下失败，根因是 Rollup/esbuild 原生可选依赖与当前 Node 架构不匹配。
- 根据用户要求切换到指定环境：`conda activate booking-room` 与 `nvm use v22.22.0`。
- 在 Node 22.22.0 darwin-arm64 环境下重新验证，后台测试、语法检查和构建均通过。

### 第一轮独立多维度评审

结论：通过，无新增实质阻塞问题。

评审维度：

- 需求覆盖：已覆盖来源新增、可抽取来源、High 待审、LLM 成本、任务流、暂停阈值。
- API 真实性：页面调用 `/dashboard/phase2`，没有用 seed 数据伪装 Phase2 指标。
- 风险边界：High/Forbidden 风险事件使用红色突出显示；guardrail 明确展示。
- 测试覆盖：服务层覆盖 view model、查询参数和 fetch URL；后端 Phase2 API 回归通过。
- 构建可用性：指定 Node 22.22.0 环境下 Vite 构建通过。

发现项与修正结果：

- 发现：Node 18/x64 环境与项目原生依赖架构不匹配，导致构建失败。
- 修正：改用用户指定的 Node 22.22.0 darwin-arm64 环境验证，构建通过；未保留临时 `@esbuild/darwin-x64` 依赖声明。

### 第二轮独立多维度评审

结论：通过，无新增实质阻塞问题。

复核维度：

- Story 边界：仅完成 `P2-E6-S2`，未推进 `P2-E6-S3`。
- 产品一致性：页面结构与 `admin-phase2.html` 的第二阶段运行看板一致，保持后台密度和管理视角。
- 技术一致性：沿用现有后台 `buildXView`、`fetchX` 服务模式；未引入新框架。
- 联调证据：前端构建与后端 `/dashboard/phase2` 真实 PostgreSQL 测试均有命令输出证明。
- 合规边界：没有新增任何自动触达、自动加好友、登录后批量采集或反爬规避能力。

发现项与修正结果：

- 发现：无新增实质问题。
- 修正：无需修正。
