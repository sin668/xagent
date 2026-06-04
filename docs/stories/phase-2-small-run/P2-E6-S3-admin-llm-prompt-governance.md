# Story P2-E6-S3：管理后台 LLM/Prompt 治理页面

状态：Done  
Sprint：Sprint 5  
优先级：P2  
Epic：P2-E6

## 用户故事

作为第二阶段小范围运行的研发执行者，我希望完成“管理后台 LLM/Prompt 治理页面”，以便系统可以按 BMAD 已冻结方案推进真实 LLM、来源发现、审核、抽取、审计和联调闭环。

## 上下文来源

- `docs/product/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行方案与产品技术设计.md`
- `_bmad-output/brainstorming/brainstorming-session-2026-06-02-第二阶段小范围运行-LLM来源发现Agent.md`
- `docs/superpowers/plans/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行Codex推进计划.md`
- `docs/AI协同开发执行标准.md`
- `AGENTS.md`

## Story 定义

**目标：** 对齐原型 `admin-llm.html`，展示 Provider、prompt 版本和 fallback 边界。

**Files:**

- Create: `apps/admin/src/services/llmGovernance.js`
- Modify: `apps/admin/src/App.vue`
- Test: `apps/admin/tests/llmGovernance.test.mjs`

**Codex 提示词：**

```text
请执行 P2-E6-S3：管理后台 LLM/Prompt 治理页面。

要求：
1. 使用 superpowers:test-driven-development。
2. 页面参考 prototypes/mvp-mobile-agent/pages/admin-llm.html。
3. 展示 Provider 健康状态、prompt template 列表、默认版本、schema 摘要、fallback 边界。
4. 第二阶段只读，不开放普通运营编辑 prompt。
5. 运行 npm --prefix apps/admin test 或项目已有后台测试命令。
6. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p2-e6-s3-执行结果.md。
不要执行下一个 Story。
```

**验收标准：**

- LLM 治理数据来自真实 API。
- 页面不暴露 API key。

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作。
- 不做 git 操作。
- 代码实现 Story 必须使用 `superpowers:test-driven-development`。
- 调试异常必须使用 `superpowers:systematic-debugging`。
- 完成前必须使用 `superpowers:verification-before-completion`。
- 完成后必须执行两轮独立多维度评审，并记录结论、发现项和修正结果。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- 不自动社交私信。
- 不自动加好友。
- 不登录后批量采集。
- 不反爬规避。
- 不抓取非公开数据。
- High 来源未审核不得进入自动抽取。
- Forbidden 来源不得进入自动抽取。
- Invalid 和 Watch 不进入触达队列。
- 勿扰客户不得再次进入触达队列。
- C 级线索报价、合同或实质交易前必须合规复核。
- 所有 AI 输出必须保存来源证据、prompt 版本、模型和审计记录。

## 实施结果

已完成。

### 实现内容

- 新增 `apps/admin/src/services/llmGovernance.js`：
  - 聚合真实 API：`GET /llm-health` 与 `GET /llm-prompt-templates`。
  - 支持 prompt template 只读筛选参数：`task_type`、`status`、`is_default`。
  - 将 Provider 健康状态、prompt template、schema 摘要、fallback 边界转换为后台 view model。
  - 只展示 API key 是否配置，不展示 API key、secret 或完整敏感连接配置。
- 新增 `apps/admin/tests/llmGovernance.test.mjs`：
  - 覆盖 Provider 健康状态、模型摘要、prompt 版本、默认版本、schema 摘要、fallback 边界。
  - 覆盖只读查询参数。
  - 覆盖真实 API 调用路径，确认不暴露 API key。
- 修改 `apps/admin/src/App.vue`：
  - 新增“LLM 治理”后台导航入口。
  - 新增 LLM Provider 与 Prompt Schema 治理页面。
  - 页面挂载时调用真实 `/llm-health` 与 `/llm-prompt-templates` API。
  - 明确展示第二阶段只读边界，普通运营不可创建、编辑或删除 prompt template。
- 修改 `apps/admin/src/styles/admin.css`：
  - 增加 Provider 卡片、prompt 治理布局、fallback 列表和 schema 预览样式。
- 修改 `apps/admin/package.json`：
  - 将 `src/services/llmGovernance.js` 加入 `check:syntax`。

### TDD 记录

- RED：
  - 先创建 `apps/admin/tests/llmGovernance.test.mjs`。
  - 首次运行 `npm --prefix apps/admin test` 失败，原因是 `apps/admin/src/services/llmGovernance.js` 尚不存在。
  - 失败符合预期，证明测试覆盖新增治理服务能力。
- GREEN：
  - 创建 `llmGovernance.js` 后，`npm --prefix apps/admin test` 通过。
  - 接入 `App.vue` 后完成后台测试、语法检查、生产构建和后端真实 API 回归。

### 验证结果

执行环境：

- `conda activate booking-room`
- `nvm use v22.22.0`
- Node：`v22.22.0 darwin-arm64`
- Python：`/opt/miniconda3/envs/booking-room/bin/python`，版本 `3.12.11`

验证命令与结果：

- `npm --prefix apps/admin test`
  - 结果：`24 passed`
- `npm --prefix apps/admin run check:syntax`
  - 结果：通过，包含 `src/services/llmGovernance.js`
- `npm --prefix apps/admin run build`
  - 结果：通过，Vite 构建成功
- `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_health_api.py apps/api/tests/test_llm_prompt_templates_api.py`
  - 结果：`7 passed`
  - 说明：使用真实 PostgreSQL 连接验证 prompt template 只读 API。

### 验收结论

- LLM 治理数据来自真实 API：通过。
- 页面不暴露 API key：通过。
- 展示 Provider 健康状态、prompt template 列表、默认版本、schema 摘要、fallback 边界：通过。
- 第二阶段只读，不开放普通运营编辑 prompt：通过；后端 API 仅 GET，页面无编辑入口。
- 未执行下一个 Story：通过。
- 未做锁操作：通过。
- 未做 git 操作：通过。

### 第一轮独立多维度评审

结论：通过，无新增实质阻塞问题。

评审维度：

- 需求覆盖：已覆盖 Provider、prompt 版本、默认版本、schema 摘要和 fallback 边界。
- API 真实性：页面调用 `/llm-health` 与 `/llm-prompt-templates`，未使用 seed 数据伪装治理数据。
- 敏感信息：页面只显示 API key 配置状态，不展示 API key 原文、secret 或敏感连接信息。
- 只读边界：页面无创建、编辑、删除入口；后端 prompt template API 已验证仅 GET。
- 测试证据：后台 24 个测试、构建、语法检查和后端 7 个 API 测试通过。

发现项与修正结果：

- 发现：无实质阻塞问题。
- 修正：无需修正。

### 第二轮独立多维度评审

结论：通过，无新增实质阻塞问题。

复核维度：

- Story 边界：仅完成 `P2-E6-S3`，未推进 `P2-E6-S4`。
- 产品一致性：页面结构对齐 `admin-llm.html` 的 Provider、Prompt Template、Fallback、Schema 预览核心区域。
- 技术一致性：沿用现有后台服务层 `buildXView`、`fetchX` 模式。
- 合规边界：未新增自动触达、自动加好友、登录后批量采集或反爬规避能力。
- 审计能力：prompt 版本、schema 和模型配置可见，支持后续 LLM 调用审计。

发现项与修正结果：

- 发现：无新增实质问题。
- 修正：无需修正。
