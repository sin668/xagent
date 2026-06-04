# P2-E3-S3 执行结果：实现 Source Discovery Agent 核心运行服务

执行日期：2026-06-02  
Story 文件：`docs/stories/phase-2-small-run/P2-E3-S3-source-discovery-agent-service.md`  
状态：Done

## 1. 执行范围

本次只执行 P2-E3-S3，不执行下一个 Story。

已完成：

- 创建 `apps/api/app/services/source_discovery_agent.py`。
- 创建 `apps/api/tests/test_source_discovery_agent.py`。
- 实现 Source Discovery Agent 核心服务。
- 串联 prompt template、LLMClient、schema 校验、来源候选 upsert 和 `agent_task_runs` 审计。
- 覆盖成功、schema 校验失败、LLM 技术错误三类路径。

未执行：

- 未实现 Source Discovery 运行 API。
- 未实现定时任务。
- 未实现真实联网搜索。
- 未实现客户线索抽取。
- 未实现客户触达、私信、加好友或短信。
- 未实现移动端页面。
- 未执行 P2-E3-S4 或其他后续 Story。

## 2. 修改文件

- `apps/api/app/services/source_discovery_agent.py`
- `apps/api/tests/test_source_discovery_agent.py`
- `docs/stories/phase-2-small-run/P2-E3-S3-source-discovery-agent-service.md`
- `_bmad-output/implementation-artifacts/codex-p2-e3-s3-执行结果.md`

## 3. TDD 记录

RED：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_source_discovery_agent.py -q
```

结果：

```text
F..  # 1 failed, 2 passed
AssertionError: assert 'автосалон' in llm_client.calls[0]["user_prompt"]
```

失败原因：Source Discovery Agent 服务已能调用 mock LLM，但 user prompt 未稳定携带本次运行关键词，无法证明 LLM 调用包含 Story 要求的关键词输入。

GREEN：

- 在 `_render_user_prompt` 中保留 prompt template 的 `.format(...)` 渲染能力。
- 追加“本次运行变量”块，明确写入国家、城市、渠道策略、关键词和候选来源上限。
- 保持修复范围限定在 Source Discovery Agent 服务，不修改默认 prompt seed，不引入 Story 外功能。

## 4. 验证命令与结果

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

## 5. 验收结果

- Agent 服务可生成候选来源。
- 成功路径会写入 `lead_source_candidates`。
- 任务状态可从运行中进入 `succeeded`。
- LLM 技术错误会进入 `failed`。
- schema 校验失败会进入 `manual_review_required`，不 fallback，不写候选来源。
- `agent_task_runs` 保留 prompt 版本、模型、token usage、latency 和输出摘要。
- LLM user prompt 包含本次运行关键词和候选来源上限。

## 6. 风控结果

- 未调用真实联网搜索。
- 未抽取客户线索。
- 未触达客户。
- 未自动社交私信。
- 未自动加好友。
- 未登录后批量采集。
- 未反爬规避。
- 未抓取非公开数据。
- High/Forbidden 风险边界未被放宽。

## 7. 双轮评审记录

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
- High/Forbidden 具体风险默认状态仍由 P2-E3-S2 的来源候选 upsert 服务控制，本 Story 未放宽风险规则。
- 目标测试 3 条通过，相关回归测试 46 条通过。
- Python 编译通过。
- 并行运行同前缀数据库测试会产生清理冲突；当前完成验证已采用顺序执行。

修正结果：

- 第二轮未发现新增实质阻塞问题，无需追加业务代码修正。
