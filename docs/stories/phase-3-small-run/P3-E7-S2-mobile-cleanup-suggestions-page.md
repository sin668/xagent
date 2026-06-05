# Story P3-E7-S2：移动端清洗建议队列页面

状态：实现完成
Sprint：Sprint 7
优先级：P1
Epic：P3-E7

## 用户故事

作为第三阶段小范围运行的研发执行者，我希望完成“移动端清洗建议队列页面”，以便系统可以按 BMAD 已冻结方案推进线索完善、客户晋级、客户承接、清洗治理和 LangGraph 局部试点闭环。

## 上下文来源

- `docs/brainstorm/brainstorming-session-2026-06-04-第三阶段小范围运行-客户管理工作台.md`
- `docs/product/2026-06-04-海外车辆采购AI获客系统-第三阶段小范围运行方案与产品技术设计.md`
- `docs/architecture/2026-06-03-LLM-Agent服务编排选型分析.md`
- `prototypes/mvp-mobile-agent/design-brief.md`
- `docs/AI协同开发执行标准.md`
- `agents.md`

## Story 定义

**目标：** 移动端展示待清洗、疑似重复、可恢复 Watch、确认无效等建议。

**Files:**

- Create: `apps/mobile/src/pages/lead-cleanup/index.vue` 或对应页面
- Create: `apps/mobile/src/services/leadCleanup*.js`
- Test: `apps/mobile` 相关测试

**Codex 提示词：**

```text
请执行 P3-E7-S2：移动端清洗建议队列页面。

要求：
1. 使用 superpowers:test-driven-development。
2. 严格依据第三阶段方案和本 Story 验收标准实现。
3. 保持 raw/staging/core/audit 分层，不让 AI 直接污染 core 数据。
4. 所有关键动作必须保留来源证据、操作人、时间和审计记录。
5. 不自动社交私信、不自动加好友、不自动发送触达消息。
6. 运行本 Story 对应测试，并按需执行相关联调验证。
7. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p3-e7-s2-执行结果.md。
8. 不要执行下一个 Story。
```

**验收标准：**

- 列表可查看 suggestion_type、原因、证据、目标线索。
- 支持 approve/reject/execute 入口。
- 高风险动作需要权限提示。
- 不提供自动删除入口。

**非目标：**

- 不实现 Agent 定时任务。

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
执行方式：`superpowers:executing-plans` + `superpowers:test-driven-development`

### 实现内容

- 新增 `apps/mobile/src/services/leadCleanup.js`，封装清洗建议 mapper、查询、approve/reject/execute payload 和 API 调用。
- 新增 `apps/mobile/src/pages/lead-cleanup/index.vue`，实现移动端清洗建议队列页面。
- 新增 `apps/mobile/src/styles/leadCleanup.css`，实现移动端清洗建议页面样式和宽度约束。
- 更新 `apps/mobile/src/pages.json` 与 `apps/mobile/pages.json`，注册清洗建议页面。
- 新增 `apps/mobile/tests/leadCleanup.test.mjs` 和 `apps/mobile/tests/leadCleanupPage.test.mjs`。

### 验收结果

- 列表可查看 `suggestion_type`、原因、证据、目标线索：已展示建议类型、原因、证据说明、证据链接、来源线索和目标线索。
- 支持 approve/reject/execute 入口：已接入 `PATCH /lead-cleanup/suggestions/{id}/approve`、`PATCH /lead-cleanup/suggestions/{id}/reject` 和 `POST /lead-cleanup/suggestions/{id}/execute`。
- 高风险动作需要权限提示：`restore_from_watch`、重复和归并类建议展示高风险权限提示；移动端不自动提权，后端继续执行权限阻断。
- 不提供自动删除入口：页面和服务未接入删除、移除、销毁类接口。
- 非目标“Agent 定时任务”：未实现，符合 Story 边界。

### 测试记录

- 红灯验证：`npm --prefix apps/mobile test`，失败原因为 `Cannot find module .../leadCleanup.js`、清洗建议页面未注册和页面文件缺失，符合测试先行预期。
- 绿灯验证：`npm --prefix apps/mobile test`，结果 `94 passed`。
- H5 构建：`npm --prefix apps/mobile run build:h5`，结果 `DONE Build complete.`。
- 后端清洗契约验证：`cd apps/api && python -m pytest tests -q -k "cleanup"`，结果 `34 passed, 456 deselected`。
- 风控扫描：页面和服务未命中 `delete/remove/destroy/自动删除/直接删除/批量删除/自动私信/自动加好友/批量触达/sendMessage/addFriend/前端自动提权`。

### 两轮独立评审

第一轮评审：

- 结论：通过，修正后无新增阻塞问题。
- 发现项：页面原先根据建议类型自动把角色设置为 `admin` 或 `compliance`，存在前端伪造提权风险。
- 修正结果：改为 `currentActorRole` 默认 `ops`，高风险建议仅展示权限提示，是否可通过/执行由后端权限守卫决定；新增测试确保不按建议类型自动提权。

第二轮评审：

- 结论：通过，无新增实质阻塞问题。
- 发现项：页面按钮可见文案为英文 `approve/reject/execute`，不符合当前项目中文界面风格。
- 修正结果：按钮显示改为“通过 / 拒绝 / 执行”，保留方法名和 API 契约不变。
