# Story E3-S1：移动端智能体首页

## 基本信息

- Epic：E3 移动端线索工作台
- Sprint：Sprint 4 MVP 移动端线索工作台
- 优先级：P0
- 状态：Done
- 负责人建议：前端工程 + 产品负责人

## 用户故事

作为一线用户，我希望打开移动端后看到今日任务、AI 状态和待处理线索，以便快速进入工作。

## 业务价值

降低使用门槛，让移动端成为日常作业入口。

## 依赖

- E1-S1 定义客户主体模型
- E2-S2 AI 线索分级建议

## 任务清单

- [x] 使用 uni-app/Vue3 实现首页。
- [x] 展示今日待处理 B/C 级线索数。
- [x] 展示 AI 运行任务状态。
- [x] 展示总候选线索、B 级比例、待跟进数。
- [x] 展示渠道表现摘要。
- [x] 提供进入线索池、触达任务、详情页的入口。
- [x] 适配移动端优先交互。

## 验收标准

- 显示今日待处理 B/C 级线索数。
- 显示 AI 运行任务状态。
- 显示关键指标：总候选线索、B 级比例、待跟进数。
- 显示渠道表现摘要。

## 非目标

- 首页不做复杂 BI。

## QA / 风控检查

- [x] 勿扰客户不计入待触达任务。
- [x] High/Forbidden 渠道任务不显示为可执行。

## 交付记录

完成日期：2026-05-28

### 实现文件

- `apps/mobile/package.json`：移动端子应用脚本与 uni-app/Vue3 依赖声明。
- `apps/mobile/src/pages/home/index.vue`：移动端智能体首页，包含今日优先线索、AI 队列、关键指标、渠道表现和入口。
- `apps/mobile/src/styles/home.css`：移动端优先首页样式。
- `apps/mobile/src/services/homeMetrics.js`：首页指标、勿扰过滤和渠道风险过滤逻辑。
- `apps/mobile/src/data/homeSeed.js`：PoC/MVP 首页演示数据与 dashboard 构建。
- `apps/mobile/tests/homeMetrics.test.mjs`：首页业务规则测试。
- `apps/mobile/src/main.js`、`apps/mobile/src/App.vue`、`apps/mobile/src/pages.json`、`apps/mobile/src/manifest.json`、`apps/mobile/index.html`：uni-app/Vue3 最小应用骨架。

### 验收命令

```bash
source ~/.zshrc >/dev/null 2>&1 || true
nvm use v22.22.0 >/dev/null
npm --prefix apps/mobile run test
npm --prefix apps/mobile run check:syntax
```

结果：`4 passed`，语法检查通过。

补充验证：

```bash
npm --prefix apps/mobile exec vite -- --version
```

结果：当前沙箱无法解析 `registry.npmmirror.com`，且本地未安装移动端构建依赖，因此完整 uni-app/Vite 构建需在依赖安装完成后执行。

### 两轮评审摘要

- 第一轮：发现待跟进统计最初会把 `Invalid` 且 `followUpDueToday=true` 的线索计入队列；已修正为仅统计 A/B/C、pending、非勿扰线索，并用测试覆盖。
- 第二轮：未发现新增实质阻塞问题；首页验收指标、勿扰过滤、High/Forbidden 过滤和入口展示均有实现与测试证据。

### 残留风险

- 当前 Story 使用静态 seed 数据支撑首页展示；后续 Story 需要接入 API 数据源。
- 由于网络/依赖限制，本轮未完成真实 uni-app 构建和手机端截图验证；依赖安装后需补跑 `npm --prefix apps/mobile run dev` 或对应 uni-app 构建命令。
