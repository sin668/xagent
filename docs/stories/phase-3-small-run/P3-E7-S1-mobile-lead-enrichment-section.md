# Story P3-E7-S1：移动端线索详情新增完善区

状态：实现完成
Sprint：Sprint 7
优先级：P1
Epic：P3-E7

## 用户故事

作为第三阶段小范围运行的研发执行者，我希望完成“移动端线索详情新增完善区”，以便系统可以按 BMAD 已冻结方案推进线索完善、客户晋级、客户承接、清洗治理和 LangGraph 局部试点闭环。

## 上下文来源

- `docs/brainstorm/brainstorming-session-2026-06-04-第三阶段小范围运行-客户管理工作台.md`
- `docs/product/2026-06-04-海外车辆采购AI获客系统-第三阶段小范围运行方案与产品技术设计.md`
- `docs/architecture/2026-06-03-LLM-Agent服务编排选型分析.md`
- `prototypes/mvp-mobile-agent/design-brief.md`
- `docs/AI协同开发执行标准.md`
- `agents.md`

## Story 定义

**目标：** 在线索详情页展示深挖按钮、补全结果、字段级采纳和建议晋级。

**Files:**

- Modify: `apps/mobile/src/pages/leads/detail.vue` 或对应页面
- Modify: `apps/mobile/src/services/leadEnrichment*.js`
- Test: `apps/mobile` 相关测试

**Codex 提示词：**

```text
请执行 P3-E7-S1：移动端线索详情新增完善区。

要求：
1. 使用 superpowers:test-driven-development。
2. 严格依据第三阶段方案和本 Story 验收标准实现。
3. 保持 raw/staging/core/audit 分层，不让 AI 直接污染 core 数据。
4. 所有关键动作必须保留来源证据、操作人、时间和审计记录。
5. 不自动社交私信、不自动加好友、不自动发送触达消息。
6. 运行本 Story 对应测试，并按需执行相关联调验证。
7. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p3-e7-s1-执行结果.md。
8. 不要执行下一个 Story。
```

**验收标准：**

- 线索详情可触发“深挖线索”。
- 展示字段候选、证据、置信度和采纳状态。
- 支持采纳/拒绝/人工补录入口。
- Watch/Invalid/勿扰/Forbidden 不显示可执行深挖按钮。

**非目标：**

- 不实现客户工作台列表。

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

- 新增 `apps/mobile/src/services/leadEnrichment.js`，封装线索完善视图模型、深挖触发、结果查询、字段采纳/拒绝、人工补录 payload 与 API 调用。
- 更新 `apps/mobile/src/services/apiClient.js`，补齐 `PATCH` 方法以支持字段级采纳和拒绝接口。
- 更新 `apps/mobile/src/pages/leads/detail.vue`，新增“线索完善区”，展示深挖按钮、字段候选、证据、置信度、采纳状态、采纳/拒绝动作和人工补录表单。
- 更新 `apps/mobile/src/styles/leadDetail.css`，补充完善区、字段候选卡片和人工补录表单样式，控制移动端宽度和按钮尺寸。
- 新增 `apps/mobile/tests/leadEnrichment.test.mjs`，覆盖完善视图模型、风险阻断、payload、服务接口调用和人工补录不提交占位数据。

### 验收结果

- 线索详情可触发“深挖线索”：已通过 `POST /staging-leads/{lead_id}/enrichment-runs` 接入。
- 展示字段候选、证据、置信度和采纳状态：已在线索完善区展示字段名、候选值、证据说明、来源链接、置信度和状态标签。
- 支持采纳/拒绝/人工补录入口：已通过 `PATCH /lead-enrichment-field-candidates/{id}/accept`、`PATCH /lead-enrichment-field-candidates/{id}/reject` 和 `POST /staging-leads/{id}/manual-enrichment` 接入。
- Watch/Invalid/勿扰/Forbidden 不显示可执行深挖按钮：已在 `canTriggerDeepEnrichment` 和页面 `v-if` 中阻断，只显示阻断原因。
- 非目标“客户工作台列表”：未实现，符合 Story 边界。

### 测试记录

- 红灯验证：`npm --prefix apps/mobile test`，失败原因为 `Cannot find module .../leadEnrichment.js`，符合测试先行预期。
- 绿灯验证：`npm --prefix apps/mobile test`，结果 `86 passed`。
- H5 构建：`npm --prefix apps/mobile run build:h5`，结果 `DONE Build complete.`。
- 后端接口契约验证：`cd apps/api && python -m pytest tests -q -k "lead_enrichment"`，结果 `26 passed, 464 deselected`。

### 两轮独立评审

第一轮评审：

- 结论：通过，修正后无新增阻塞问题。
- 发现项：后端深挖结果状态枚举包含 `succeeded`，移动端原先只把 `completed` 映射为“已完成”，真实后端数据会误显示为“待执行”。
- 修正结果：`resultStatusLabel` 已支持 `succeeded`；测试 fixture 改为后端真实枚举 `ai_deep_research`、`succeeded`、`ai_public_source`。

第二轮评审：

- 结论：通过，无新增实质阻塞问题。
- 发现项：人工补录入口不能提交占位字段，否则会污染 staging 完善区。
- 修正结果：页面改为真实人工补录表单，必须输入字段名、字段值和证据说明后才提交；新增回归测试确保不提交 `待补充` 或 `人工补录备注` 占位内容。
