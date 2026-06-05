# Story P3-E7-S4：移动端客户详情页面

状态：实现完成
Sprint：Sprint 7
优先级：P1
Epic：P3-E7

## 用户故事

作为第三阶段小范围运行的研发执行者，我希望完成“移动端客户详情页面”，以便系统可以按 BMAD 已冻结方案推进线索完善、客户晋级、客户承接、清洗治理和 LangGraph 局部试点闭环。

## 上下文来源

- `docs/brainstorm/brainstorming-session-2026-06-04-第三阶段小范围运行-客户管理工作台.md`
- `docs/product/2026-06-04-海外车辆采购AI获客系统-第三阶段小范围运行方案与产品技术设计.md`
- `docs/architecture/2026-06-03-LLM-Agent服务编排选型分析.md`
- `prototypes/mvp-mobile-agent/design-brief.md`
- `docs/AI协同开发执行标准.md`
- `agents.md`

## Story 定义

**目标：** 展示客户补全资料、联系方式、来源证据、触达历史、意向车型、跟进记录和合规状态。

**Files:**

- Create/Modify: `apps/mobile/src/pages/customers/detail.vue`
- Modify: `apps/mobile/src/services/customers*.js`
- Test: `apps/mobile` 相关测试

**Codex 提示词：**

```text
请执行 P3-E7-S4：移动端客户详情页面。

要求：
1. 使用 superpowers:test-driven-development。
2. 严格依据第三阶段方案和本 Story 验收标准实现。
3. 保持 raw/staging/core/audit 分层，不让 AI 直接污染 core 数据。
4. 所有关键动作必须保留来源证据、操作人、时间和审计记录。
5. 不自动社交私信、不自动加好友、不自动发送触达消息。
6. 运行本 Story 对应测试，并按需执行相关联调验证。
7. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p3-e7-s4-执行结果.md。
8. 不要执行下一个 Story。
```

**验收标准：**

- 详情聚合 API 数据完整展示。
- 待补全字段明确标记。
- 勿扰和 C 级合规状态可见。
- 触达仍为人工记录，不出现自动发送。

**非目标：**

- 不实现报价合同。

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作。
- 不做 git 操作。
- 代码实现 Story 必须使用 `superpowers:test-driven-development`。
- 调试异常必须使用 `superpowers:systematic-debugging`。
- 完成前必须使用 `superpowers:verification-before-completion`。
- 完成后必须执行两轮独立多维度评审，并记录结论、发现项和修正结果。
- 必须执行必要的前后端真实联调，不允许只验证 seed 静态页面。
- 所有过程、结果、注解和文档使用中文。


## 通用风控边界

- 不自动社交私信。
- 不自动加好友。
- 不登录后批量采集。
- 不反爬规避。
- 不抓取非公开数据。
- High 来源未审核不得进入自动触达。
- Forbidden 来源不得作为客户晋级关键来源。
- Invalid 和 Watch 不进入触达队列。
- 勿扰客户不得再次进入触达队列。
- C 级客户报价、合同、付款、物流、清关、交付周期等动作前必须合规复核。
- 所有 AI 输出必须保存来源证据、prompt 版本、模型和审计记录。
- Agent 不得自动晋级客户、自动归并客户、自动恢复 Invalid、自动触达客户。

## 执行记录

执行时间：2026-06-04
执行者：Codex
执行方式：`superpowers:executing-plans` + `superpowers:test-driven-development` + `superpowers:verification-before-completion`

### 本次变更

- 更新 `apps/mobile/src/services/customers.js`，新增客户详情聚合 mapper、客户详情视图模型和 `getCustomerDetail(customerId)` 服务方法。
- 新增 `apps/mobile/src/pages/customers/detail.vue`，实现移动端客户详情页面。
- 新增 `apps/mobile/src/styles/customerDetail.css`，实现客户详情独立移动端样式和溢出约束。
- 新增 `apps/mobile/tests/customerDetail.test.mjs`，覆盖详情聚合字段、待补全字段、勿扰、C 级合规、触达历史和跟进记录映射。
- 新增 `apps/mobile/tests/customerDetailPage.test.mjs`，覆盖页面注册、真实 API 调用、分区展示和禁止自动触达动作。
- 更新 `apps/mobile/src/pages.json` 与 `apps/mobile/pages.json`，注册客户详情页面。

### 验收结果

- 详情聚合 API 数据完整展示：已通过，页面通过 `customersService.getCustomerDetail` 读取 `/customers/{id}`。
- 待补全字段明确标记：已通过，字段统一显示为 `{field} 待补全`。
- 勿扰和 C 级合规状态可见：已通过，页面展示“勿扰客户状态”和 `C级合规待复核`。
- 触达仍为人工记录，不出现自动发送：已通过，页面只提供“人工记录触达”跳转入口，不执行发送动作。
- 非目标“不实现报价合同”：未实现，符合 Story 边界。

### 测试记录

```bash
source ~/.zshrc >/dev/null 2>&1 || true
nvm use v22.22.0 >/dev/null
npm --prefix apps/mobile test
```

结果：`109 passed`

```bash
source ~/.zshrc >/dev/null 2>&1 || true
nvm use v22.22.0 >/dev/null
npm --prefix apps/mobile run build:h5
```

结果：`DONE  Build complete.`

```bash
source ~/.zshrc >/dev/null 2>&1 || true
conda activate booking-room
cd apps/api
python -m pytest tests/test_customer_detail_aggregate_api.py -q
```

结果：`4 passed`

### 两轮独立评审

#### 第一轮评审：数据边界与合规

结论：通过，修正后无新增阻塞问题。

发现项：

- 客户详情必须只读取 core 聚合客户详情，不得回退到 staging、seed 或 mock。
- 页面不得出现自动发送、自动私信、自动加好友、批量触达等动作。
- 页面可见字段使用了 `ownerTeamText/contactCountText/sourceCountText/vehicleIntentCountText/outreachCountText/followupCountText`，但视图模型初版未提供这些字段。

修正结果：

- 服务只调用 `/customers/{id}`，页面未读取 staging、seed 或 mock。
- 源码扫描和页面测试确认未出现自动发送、自动私信、自动加好友、批量触达等动作。
- 补齐视图模型字段，并新增断言覆盖。

#### 第二轮评审：移动端路由与体验

结论：通过，修正后无新增实质阻塞问题。

发现项：

- 客户详情页面初版只依赖 H5 查询参数或 `globalThis.onLoad`，小程序运行时路由参数不稳定。
- 页面需要显式展示“勿扰客户”文案，不能只依赖运行时 viewModel 文案。

修正结果：

- 改用 `@dcloudio/uni-app` 的 `onLoad`，并保留 H5 URL 查询参数兼容。
- 合规区域新增“勿扰客户状态必须在触达前人工核验。”可见文案。

### 后续衔接

- 下一 Story：`P3-E7-S5-mobile-followup-records-page.md`。
- 本 Story 不实现新增跟进记录表单、不实现完整 CRM、不实现报价合同、不实现自动触达。
