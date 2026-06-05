# Story P3-E7-S5：移动端客户跟进记录页面

状态：实现完成
Sprint：Sprint 7
优先级：P1
Epic：P3-E7

## 用户故事

作为第三阶段小范围运行的研发执行者，我希望完成“移动端客户跟进记录页面”，以便系统可以按 BMAD 已冻结方案推进线索完善、客户晋级、客户承接、清洗治理和 LangGraph 局部试点闭环。

## 上下文来源

- `docs/brainstorm/brainstorming-session-2026-06-04-第三阶段小范围运行-客户管理工作台.md`
- `docs/product/2026-06-04-海外车辆采购AI获客系统-第三阶段小范围运行方案与产品技术设计.md`
- `docs/architecture/2026-06-03-LLM-Agent服务编排选型分析.md`
- `prototypes/mvp-mobile-agent/design-brief.md`
- `docs/AI协同开发执行标准.md`
- `agents.md`

## Story 定义

**目标：** 客服/销售可在移动端查看和新增客户跟进记录。

**Files:**

- Create/Modify: `apps/mobile/src/pages/customers/followups.vue`
- Create/Modify: `apps/mobile/src/services/customerFollowups*.js`
- Test: `apps/mobile` 相关测试

**Codex 提示词：**

```text
请执行 P3-E7-S5：移动端客户跟进记录页面。

要求：
1. 使用 superpowers:test-driven-development。
2. 严格依据第三阶段方案和本 Story 验收标准实现。
3. 保持 raw/staging/core/audit 分层，不让 AI 直接污染 core 数据。
4. 所有关键动作必须保留来源证据、操作人、时间和审计记录。
5. 不自动社交私信、不自动加好友、不自动发送触达消息。
6. 运行本 Story 对应测试，并按需执行相关联调验证。
7. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p3-e7-s5-执行结果.md。
8. 不要执行下一个 Story。
```

**验收标准：**

- 展示触达历史和跟进时间线。
- 可新增跟进记录和下一次跟进时间。
- 标记勿扰时提示硬阻断影响。
- 按钮不被底部导航遮挡。

**非目标：**

- 不自动发送消息。

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

### 实现摘要

- 新增 `apps/mobile/src/pages/customers/followups.vue`，支持查看客户触达与跟进时间线、新增人工跟进记录、填写下一次跟进时间、标记勿扰和触发合规复核。
- 新增 `apps/mobile/src/services/customerFollowups.js`，封装 `GET /customers/{id}/followups` 和 `POST /customers/{id}/followups`，并将后端 snake_case 响应映射为移动端展示模型。
- 新增 `apps/mobile/src/styles/customerFollowups.css`，底部操作栏固定在手机壳宽度内，并为内容区预留安全距离，避免被底部导航遮挡。
- 新增 `apps/mobile/tests/customerFollowups.test.mjs` 和 `apps/mobile/tests/customerFollowupsPage.test.mjs`，覆盖 mapper、payload、真实 API 契约、页面注册、无自动发送动作和布局约束。
- 更新 `apps/mobile/src/pages.json` 和 `apps/mobile/pages.json`，注册客户跟进记录页面。

### 验收结果

- 展示触达历史和跟进时间线：通过。
- 可新增跟进记录和下一次跟进时间：通过。
- 标记勿扰时提示硬阻断影响：通过。
- 按钮不被底部导航遮挡：通过。
- 非目标“不自动发送消息”：通过，页面和 payload 不包含发送、加好友、自动私信类动作。

### 验证命令

```bash
source ~/.zshrc >/dev/null 2>&1 || true
nvm use v22.22.0 >/dev/null
cd apps/mobile
node --test tests/customerFollowups.test.mjs tests/customerFollowupsPage.test.mjs
```

结果：9 passed。

```bash
source ~/.zshrc >/dev/null 2>&1 || true
nvm use v22.22.0 >/dev/null
cd apps/mobile
npm test
```

结果：118 passed。

```bash
source ~/.zshrc >/dev/null 2>&1 || true
nvm use v22.22.0 >/dev/null
cd apps/mobile
npm run build:h5
```

结果：`DONE Build complete.`

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_customer_followups_api.py -q
```

结果：5 passed。

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_customer_detail_aggregate_api.py tests/test_customer_followups_api.py -q
```

结果：9 passed。

### 两轮独立评审

第一轮评审：真实 API、审计字段、勿扰硬阻断、无自动发送。

结论：通过，无新增阻塞问题。

发现项：

- mapper 初始测试只校验记录人，未校验跟进记录创建时间，不足以覆盖审计要求。
- 页面必须只通过真实客户跟进 API 读取和新增记录，不得读取 seed/mock/staging。
- 标记勿扰必须明确提示“勿扰客户不得再次进入触达队列”。

修正结果：

- 将测试期望更新为 `记录人 + 创建时间`，保留完整审计文本。
- 源码扫描和页面测试确认 `followups.vue` 只调用 `customerFollowupsService`，未读取 seed/mock/staging。
- 勿扰硬阻断文案已在页面和服务测试中覆盖。

第二轮评审：移动端路由、底部操作条、UI 溢出、中文文案。

结论：通过，无新增实质阻塞问题。

发现项：

- 页面需要同时兼容 uni-app `onLoad` 参数和 H5 查询参数。
- 底部保存按钮必须固定在底部导航上方，且宽度限制在手机壳内。
- 页面不得出现自动发送、自动私信、自动加好友等动作入口。

修正结果：

- 页面使用 `@dcloudio/uni-app` 的 `onLoad`，并保留 H5 URL 查询参数兼容。
- 样式使用 `width: min(100vw, var(--phone-width, 430px))`、内容区底部 padding 和 `followup-action-bar-above-safe-area`。
- 源码扫描和测试确认未出现自动发送类动作，仅保存人工 CRM 跟进记录。

### 结果文档

- `_bmad-output/implementation-artifacts/codex-p3-e7-s5-执行结果.md`
