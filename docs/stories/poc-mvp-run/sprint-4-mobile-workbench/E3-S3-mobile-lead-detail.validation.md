# E3-S3 Validation：移动端线索详情

验证日期：2026-05-28  
Story：`E3-S3 移动端线索详情`

## 输入包检查

| 项目 | 结果 | 证据 |
|---|---|---|
| Story ID | 通过 | `docs/stories/sprint-4-mobile-workbench/E3-S3-mobile-lead-detail.md` |
| 用户价值 | 通过 | 客服/销售可查看客户证据、AI 建议、联系方式和跟进记录 |
| 依赖 | 通过 | E3-S2 线索池入口已实现，E2-S2 分级建议字段已作为 seed/view model 输入 |
| 原型对齐 | 通过 | 参考 `prototypes/mvp-mobile-agent/pages/lead-detail.html` |
| 强约束 | 通过 | 不在详情页直接自动发送社交消息；标记勿扰后排除触达 |

## 验收映射

| 验收项 | 当前证据 | 结论 |
|---|---|---|
| 显示客户基础信息 | `buildLeadDetailViewModel` 输出 `customerName/basicInfo`；页面渲染 | 通过 |
| 显示来源与证据 | `sources` 渲染证据文本和 URL；测试覆盖 `hasViewableEvidence` | 通过 |
| 显示经营状况判断 | `operatingSummary` 渲染为独立区块 | 通过 |
| 显示 AI 建议和推荐原因 | `aiAdvice.suggestion/reason/confidenceText/missingInfo/nextAction` 渲染 | 通过 |
| 显示联系方式 | `contacts` 渲染类型、用途和值 | 通过 |
| 显示跟进记录 | `followUps` 渲染时间线 | 通过 |
| 显示车源匹配入口 | `inventoryEntry` 渲染并调用 `uni.navigateTo` | 通过 |
| 支持标记勿扰 | `markLeadDoNotContact` 更新本地状态；页面按钮调用 | 通过 |
| 展示 C 级线索合规复核状态 | C 级输出 `待合规复核/合规已通过/合规未通过`；测试覆盖 | 通过 |

## QA / 风控检查

| 检查项 | 证据 | 结论 |
|---|---|---|
| 来源证据必须可查看 | 测试覆盖无 URL/无 evidence 时 `hasViewableEvidence=false` | 通过 |
| 标记勿扰后立即从触达任务排除 | `markLeadDoNotContact` 后 `canEnterOutreachQueue=false`；测试覆盖 | 通过 |
| 不在详情页直接自动发送社交消息 | 页面按钮为 `生成草稿`；view model `autoSendEnabled=false`；测试覆盖 | 通过 |
| C 级报价/合同前需合规复核 | C 级展示 `待合规复核`，不提供报价/合同动作 | 通过 |

## 实现文件

- `apps/mobile/src/pages.json`
- `apps/mobile/src/pages/leads/detail.vue`
- `apps/mobile/src/styles/leadDetail.css`
- `apps/mobile/src/data/leadDetailSeed.js`
- `apps/mobile/src/services/leadDetail.js`
- `apps/mobile/tests/leadDetail.test.mjs`

## 验证命令

```bash
source ~/.zshrc >/dev/null 2>&1 || true
nvm use v22.22.0 >/dev/null
npm --prefix apps/mobile run test
```

结果：

```text
13 passed
```

```bash
node --check apps/mobile/src/services/leadDetail.js
node --check apps/mobile/src/data/leadDetailSeed.js
```

结果：通过。

## 两轮独立评审记录

### 第一轮评审

结论：发现一个合规表达缺口，已修正。

发现项：

- 页面已覆盖基础信息、来源证据、经营判断、AI 建议、联系方式、跟进记录、车源入口和勿扰按钮。
- C 级线索能展示合规复核状态。
- 但底部按钮文案 `生成触达草稿` 仍含“触达”字样，虽然实现没有发送动作，但可能让使用者误解为可直接触达。

修正结果：

- 页面按钮文案改为 `生成草稿`。
- `buildLeadDetailViewModel` 增加 `outreachActionLabel` 和 `autoSendEnabled=false`。
- 测试断言详情页只允许生成草稿，不启用自动发送。
- 重新运行测试，结果通过。

### 第二轮评审

结论：未发现新增实质阻塞问题。

发现项：

- Story 验收项均有页面实现和测试映射。
- 来源证据可查看，并且缺证据状态可被识别。
- 标记勿扰后立即关闭触达候选资格。
- C 级显示合规复核状态，且页面未提供报价/合同动作。
- 页面仅提供草稿入口，不自动发送社交消息。

修正结果：

- 无新增代码修正。
- 将 API 接入和真实构建验证限制记录为残留风险。

## 残留风险

| 风险 | 当前处理 | 后续建议 |
|---|---|---|
| 详情页使用 seed 数据 | 满足当前 Story 的规则和页面验收 | 后续接入真实 API |
| 勿扰标记未持久化 | 当前本地状态即时排除触达 | 后续接入后端勿扰 API |
| 未完成真实构建/截图 | 当前环境缺少可用移动端依赖安装 | 依赖就绪后补跑 uni-app dev/build 与移动端截图验证 |

## 结论

E3-S3 已完成。当前实现满足移动端线索详情的客户信息、证据、经营判断、AI 建议、联系方式、跟进记录、车源入口、勿扰排除和 C 级合规状态要求。
