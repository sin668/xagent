# Story P3-E8-S2：管理后台第三阶段指标与风控看板

状态：实现完成
Sprint：Sprint 8
优先级：P2
Epic：P3-E8

## 用户故事

作为第三阶段小范围运行的研发执行者，我希望完成“管理后台第三阶段指标与风控看板”，以便系统可以按 BMAD 已冻结方案推进线索完善、客户晋级、客户承接、清洗治理和 LangGraph 局部试点闭环。

## 上下文来源

- `docs/brainstorm/brainstorming-session-2026-06-04-第三阶段小范围运行-客户管理工作台.md`
- `docs/product/2026-06-04-海外车辆采购AI获客系统-第三阶段小范围运行方案与产品技术设计.md`
- `docs/architecture/2026-06-03-LLM-Agent服务编排选型分析.md`
- `prototypes/mvp-mobile-agent/design-brief.md`
- `docs/AI协同开发执行标准.md`
- `agents.md`

## Story 定义

**目标：** 管理后台展示第三阶段客户承接、线索补全、清洗治理和风险事件。

**Files:**

- Create/Modify: `apps/admin/src/pages/Phase3Dashboard.vue` 或对应页面
- Modify: `apps/admin/src/services/*.ts`
- Test: `apps/admin` 相关测试

**Codex 提示词：**

```text
请执行 P3-E8-S2：管理后台第三阶段指标与风控看板。

要求：
1. 使用 superpowers:test-driven-development。
2. 严格依据第三阶段方案和本 Story 验收标准实现。
3. 保持 raw/staging/core/audit 分层，不让 AI 直接污染 core 数据。
4. 所有关键动作必须保留来源证据、操作人、时间和审计记录。
5. 不自动社交私信、不自动加好友、不自动发送触达消息。
6. 运行本 Story 对应测试，并按需执行相关联调验证。
7. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p3-e8-s2-执行结果.md。
8. 不要执行下一个 Story。
```

**验收标准：**

- 展示有效客户承接率。
- 展示深挖补全、客户晋级、清洗建议、风险事件。
- 风险指标目标 0 明确可见。
- 不展示自动触达能力。

**非目标：**

- 不实现复杂 BI。

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

- 新增 `apps/admin/src/services/phase3Dashboard.js`，归一化 `GET /phase3-dashboard/metrics` 返回的第三阶段指标。
- 新增 `apps/admin/tests/phase3Dashboard.test.mjs`，覆盖指标视图、后端接口路径和后台页面风控文案。
- 更新 `apps/admin/src/App.vue`，新增“第三阶段指标与风控”后台看板，展示有效客户承接率、深挖补全、客户晋级、清洗治理、风险违规目标 0 和人工触达门禁。
- 更新 `apps/admin/src/styles/admin.css`，补充第三阶段看板样式，保持后台工作台密集、可扫描、8px 圆角以内的设计规则。
- 更新 `apps/admin/package.json`，将 `phase3Dashboard.js` 纳入 `check:syntax`。

### 验收结果

- 展示有效客户承接率：通过，显示 `effective_customer_acceptance_rate` 及首次跟进分子/分母。
- 展示深挖补全、客户晋级、清洗建议、风险事件：通过，展示补全成功率、字段采纳率、晋级率、联系方式完整率、意向车型覆盖率、清洗采纳率、重复归并率、Watch 恢复率、风险违规数。
- 风险指标目标 0 明确可见：通过，页面显示“风险违规目标 0”和 `目标 0` 状态。
- 不展示自动触达能力：通过，仅展示“客户触达仅人工、好友请求禁止、登录批量采集禁用”的风控状态，不提供发送、加好友或触达操作。
- 非目标“不实现复杂 BI”：遵守，本次只做只读管理看板，不新增复杂筛选、报表建模或 BI 组件。

### TDD 记录

红灯命令：

```bash
cd apps/admin
source ~/.zshrc >/dev/null 2>&1 || true
nvm use v22.22.0 >/dev/null
node --test tests/phase3Dashboard.test.mjs
```

红灯结果：

```text
ERR_MODULE_NOT_FOUND: Cannot find module 'apps/admin/src/services/phase3Dashboard.js'
```

结论：红灯符合预期，第三阶段后台看板服务和页面入口尚未实现。

绿灯命令：

```bash
cd apps/admin
source ~/.zshrc >/dev/null 2>&1 || true
nvm use v22.22.0 >/dev/null
node --test tests/phase3Dashboard.test.mjs
```

绿灯结果：

```text
3 passed
```

### 验证命令

```bash
source ~/.zshrc >/dev/null 2>&1 || true
nvm use v22.22.0 >/dev/null
npm --prefix apps/admin test
```

结果：27 passed。

```bash
source ~/.zshrc >/dev/null 2>&1 || true
nvm use v22.22.0 >/dev/null
npm --prefix apps/admin run check:syntax
```

结果：退出码 0。

```bash
source ~/.zshrc >/dev/null 2>&1 || true
nvm use v22.22.0 >/dev/null
npm --prefix apps/admin run build
```

结果：Vite build 通过，19 modules transformed。

```bash
source ~/.zshrc >/dev/null 2>&1 || true
conda activate booking-room
cd apps/api
python -m pytest tests/test_phase3_metrics_service.py -q
```

结果：3 passed。

### 两轮独立评审

第一轮评审：数据/API/指标口径/风控边界。

结论：通过，无新增阻塞问题。

发现项：

- 第三阶段看板必须读取真实 `/phase3-dashboard/metrics`，不能使用 seed 或静态 mock。
- 页面必须同时表达风险目标 0 和人工触达门禁，避免误解为可自动触达。
- 初版加载态样式存在风险：未加载数据时 `riskViolationTargetZero` 默认 false，可能显示红色状态。

修正结果：

- 新增 `fetchPhase3Dashboard` 直接请求 `/phase3-dashboard/metrics`。
- 页面只展示“客户触达仅人工、好友请求禁止、登录批量采集禁用/异常开启”状态，不提供任何操作按钮。
- 修正 `phase3StatusClass` 判断顺序，加载期间优先显示 amber。

第二轮评审：页面集成/构建/非目标/回归。

结论：通过，无新增实质阻塞问题。

发现项：

- 需要确认第三阶段入口已加入侧边导航并存在 `id="phase3"`。
- 需要确认新增服务纳入后台语法检查，避免后续遗漏。
- 需要确认本 Story 没有新增复杂 BI、客户晋级、清洗执行或触达动作。

修正结果：

- `App.vue` 已新增第三阶段导航和 section。
- `apps/admin/package.json` 的 `check:syntax` 已纳入 `src/services/phase3Dashboard.js`。
- 源码与测试确认本 Story 只读展示指标，不新增发送、私信、加好友、晋级、归并、恢复或触达能力。

### 结果文档

- `_bmad-output/implementation-artifacts/codex-p3-e8-s2-执行结果.md`
