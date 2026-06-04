# E3-S1 移动端智能体首页执行结果

执行日期：2026-05-28  
Story：`docs/stories/sprint-4-mobile-workbench/E3-S1-mobile-agent-home.md`  
Story lock owner：`codex-E3-S1-mobile-agent-home`

## 执行范围

- 创建 `apps/mobile` uni-app/Vue3 最小应用骨架。
- 实现移动端智能体首页。
- 展示今日待处理 B/C 线索、AI 运行状态、总候选线索、B 级比例、待跟进数和渠道表现。
- 提供线索池、触达任务、线索详情入口。
- 抽取首页统计规则，测试覆盖勿扰和渠道风险过滤。

## 主要改动

- `apps/mobile/src/pages/home/index.vue`
  - 实现首页 Hero、指标卡、AI 作业队列、渠道表现、快速入口和底部 Tab。
- `apps/mobile/src/styles/home.css`
  - 实现移动端优先布局和视觉样式。
- `apps/mobile/src/services/homeMetrics.js`
  - 实现 `getPendingPriorityLeads`、`filterExecutableAiTasks`、`filterExecutableChannelPerformance`、`buildHomeDashboard`。
- `apps/mobile/src/data/homeSeed.js`
  - 提供 MVP 首页 seed 数据，并包含 High 风险样本以验证其不会作为可执行项展示。
- `apps/mobile/tests/homeMetrics.test.mjs`
  - 覆盖 B/C 待处理、勿扰排除、High/Forbidden 过滤、候选池指标、seed dashboard 风控边界。
- `apps/mobile/package.json`、`apps/mobile/src/main.js`、`apps/mobile/src/App.vue`、`apps/mobile/src/pages.json`、`apps/mobile/src/manifest.json`、`apps/mobile/index.html`
  - 创建 uni-app/Vue3 子应用基础结构。

## 验收结果

| 验收项 | 结果 | 证据 |
|---|---|---|
| 显示今日待处理 B/C 级线索数 | 通过 | Hero 渲染 `dashboard.pendingPriorityCount`；测试覆盖 |
| 显示 AI 运行任务状态 | 通过 | Hero 和 AI 作业队列渲染 `aiStatusText`、`executableAiTasks` |
| 显示总候选线索 | 通过 | 指标卡渲染 `totalCandidateLeads` |
| 显示 B 级比例 | 通过 | 指标卡渲染 `bGradeRatioText` |
| 显示待跟进数 | 通过 | 指标卡渲染 `pendingFollowUpCount`，且排除勿扰/Invalid |
| 显示渠道表现摘要 | 通过 | 渲染 `channelPerformance`，仅显示 Low/Medium |
| 提供进入线索池、触达任务、详情页入口 | 通过 | `entries` 三入口调用 `uni.navigateTo` |
| 勿扰客户不计入待触达任务 | 通过 | `getPendingPriorityLeads` 与测试覆盖 |
| High/Forbidden 渠道任务不显示为可执行 | 通过 | `filterExecutableAiTasks` 与 seed 测试覆盖 |

## 验证命令与结果

```bash
source ~/.zshrc >/dev/null 2>&1 || true
nvm use v22.22.0 >/dev/null
npm --prefix apps/mobile run test
```

结果：

```text
4 passed
```

```bash
npm --prefix apps/mobile run check:syntax
```

结果：通过。

```bash
npm --prefix apps/mobile exec vite -- --version
```

结果：

```text
npm error network request to https://registry.npmmirror.com/vite failed, reason: getaddrinfo ENOTFOUND registry.npmmirror.com
```

说明：当前环境无法解析 npm 镜像域名，且移动端构建依赖未在本地可用；未宣称完整 uni-app 构建通过。

## 两轮独立评审

### 第一轮评审

结论：发现一个实质缺口，已修正。

发现项：

- 页面已覆盖 Story 展示内容和入口。
- 勿扰客户已从今日 B/C 优先处理队列排除。
- High/Forbidden 已从 AI 可执行任务过滤。
- 待跟进统计最初没有限定 A/B/C，会把 Invalid 的待跟进标记计入触达口径。

修正结果：

- 在 `homeMetrics.js` 增加 `ACTIONABLE_GRADES`。
- `pendingFollowUpCount` 改为仅统计 A/B/C、pending、非勿扰线索。
- 重新运行移动端测试，结果 `4 passed`。

### 第二轮评审

结论：未发现新增实质阻塞问题，E3-S1 可收口。

发现项：

- 首页信息结构与原型一致，且更明确标注仅展示可执行风险等级。
- 业务规则测试覆盖勿扰、Invalid/Watch 隔离、High/Forbidden 过滤。
- 快速入口已提供线索池、触达任务、线索详情路径。
- 当前环境无法完成 Vite/uni-app 构建验证，属于依赖网络环境限制。

修正结果：

- 无新增修正。
- 已在 Story 和 validation 记录构建验证限制。

## 残留风险与后续建议

| 风险 | 当前处理 | 后续建议 |
|---|---|---|
| 首页使用 seed 数据 | 满足当前 Story 页面与规则验证 | 后续 Story 接入后端 API |
| 未完成真实构建/截图 | 受 npm 网络和本地依赖限制 | 依赖安装完成后补跑 uni-app build/dev 与移动端截图 |

## 下一接力点

E3-S1 已完成并应释放 Story lock。下一 Story 仍需按锁、TDD、测试、两轮评审、回写、释放锁的流程单独执行。
