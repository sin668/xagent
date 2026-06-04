# 第二阶段小范围运行最终验收归档

归档日期：2026-06-03  
范围：`docs/stories/phase-2-small-run/` 第二阶段 29 个 Story  
执行原则：未执行锁操作，未执行 git 操作；每次只执行一个 Story；所有说明使用中文。

## 1. 已完成 Story

| Epic | Story | 状态 | 结果摘要 |
|---|---|---|---|
| P2-E1 | P2-E1-S1 | Done | 创建 `llm_prompt_templates` 数据模型、schema 和 migration。 |
| P2-E1 | P2-E1-S2 | Done | 创建 `agent_task_runs` 状态机和任务审计基础。 |
| P2-E1 | P2-E1-S3 | Done | 创建 `lead_source_candidates` 来源候选模型和默认风险准入。 |
| P2-E1 | P2-E1-S4 | Done | 完成第二阶段数据层契约和 migration 验证。 |
| P2-E2 | P2-E2-S1 | Done | 扩展 LLM 配置和 `/llm-health`。 |
| P2-E2 | P2-E2-S2 | Done | 实现统一 `LLMClient` 和 mock 测试。 |
| P2-E2 | P2-E2-S3 | Done | 实现 fallback 规则，技术失败可重试，schema/合规失败不 fallback。 |
| P2-E2 | P2-E2-S4 | Done | SOURCE_DISCOVERY prompt/schema 入库并设默认版本。 |
| P2-E2 | P2-E2-S5 | Done | 实现 prompt template 查询 API。 |
| P2-E3 | P2-E3-S1 | Done | 实现 SOURCE_DISCOVERY 输出 schema 校验。 |
| P2-E3 | P2-E3-S2 | Done | 实现来源候选 upsert、去重和默认审核状态。 |
| P2-E3 | P2-E3-S3 | Done | 实现 SOURCE_DISCOVERY Agent 核心运行服务。 |
| P2-E3 | P2-E3-S4 | Done | 实现 SOURCE_DISCOVERY 手动启动 API 和任务审计。 |
| P2-E3 | P2-E3-S5 | Done | 实现来源候选列表、详情和筛选 API。 |
| P2-E3 | P2-E3-S6 | Done | 实现来源审核动作 API 与风险闸门。 |
| P2-E4 | P2-E4-S1 | Done | 实现移动端来源候选 service 和 API adapter。 |
| P2-E4 | P2-E4-S2 | Done | 实现移动端来源候选队列页面。 |
| P2-E4 | P2-E4-S3 | Done | 实现移动端来源详情与审核动作页面。 |
| P2-E4 | P2-E4-S4 | Done | 实现移动端 Agent 手动调用页面和任务状态展示。 |
| P2-E4 | P2-E4-S5 | Done | 完成移动端前后端联调与 H5 可用性验证。 |
| P2-E5 | P2-E5-S1 | Done | 实现 APScheduler 开关、任务注册和 Redis lock。 |
| P2-E5 | P2-E5-S2 | Done | 实现失败重试、超时恢复和任务状态机收敛。 |
| P2-E5 | P2-E5-S3 | Done | 实现 LEAD_EXTRACTION 从 approved 来源消费。 |
| P2-E5 | P2-E5-S4 | Done | 实现抽取结果写入 staging、audit，并更新来源抽取状态。 |
| P2-E6 | P2-E6-S1 | Done | 实现第二阶段 dashboard API。 |
| P2-E6 | P2-E6-S2 | Done | 实现管理后台第二阶段运行看板。 |
| P2-E6 | P2-E6-S3 | Done | 实现管理后台 LLM/Prompt 治理页面。 |
| P2-E6 | P2-E6-S4 | Done | 完成真实 PostgreSQL + Redis + LLM + 移动端 H5 端到端验收。 |
| P2-E6 | P2-E6-S5 | Done | 完成部署运行手册和最终验收归档。 |

## 2. 测试结果

已记录的关键验证结果：

- P2-E6-S2 管理后台看板：
  - `npm --prefix apps/admin test`：`21 passed`
  - `npm --prefix apps/admin run check:syntax`：通过
  - `npm --prefix apps/admin run build`：通过
  - `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_phase2_dashboard_api.py`：`2 passed`
- P2-E6-S3 LLM/Prompt 治理：
  - `npm --prefix apps/admin test`：`24 passed`
  - `npm --prefix apps/admin run check:syntax`：通过
  - `npm --prefix apps/admin run build`：通过
  - `/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_llm_health_api.py apps/api/tests/test_llm_prompt_templates_api.py`：`7 passed`
- P2-E6-S4 端到端验收：
  - Alembic current：`20260602_0022 (head)`
  - PostgreSQL：`postgres_ok=1`，`public_tables=30`
  - Redis：`redis_ping=True`
  - API `/health`：`{"status":"ok","service":"vehicle-leads-api"}`
  - 移动端 H5 `/pages/sources/index`：HTTP `200 OK`
  - `npm --prefix apps/mobile test`：`69 passed`
  - `npm --prefix apps/mobile run build:h5`：通过
  - `scripts/phase2_e2e_verification.py` 语法检查：通过

## 3. 联调结果

真实联调链路：

1. API 启动并访问 `/health` 成功。
2. `/llm-health` 可返回 Provider、模型、base URL 和 API key 配置状态。
3. SOURCE_DISCOVERY 通过真实 API 创建任务并写入 `agent_task_runs`。
4. 移动端调用同源来源审核 API，可把 Medium 来源审核为 `approved` 并设为可抽取。
5. LEAD_EXTRACTION 从审核通过的来源候选中选择来源，创建任务。
6. 受控 LLM 输出验证后续写库链路，产生 `staging_leads` 和 `ai_audit_logs`。
7. High 未审核来源被阻断，阻断原因为 `high_risk_requires_manual_approval`。
8. Forbidden 来源被阻断，阻断原因为 `forbidden_risk_blocked`。
9. 管理后台第二阶段看板和 LLM/Prompt 治理页面调用真实 API，不使用 seed 伪装真实运行状态。

## 4. 未完成项

- `LLM_API_KEY` 当前未配置，`/llm-health` 显示 `api_key_configured=false`、`configuration_complete=false`。
- 因 API key 未配置，真实外部 LLM 调用未完成成功验收；SOURCE_DISCOVERY 真实任务可启动和审计，但状态为 `failed`。
- `AgentSchedulerService` 已实现定时注册和 Redis lock，但默认 handler 仍是 placeholder；启用自动调度前必须接入真实 handler。
- 未进行生产服务器部署，只完成本机和真实数据库小范围运行验收。

## 5. 残留风险

| 风险 | 等级 | 当前处理 |
|---|---|---|
| LLM API key 未配置，真实外部 LLM 不可用 | High | 部署手册要求 `/llm-health.configuration_complete=true` 后才可宣称可用。 |
| 定时调度 handler 未绑定真实任务 | High | `AGENT_SCHEDULER_ENABLED` 默认关闭；启用前必须复核 handler。 |
| High 风险来源误入自动化 | High | 服务层要求 High 未人工批准阻断；端到端脚本已验证。 |
| Forbidden 来源误入自动化 | High | 服务层直接阻断；端到端脚本已验证。 |
| LLM 编造联系方式或证据 | Medium | AI 输出必须保留证据和审计；抽取服务执行来源证据校验。 |
| 运营绕过审核直接触达 | Medium | 文档和系统边界要求只允许人工触达，Invalid/Watch 和勿扰不得进入触达队列。 |
| Provider 限流或网络失败 | Medium | retry policy 仅允许技术失败重试，schema/合规失败不可 fallback。 |

## 6. 最终结论

第二阶段小范围运行的工程闭环已完成到可试运行状态：

- 数据底座、LLM 配置健康检查、prompt/schema 入库、来源发现 Agent、来源候选审核、来源驱动抽取、审计、移动端、管理后台和端到端验收均已落盘。
- 当前不能宣称真实外部 LLM 已可用；必须先配置 `LLM_API_KEY` 并重新通过 `/llm-health` 与 SOURCE_DISCOVERY 成功调用验收。
- 自动定时运行必须在真实 handler 接入并完成联调后再开启。

## 7. 两轮评审

### 第一轮独立多维度评审

结论：通过，无新增实质阻塞问题。

评审维度：

- 需求覆盖：归档列出所有 29 个第二阶段 Story、测试结果、联调结果、未完成项和残留风险。
- 真实性：明确区分已通过受控 LLM 的写库链路和未通过真实外部 LLM 的 Provider 调用。
- 合规边界：保留不自动私信、不自动加好友、不登录后批量采集、不反爬规避等红线。
- 运维可用性：部署手册已包含环境变量、migration、Redis、LLM Provider、APScheduler、移动端、后台、故障和暂停恢复流程。

发现项与修正结果：

- 发现：需要突出 `AGENT_SCHEDULER_ENABLED` 默认关闭和 handler placeholder 风险。
- 修正：已在部署手册、归档未完成项和残留风险中明确说明。

### 第二轮独立多维度评审

结论：通过，无新增实质阻塞问题。

复核维度：

- BMAD 流程：仅执行当前 `P2-E6-S5`，未进入新 Story。
- 文档完整性：部署手册和归档均已创建，Story 状态应更新为 Done。
- 验收证据：引用 E6-S2、E6-S3、E6-S4 已记录测试结果，不额外虚构未执行的真实 LLM 成功结果。
- 风险收口：LLM API key、自动调度、High/Forbidden、勿扰和 C 级复核均有明确处理边界。

发现项与修正结果：

- 发现：无新增实质问题。
- 修正：无需修正。
