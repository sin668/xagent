# E3-S1 Validation：移动端智能体首页

验证日期：2026-05-28  
Story：`E3-S1 移动端智能体首页`

## 输入包检查

| 项目 | 结果 | 证据 |
|---|---|---|
| Story ID | 通过 | `docs/stories/sprint-4-mobile-workbench/E3-S1-mobile-agent-home.md` |
| 用户价值 | 通过 | 一线用户打开移动端即可看到今日任务、AI 状态和待处理线索 |
| 依赖 | 通过 | E1-S1 客户主体模型、E2-S2 AI 分级建议已作为统计字段约束 |
| 原型对齐 | 通过 | 参考 `prototypes/mvp-mobile-agent/pages/mobile-home.html` 的首页结构 |
| 强约束 | 通过 | 勿扰客户不进入待触达；High/Forbidden 不显示为可执行 |

## 验收映射

| 验收项 | 当前证据 | 结论 |
|---|---|---|
| 显示今日待处理 B/C 级线索数 | `dashboard.pendingPriorityCount` 渲染到 Hero；测试覆盖 B/C、pending、非勿扰过滤 | 通过 |
| 显示 AI 运行任务状态 | `dashboard.aiStatusText` 和 `dashboard.executableAiTasks` 渲染 AI 队列 | 通过 |
| 显示总候选线索 | `dashboard.totalCandidateLeads` 渲染指标卡 | 通过 |
| 显示 B 级比例 | `dashboard.bGradeRatioText` 渲染指标卡；测试覆盖候选池比例 | 通过 |
| 显示待跟进数 | `dashboard.pendingFollowUpCount` 渲染指标卡；测试覆盖 A/B/C、pending、非勿扰 | 通过 |
| 显示渠道表现摘要 | `dashboard.channelPerformance` 渲染官网/公开目录、搜索引擎等可执行渠道 | 通过 |
| 提供进入线索池、触达任务、详情页入口 | `entries` 包含三类入口并调用 `uni.navigateTo` | 通过 |

## QA / 风控检查

| 检查项 | 证据 | 结论 |
|---|---|---|
| 勿扰客户不计入待触达任务 | `getPendingPriorityLeads` 排除 `doNotContact`；测试覆盖 | 通过 |
| Invalid/Watch 不进入待跟进任务 | `pendingFollowUpCount` 仅统计 A/B/C；第一轮评审发现并修正 | 通过 |
| High/Forbidden 渠道任务不显示为可执行 | `filterExecutableAiTasks` 仅允许 Low/Medium；测试覆盖 | 通过 |
| High/Forbidden 渠道表现不作为可执行渠道展示 | `filterExecutableChannelPerformance` 仅允许 Low/Medium；seed 测试覆盖 | 通过 |

## 实现文件

- `apps/mobile/package.json`
- `apps/mobile/index.html`
- `apps/mobile/src/App.vue`
- `apps/mobile/src/main.js`
- `apps/mobile/src/manifest.json`
- `apps/mobile/src/pages.json`
- `apps/mobile/src/pages/home/index.vue`
- `apps/mobile/src/styles/home.css`
- `apps/mobile/src/data/homeSeed.js`
- `apps/mobile/src/services/homeMetrics.js`
- `apps/mobile/tests/homeMetrics.test.mjs`

## 验证命令

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

说明：当前环境无法解析 npm 镜像域名，且本地未安装移动端构建依赖；完整 uni-app/Vite 构建需待依赖可用后补跑。

## 两轮独立评审记录

### 第一轮评审

结论：发现一个实质规则缺口，已修正。

发现项：

- 首页已展示今日 B/C 优先线索、AI 运行状态、关键指标、渠道表现和三类入口。
- `getPendingPriorityLeads` 已排除勿扰客户。
- `filterExecutableAiTasks` 已排除 High/Forbidden。
- 但 `pendingFollowUpCount` 最初只判断 `followUpDueToday` 与 `pending`，会把 `Invalid` 且待跟进的数据计入待触达口径。

修正结果：

- 新增 `ACTIONABLE_GRADES = A/B/C`。
- `pendingFollowUpCount` 改为仅统计 A/B/C、pending、非勿扰线索。
- 保留测试中对 Invalid/Watch 不进入触达队列的约束。
- 重新运行 `npm --prefix apps/mobile run test`，结果通过。

### 第二轮评审

结论：未发现新增实质阻塞问题。

发现项：

- Story 验收项均能映射到页面实现和 `homeMetrics` 输出。
- 勿扰客户不会进入今日 B/C 优先线索或待跟进任务。
- High/Forbidden 风险渠道不会显示为可执行 AI 任务或可执行渠道表现。
- 页面结构符合移动端优先：首页 Hero、指标、AI 队列、渠道表现、快速入口和底部 Tab。
- 完整 uni-app 构建受当前 npm 网络/依赖环境限制，需后续补跑。

修正结果：

- 无新增代码修正。
- 将构建限制记录为残留风险，不作为已完成项宣称。

## 残留风险

| 风险 | 当前处理 | 后续建议 |
|---|---|---|
| 首页暂用 seed 数据 | 满足 E3-S1 首屏实现和验收展示 | E3-S2/E3-S3 或后续 API Story 接入真实接口 |
| 当前环境无法安装/解析 Vite 依赖 | 已完成规则测试和语法检查 | 依赖可用后补跑 uni-app dev/build 和真机/浏览器截图验证 |

## 结论

E3-S1 已完成。当前实现满足移动端智能体首页的核心展示、入口、勿扰过滤和渠道风险过滤要求；完整构建验证待移动端依赖安装环境可用后补跑。
