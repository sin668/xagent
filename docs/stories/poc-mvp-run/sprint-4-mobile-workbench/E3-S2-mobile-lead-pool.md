# Story E3-S2：移动端线索池

## 基本信息

- Epic：E3 移动端线索工作台
- Sprint：Sprint 4 MVP 移动端线索工作台
- 优先级：P0
- 状态：Done
- 负责人建议：前端工程 + 线索运营

## 用户故事

作为线索运营或客服，我希望在移动端筛选和查看不同状态的线索。

## 业务价值

让团队可以随时处理和复核线索。

## 依赖

- E1-S1 定义客户主体模型

## 任务清单

- [x] 实现线索池列表页。
- [x] 支持待处理、B 级、C 级、超时、勿扰筛选。
- [x] 每张线索卡展示客户名称、城市、客户类型、渠道、等级和风险标签。
- [x] C 级线索展示销售交付和合规复核状态。
- [x] 默认列表排除无效线索和勿扰线索。
- [x] 支持进入线索详情页。

## 验收标准

- 支持按待处理、B 级、C 级、超时、勿扰筛选。
- 每张线索卡显示客户名称、城市、客户类型、渠道、等级和风险标签。
- C 级线索明确标识交付销售和合规复核。
- 无效线索和勿扰线索不会进入默认待处理队列。

## 非目标

- MVP 不做高级多条件查询。

## QA / 风控检查

- [x] 列表默认不暴露勿扰客户为待触达。
- [x] 风险标签清晰可见。

## 交付记录

完成日期：2026-05-28

### 实现文件

- `apps/mobile/src/pages/leads/index.vue`：移动端线索池页面，包含搜索提示、筛选 chip、线索卡和底部导航。
- `apps/mobile/src/styles/leadPool.css`：线索池移动端样式。
- `apps/mobile/src/services/leadPool.js`：线索池筛选、标签和卡片视图模型逻辑。
- `apps/mobile/src/data/leadPoolSeed.js`：线索池 seed 数据，覆盖 B/C、勿扰、Invalid、Watch、超时等场景。
- `apps/mobile/tests/leadPool.test.mjs`：线索池筛选和卡片规则测试。
- `apps/mobile/src/pages.json`：注册 `pages/leads/index` 页面。

### 验收命令

```bash
source ~/.zshrc >/dev/null 2>&1 || true
nvm use v22.22.0 >/dev/null
npm --prefix apps/mobile run test
node --check apps/mobile/src/services/leadPool.js
node --check apps/mobile/src/data/leadPoolSeed.js
```

结果：`9 passed`，语法检查通过。

### 两轮评审摘要

- 第一轮：发现 C 级合规标签过于笼统，容易误解为已完成复核；已修正为 `待合规复核 / 合规已通过 / 合规未通过`，并补充测试。
- 第二轮：未发现新增实质阻塞问题；默认待处理队列排除 Invalid、Watch 和勿扰，B/C/超时/勿扰筛选、风险标签、C 级销售交付和合规状态均有测试与页面证据。

### 残留风险

- 当前线索池使用 seed 数据；后续 Story 需接入后端 API。
- 当前环境未完成真实 uni-app 构建和移动端截图验证；依赖安装后需补跑构建/预览。
