# Story P4-E3-S3：兼容现有 runtime 方法：深挖和清洗

状态：已实现  
Sprint：Sprint 3  
优先级：P0  
Epic：P4-E3

## 用户故事

作为现有 `apps/api` Agent 编排代码的维护者，我希望 `HttpAgentRuntime` 暴露与现有深挖和清洗 runtime 相容的方法，以便局部切换到 HTTP active_run 时不需要大改上层业务编排。

## 上下文来源

- `docs/product/2026-06-04-海外车辆采购AI获客系统-第四阶段小范围运行方案与产品技术设计.md`

## Story 定义

**目标：** 为 `HttpAgentRuntime` 增加 `run_deep_enrichment`、`run_lead_cleanup` 等与现有调用方兼容的方法签名和返回结构。

**建议文件：**

- Modify: `apps/api/app/agents/http_runtime.py`
- Modify: `apps/api/app/agents/`
- Test: `apps/api/tests/agents/test_http_runtime_compatibility.py`

**验收标准：**

- `run_deep_enrichment` 可将现有输入转换为 `apps/agents` Deep Enrichment run 请求。
- `run_lead_cleanup` 可将现有输入转换为 `apps/agents` Lead Cleanup run 请求。
- 返回结构能被现有上层 service 消费。
- 兼容层不改变现有本地 runtime 的行为。

**非目标：**

- 不接入生产入口。
- 不实现 LangGraph Agent API。
- 不写业务 core 表。

## Codex 提示词

```text
请执行 P4-E3-S3：兼容现有 runtime 方法：run_deep_enrichment 和 run_lead_cleanup。
要求使用 TDD；只新增 HTTP runtime 兼容层；不得修改现有本地 runtime 语义；完成后执行两轮独立评审。
```

## 通用执行要求

- 每次只执行当前 Story，不要执行下一个 Story。
- 不做锁操作，不做 git 操作。
- 使用 `superpowers:test-driven-development`。
- 完成前使用 `superpowers:verification-before-completion`。
- 所有过程、结果、注解和文档使用中文。

## 通用风控边界

- `apps/api` 中现有 LLM Agent 保持不变。
- `apps/agents` 独立服务运行，通过 HTTP API 交互。
- 不自动触达、不自动晋级、不自动归并、不自动恢复 Invalid。

## 执行记录

执行日期：2026-06-05  
执行方式：按 `docs/superpowers/plans/2026-06-05-海外车辆采购AI获客系统-第四阶段小范围运行LangGraph-Agent迁移推进计划.md` 执行当前 Story。

### Git / Worktree 记录

- 延续当前环境事实：沙箱禁止写 `.git/FETCH_HEAD` 和 `.git/refs/heads/*.lock`。
- 无法在本环境完成 `git fetch`、创建分支和 worktree。
- 按当前目标的 sandbox fallback，在当前工作区继续执行本 Story。
- 未执行 git 提交。

### TDD 记录

红灯：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/agents/test_http_runtime_compatibility.py -q
```

结果：`3 failed`，原因是 `HttpAgentRuntime` 尚无 `run_deep_enrichment` 和 `run_lead_cleanup`，符合当前 Story 需要新增兼容方法的预期。

绿灯：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/agents/test_http_runtime_compatibility.py -q
```

结果：`3 passed in 0.06s`。

第二轮评审补充测试后发现：

- phase4 response envelope 若状态为 `failed` 或 `blocked`，兼容层不能把其中的 `output` 当作成功 phase3 输出返回给上层 service。

修正：

- 新增 `test_compatibility_methods_reject_non_succeeded_phase4_run`。
- `_phase3_output_from_response` 增加 `response.status == "succeeded"` 校验。

修正后绿灯：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/agents/test_http_runtime_compatibility.py -q
```

结果：`4 passed in 0.07s`。

### 实现摘要

- 在 `apps/api/app/agents/http_runtime.py` 中新增 `HttpAgentRuntime.run_deep_enrichment`。
- `run_deep_enrichment` 兼容现有上层 service 调用签名：`agent_run_id`、`staging_lead_id`、`lead_snapshot`、`missing_fields`。
- `run_deep_enrichment` 将现有输入转换为 `POST /agent-runs/deep-enrichment` 的 phase4 request envelope。
- 在 `apps/api/app/agents/http_runtime.py` 中新增 `HttpAgentRuntime.run_lead_cleanup`。
- `run_lead_cleanup` 兼容现有上层 service 调用签名：`cleanup_run_id`、`leads`。
- `run_lead_cleanup` 将现有输入转换为 `POST /agent-runs/lead-cleanup` 的 phase4 request envelope。
- 兼容方法从 phase4 response envelope 中提取 `output`，返回现有上层 service 可消费的 phase3 output dict。
- 兼容方法校验 phase4 run status 必须为 `succeeded`。
- 兼容方法校验 phase3 output `schema_version` 必须匹配现有 service 期望。
- 未接入生产入口。
- 未实现 LangGraph Agent API。
- 未写业务 core 表。
- 未改变现有本地 runtime 语义。

### 验证命令

当前 Story 测试：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/agents/test_http_runtime_compatibility.py -q
```

结果：`4 passed in 0.07s`。

`apps/api` 聚焦回归：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest tests/agents/test_http_runtime_compatibility.py tests/agents/test_http_agent_runtime.py tests/test_agents_settings.py tests/test_llm_settings.py tests/test_llm_client.py tests/test_phase3_agent_runtime_integration.py -q
```

结果：`25 passed in 0.42s`。

`apps/api` 导入与兼容方法检查：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/python - <<'PY'
from app.main import app
from app.agents import HttpAgentRuntime
print(app.title)
print(len(app.routes) > 0)
print(hasattr(HttpAgentRuntime, 'run_deep_enrichment'))
print(hasattr(HttpAgentRuntime, 'run_lead_cleanup'))
PY
```

执行目录：`apps/api`  
结果：

```text
Overseas Vehicle Leads AI API
True
True
True
```

`apps/agents` 回归：

```bash
PYTHONPATH=$PWD /opt/miniconda3/envs/booking-room/bin/pytest -q
```

执行目录：`apps/agents`  
结果：`49 passed in 0.53s`。

## 两轮独立评审记录

### 第一轮评审：兼容签名、输入转换和现有本地 runtime

结论：

- 通过。`run_deep_enrichment` 可将现有输入转换为 `apps/agents` Deep Enrichment run 请求。
- 通过。`run_lead_cleanup` 可将现有输入转换为 `apps/agents` Lead Cleanup run 请求。
- 通过。返回结构为 phase3 output dict，可被现有上层 service 消费。
- 通过。未接入生产入口。
- 通过。未实现 LangGraph Agent API。
- 通过。未写业务 core 表。

发现项：

- 需要确认新增兼容层没有改变现有本地 runtime 的上层 service 消费语义。

修正结果：

- 已补跑 `tests/test_phase3_agent_runtime_integration.py`，结果：`3 passed in 0.42s`。
- 该测试覆盖现有 `LeadEnrichmentService.run_deep_enrichment_agent` 和 `LeadCleanupSuggestionService.run_cleanup_agent` 对本地 runtime dict 输出的消费路径。

### 第二轮评审：失败边界、回归风险和可维护性

结论：

- 通过。phase4 response envelope 缺少 output 时会抛 `HttpAgentRuntimeValidationError`。
- 通过。phase3 output `schema_version` 不匹配时会抛 `HttpAgentRuntimeValidationError`。
- 通过。phase4 run status 非 `succeeded` 时不会被当作成功 phase3 output 返回。
- 通过。`apps/api` 聚焦回归通过：`25 passed in 0.42s`。
- 通过。`apps/api` 导入与兼容方法检查通过。
- 通过。`apps/agents` 回归通过：`49 passed in 0.53s`。

发现项：

- 同步兼容方法内部使用 `asyncio.run` 调用 async `run_agent`，因此只能从现有同步 service 代码路径调用。

修正结果：

- 已在 `_run_agent_sync` 中检测运行中的 event loop；如从异步上下文调用，会抛 `HttpAgentRuntimeConfigurationError`，避免嵌套 event loop 行为不明确。
