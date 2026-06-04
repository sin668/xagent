# Story P2-E3-S3：实现 Source Discovery Agent 核心运行服务

状态：Done  
Sprint：Sprint 2  
优先级：P0  
Epic：P2-E3

## 用户故事

作为第二阶段小范围运行的研发执行者，我希望完成“实现 Source Discovery Agent 核心运行服务”，以便系统可以按 BMAD 已冻结方案推进真实 LLM、来源发现、审核、抽取、审计和联调闭环。

## 上下文来源

- `docs/product/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行方案与产品技术设计.md`
- `_bmad-output/brainstorming/brainstorming-session-2026-06-02-第二阶段小范围运行-LLM来源发现Agent.md`
- `docs/superpowers/plans/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行Codex推进计划.md`
- `docs/AI协同开发执行标准.md`
- `AGENTS.md`

## Story 定义

**目标：** 串联 prompt template、LLMClient、schema 校验、来源候选 upsert 和任务审计。

**Files:**

- Create: `apps/api/app/services/source_discovery_agent.py`
- Test: `apps/api/tests/test_source_discovery_agent.py`

**Codex 提示词：**

```text
请执行 P2-E3-S3：实现 Source Discovery Agent 核心运行服务。

要求：
1. 使用 superpowers:test-driven-development。
2. 输入包括国家、城市、渠道策略、关键词、运行上限。
3. 创建 agent_task_runs，状态从 pending 到 running，再到 succeeded/failed/manual_review_required。
4. 读取 active + default 的 SOURCE_DISCOVERY prompt template。
5. 调用 LLMClient。
6. schema 校验通过后调用来源候选 upsert。
7. schema 校验失败不 fallback，任务进入 manual_review_required。
8. 不抽取客户、不触达、不生成私信。
9. 运行 pytest apps/api/tests/test_source_discovery_agent.py。
10. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p2-e3-s3-执行结果.md。
不要执行下一个 Story。
```

**验收标准：**

- Agent 服务可生成候选来源。
- 任务状态和 LLM 输出可审计。

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

执行日期：2026-06-02

已完成：

- 新增 `apps/api/app/services/source_discovery_agent.py`。
- 新增 `apps/api/tests/test_source_discovery_agent.py`。
- 实现 `SourceDiscoveryAgentRequest`，输入包含：
  - 国家
  - 城市
  - 渠道策略
  - 关键词
  - 运行上限
  - 触发来源
- 实现 `SourceDiscoveryAgentService.run`：
  - 创建 `agent_task_runs` 运行记录。
  - 读取 `active + default` 的 `SOURCE_DISCOVERY` prompt template。
  - 渲染 user prompt，并追加本次运行变量，避免历史默认模板缺少 `{keywords}` 或 `{max_candidates}` 时丢失运行输入。
  - 调用 `LLMClient.generate_json`。
  - LLM 技术错误时将任务标记为 `failed`。
  - schema 校验失败时将任务标记为 `manual_review_required`，不 fallback，不写候选来源。
  - schema 校验通过后调用 `LeadSourceCandidateService.upsert_from_source_discovery_output`。
  - 成功时将任务标记为 `succeeded`。
- 写入并保留审计字段：
  - `prompt_template_id`
  - `prompt_version`
  - `llm_provider`
  - `llm_model`
  - `token_usage_json`
  - `latency_ms`
  - `output_summary_json`
  - `error_message`
- 测试覆盖成功、schema 失败、LLM 技术错误三类路径。

未执行：

- 未实现 Source Discovery 运行 API。
- 未实现定时任务。
- 未实现真实联网搜索。
- 未实现客户线索抽取。
- 未实现客户触达、私信、加好友或短信。
- 未实现移动端页面。
- 未执行 P2-E3-S4 或其他后续 Story。

## TDD 记录

RED：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_source_discovery_agent.py -q
```

结果：

```text
F..  # 1 failed, 2 passed
AssertionError: assert 'автосалон' in llm_client.calls[0]["user_prompt"]
```

失败原因符合预期：Source Discovery Agent 服务已初步创建，但 prompt 渲染未稳定携带本次运行关键词，无法证明 LLM 调用包含 Story 要求的关键词输入。

GREEN：

- 在 `_render_user_prompt` 中保留模板 `.format(...)` 渲染。
- 额外追加“本次运行变量”块，明确包含国家、城市、渠道策略、关键词和候选来源上限。
- 保持修复范围限定在 prompt 渲染，不修改默认 prompt seed，不扩展 Story 外功能。

## 验证结果

目标测试：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_source_discovery_agent.py -q
```

结果：

```text
3 passed in 7.43s
```

相关回归：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_source_discovery_agent.py apps/api/tests/test_lead_source_candidate_upsert.py apps/api/tests/test_source_discovery_schema.py apps/api/tests/test_llm_prompt_templates.py apps/api/tests/test_llm_prompt_templates_api.py apps/api/tests/test_llm_client.py apps/api/tests/test_llm_fallback.py apps/api/tests/test_agent_task_run_model.py -q
```

结果：

```text
46 passed in 18.43s
```

编译验证：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/source_discovery_agent.py apps/api/tests/test_source_discovery_agent.py
```

结果：通过，退出码 0。

完成前补充验证说明：

- 曾将目标测试和相关回归测试并行执行，因两组测试使用相同 `p2e3s3` 清理前缀，出现测试进程相互删除 `agent_task_runs` 的 `StaleDataError`。
- 该问题属于测试并发隔离问题，不属于业务代码失败。
- 已按顺序重新执行目标测试和相关回归，结果分别为 `3 passed` 和 `46 passed`。

## 两轮独立评审记录

### 第一轮评审：Story 范围、状态流转与审计链路

结论：通过。

发现项：

- Agent 服务可从 `active + default SOURCE_DISCOVERY` prompt template 启动运行。
- `agent_task_runs` 会记录输入、prompt template、prompt 版本、LLM provider/model、token usage、latency 和输出摘要。
- 成功路径会调用来源候选 upsert，并将任务标记为 `succeeded`。
- schema 校验失败路径会进入 `manual_review_required`，不 fallback，不写入候选来源。
- LLM 技术错误路径会进入 `failed`，不写入候选来源。
- 当前 Story 未越界实现运行 API、调度器、真实搜索、客户抽取或触达。

修正结果：

- 已修正 prompt 渲染缺失运行关键词的问题，追加“本次运行变量”块，确保关键词和运行上限进入 LLM user prompt。

### 第二轮评审：合规边界、失败处理与回归风险

结论：通过。

发现项：

- 当前实现只处理来源发现候选，不抽取客户，不触达客户，不生成私信，不自动加好友。
- schema 校验失败不会被静默吞掉或自动降级写入，符合“AI 输出必须可审计、失败进入人工复核”的边界。
- High/Forbidden 具体风险默认状态仍由上一 Story 的来源候选 upsert 服务控制，本 Story 未放宽风险规则。
- 目标测试 3 条通过，相关回归测试 46 条通过。
- Python 编译通过。
- 并行运行同前缀数据库测试会产生清理冲突；当前完成验证已采用顺序执行。

修正结果：

- 第二轮未发现新增实质阻塞问题，无需追加业务代码修正。
