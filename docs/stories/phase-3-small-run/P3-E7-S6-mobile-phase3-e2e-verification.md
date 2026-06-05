# Story P3-E7-S6：移动端第三阶段前后端联调验收

状态：实现完成
Sprint：Sprint 7
优先级：P1
Epic：P3-E7

## 用户故事

作为第三阶段小范围运行的研发执行者，我希望完成“移动端第三阶段前后端联调验收”，以便系统可以按 BMAD 已冻结方案推进线索完善、客户晋级、客户承接、清洗治理和 LangGraph 局部试点闭环。

## 上下文来源

- `docs/brainstorm/brainstorming-session-2026-06-04-第三阶段小范围运行-客户管理工作台.md`
- `docs/product/2026-06-04-海外车辆采购AI获客系统-第三阶段小范围运行方案与产品技术设计.md`
- `docs/architecture/2026-06-03-LLM-Agent服务编排选型分析.md`
- `prototypes/mvp-mobile-agent/design-brief.md`
- `docs/AI协同开发执行标准.md`
- `agents.md`

## Story 定义

**目标：** 验证线索完善、晋级客户、客户工作台、清洗建议和跟进记录在移动端可用。

**Files:**

- Test/Docs: `_bmad-output/implementation-artifacts/codex-p3-e7-s6-执行结果.md`
- 可能修改移动端服务或页面缺陷

**Codex 提示词：**

```text
请执行 P3-E7-S6：移动端第三阶段前后端联调验收。

要求：
1. 使用 superpowers:test-driven-development。
2. 严格依据第三阶段方案和本 Story 验收标准实现。
3. 保持 raw/staging/core/audit 分层，不让 AI 直接污染 core 数据。
4. 所有关键动作必须保留来源证据、操作人、时间和审计记录。
5. 不自动社交私信、不自动加好友、不自动发送触达消息。
6. 运行本 Story 对应测试，并按需执行相关联调验证。
7. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p3-e7-s6-执行结果.md。
8. 不要执行下一个 Story。
```

**验收标准：**

- 真实 API 下线索详情完善区可运行。
- 晋级客户后客户工作台可见。
- 客户详情和跟进记录可读写。
- 清洗建议可查询和人工确认。
- H5 构建通过。

**非目标：**

- 不做管理后台。

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

- 新增 `apps/mobile/src/services/phase3E2E.js`，提供第三阶段移动端前后端联调验收契约。
- 新增 `apps/mobile/tests/phase3E2E.test.mjs`，覆盖页面注册、真实 API 调用顺序、线索完善、客户晋级、客户工作台、客户详情、跟进记录、清洗建议和安全边界摘要。
- 修正 `apps/mobile/src/services/leadDetail.js` 中 `buildPromoteStagingPayload`，补齐 `accepted_fields_json` 字段级审计来源，保持人工确认晋级契约。
- 修正 `apps/mobile/src/pages/leads/detail.vue`，移动端线索晋级入口统一调用第三阶段 `POST /staging-leads/{id}/promote-to-customer`。
- E2E 验收服务在人工补录缺少真实字段、字段值或证据说明时直接失败并停止后续写操作。

### 验收结果

- 真实 API 下线索详情完善区可运行：通过，E2E 契约覆盖 `POST /staging-leads/{id}/manual-enrichment` 和 `GET /staging-leads/{id}/enrichment-results`。
- 晋级客户后客户工作台可见：通过，E2E 契约覆盖 `POST /staging-leads/{id}/promote-to-customer` 和 `GET /customers?limit=20`。
- 客户详情和跟进记录可读写：通过，E2E 契约覆盖 `GET /customers/{id}`、`GET /customers/{id}/followups`、`POST /customers/{id}/followups`。
- 清洗建议可查询和人工确认：通过，E2E 契约覆盖 `GET /lead-cleanup/suggestions?review_status=pending&limit=20` 和 `PATCH /lead-cleanup/suggestions/{id}/approve`。
- H5 构建通过：通过。
- 不做管理后台：遵守，本 Story 未修改管理后台。

### 验证命令

```bash
source ~/.zshrc >/dev/null 2>&1 || true
nvm use v22.22.0 >/dev/null
cd apps/mobile
node --test tests/leadDetail.test.mjs tests/customerDetailPage.test.mjs tests/phase3E2E.test.mjs
```

结果：16 passed。

```bash
source ~/.zshrc >/dev/null 2>&1 || true
nvm use v22.22.0 >/dev/null
cd apps/mobile
npm test
```

结果：123 passed。

```bash
source ~/.zshrc >/dev/null 2>&1 || true
nvm use v22.22.0 >/dev/null
cd apps/mobile
npm run build:h5
```

结果：`DONE Build complete.`

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m pytest tests/test_lead_enrichment_query_api.py tests/test_manual_enrichment_api.py tests/test_promote_staging_lead_to_customer_phase3.py tests/test_customer_promotion_audit_dnc.py tests/test_customers_workbench_list_api.py tests/test_customer_detail_aggregate_api.py tests/test_customer_followups_api.py tests/test_lead_cleanup_query_api.py tests/test_lead_cleanup_review_api.py -q
```

结果：40 passed。

### 两轮独立评审

第一轮评审：API 链路、审计字段和安全边界。

结论：通过，修正后无新增阻塞问题。

发现项：

- 第三阶段移动端缺少统一 E2E 联调契约，无法一次性证明线索完善、客户晋级、客户工作台、详情、跟进和清洗建议链路。
- `buildPromoteStagingPayload` 缺少既有测试要求的 `accepted_fields_json`，不能证明人工晋级时记录字段来源审计。
- E2E 验收服务在人工补录字段缺失时仍可能继续执行后续晋级和查询步骤。

修正结果：

- 新增 `phase3E2E.js` 和 `phase3E2E.test.mjs`，固化第三阶段移动端前后端联调契约。
- 修正 `buildPromoteStagingPayload`，恢复 `accepted_fields_json` 字段级审计来源。
- 修正线索详情页晋级端点，避免移动端仍走旧 `/promote` 路径。
- 增加人工补录真实字段校验，并在前置步骤失败时短路返回，不继续执行后续写操作。

第二轮评审：页面注册、seed/mock 隔离和验收文档完整性。

结论：通过，无新增实质阻塞问题。

发现项：

- 需要确认线索详情完善区、清洗建议、客户工作台、客户详情和客户跟进记录均注册到两份 uni-app 页面配置。
- 需要确认本 Story 没有引入自动发送、自动私信、自动加好友和管理后台改动。
- 需要确认 E2E 摘要能输出中文阻断项，便于后续真实环境联调复盘。

修正结果：

- 测试覆盖 `apps/mobile/src/pages.json` 和 `apps/mobile/pages.json` 的页面注册。
- 源码扫描确认本 Story 未新增自动触达动作；`phase3E2E.js` 仅做人工补录、人工晋级、人工跟进记录和人工确认清洗建议。
- `summarizePhase3MobileE2E` 输出中文通过或阻断摘要，并覆盖失败原因。

### 结果文档

- `_bmad-output/implementation-artifacts/codex-p3-e7-s6-执行结果.md`
