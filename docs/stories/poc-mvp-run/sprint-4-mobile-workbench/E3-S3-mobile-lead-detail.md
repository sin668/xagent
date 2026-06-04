# Story E3-S3：移动端线索详情

## 基本信息

- Epic：E3 移动端线索工作台
- Sprint：Sprint 4 MVP 移动端线索工作台
- 优先级：P0
- 状态：Done
- 负责人建议：前端工程 + 客服/销售代表

## 用户故事

作为客服或销售，我希望打开线索详情后看到客户证据、AI 建议、联系方式和跟进记录。

## 业务价值

让线索可解释、可跟进、可交接。

## 依赖

- E3-S2 移动端线索池
- E2-S2 AI 线索分级建议

## 任务清单

- [x] 展示客户基础信息。
- [x] 展示来源与证据。
- [x] 展示经营状况判断。
- [x] 展示 AI 建议、推荐原因、缺失信息、下一步动作。
- [x] 展示联系方式和跟进记录。
- [x] 展示车源匹配入口。
- [x] 支持标记勿扰。
- [x] 展示 C 级线索合规复核状态。

## 验收标准

- 显示客户基础信息。
- 显示来源与证据。
- 显示经营状况判断。
- 显示 AI 建议和推荐原因。
- 显示跟进记录。
- 显示车源匹配入口。
- 支持标记勿扰。

## 非目标

- 不在详情页直接自动发送社交消息。

## QA / 风控检查

- [x] 来源证据必须可查看。
- [x] 标记勿扰后立即从触达任务排除。

## 交付记录

完成日期：2026-05-28

### 实现文件

- `apps/mobile/src/pages/leads/detail.vue`：移动端线索详情页。
- `apps/mobile/src/styles/leadDetail.css`：线索详情页样式。
- `apps/mobile/src/services/leadDetail.js`：详情页 view model、勿扰标记和触达队列排除规则。
- `apps/mobile/src/data/leadDetailSeed.js`：详情页 seed 数据，覆盖 B/C、证据、联系方式、跟进、车源匹配和合规状态。
- `apps/mobile/tests/leadDetail.test.mjs`：详情页规则测试。
- `apps/mobile/src/pages.json`：注册 `pages/leads/detail` 页面。

### 验收命令

```bash
source ~/.zshrc >/dev/null 2>&1 || true
nvm use v22.22.0 >/dev/null
npm --prefix apps/mobile run test
node --check apps/mobile/src/services/leadDetail.js
node --check apps/mobile/src/data/leadDetailSeed.js
```

结果：`13 passed`，语法检查通过。

### 两轮评审摘要

- 第一轮：发现“生成触达草稿”按钮仍可能让人误解为触达动作，已改为“生成草稿”，并在 view model 中显式标记 `autoSendEnabled=false`。
- 第二轮：未发现新增实质阻塞问题；客户信息、证据、经营判断、AI 建议、联系方式、跟进记录、车源入口、勿扰排除和 C 级合规状态均有实现和测试证据。

### 残留风险

- 当前详情页使用 seed 数据；后续 Story 需接入真实 API。
- 标记勿扰当前为本地状态即时生效；后续需接入后端勿扰 API 持久化。
- 当前环境未完成真实 uni-app 构建和移动端截图验证；依赖安装后需补跑构建/预览。
