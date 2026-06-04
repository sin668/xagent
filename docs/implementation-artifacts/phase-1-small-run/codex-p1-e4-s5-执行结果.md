# P1-E4-S5 执行结果

Story：`docs/stories/phase-1-small-run/P1-E4-S5-agent-failed-case-library.md`  
执行人：Codex  
执行日期：2026-05-29  
状态：已完成本地实现、迁移、TDD、定向回归、编译检查和 Story 状态回写；真实 PostgreSQL/Redis migration/联调验证受当前沙箱出网限制影响，待可出网环境复验

## 1. 执行说明

本 Story 按 `docs/AI协同开发执行标准.md`、第一阶段实施计划和 superpowers TDD/verification 规范执行。用户已明确要求不执行 Story lock 操作，因此本 Story 未执行任何锁命令。

## 2. 修改文件

- `apps/api/alembic/versions/20260529_0017_failed_cases.py`
- `apps/api/app/models/enums.py`
- `apps/api/app/models/failed_case.py`
- `apps/api/app/models/__init__.py`
- `apps/api/app/services/failed_cases.py`
- `apps/api/app/schemas/failed_cases.py`
- `apps/api/app/api/failed_cases.py`
- `apps/api/app/main.py`
- `apps/api/app/services/llm_lead_extraction.py`
- `apps/api/app/services/llm_lead_grading.py`
- `apps/api/app/services/public_page_read_agent.py`
- `apps/api/tests/test_failed_cases_library.py`
- `docs/stories/phase-1-small-run/P1-E4-S5-agent-failed-case-library.md`
- `_bmad-output/implementation-artifacts/codex-p1-e4-s5-执行结果.md`

## 3. 实现内容

### 3.1 failed_cases 数据层

新增 `failed_cases` 表，字段覆盖：

- `case_type`
- `source_url`
- `risk_level`
- `related_task_type`
- `related_object_type`
- `related_object_id`
- `failure_reason`
- `evidence_note`
- `raw_input_ref`
- `raw_output_json`
- `model_name`
- `prompt_version`
- `usable_for_rag`
- `touch_queue_allowed`
- `created_at`

新增 `FailedCaseType` 枚举：

- `fetch_failed`
- `schema_invalid`
- `missing_evidence`
- `risk_blocked`
- `duplicate`
- `llm_suspected_fabrication`

### 3.2 服务与 API

新增 `FailedCaseService`：

- `classify_failure_reason`
- `build_failed_case_payload`
- `record_failed_case`
- `list_failed_cases`

新增后台查询 API：

```text
POST /failed-cases
GET /failed-cases
```

查询支持：

- `case_type`
- `usable_for_rag`
- `limit`

### 3.3 Agent 失败路径接入

已接入：

- LLM 抽取 schema/证据/风险/反编造校验失败
- LLM 分级 schema/证据/硬规则校验失败
- 公开页面读取 failed

失败案例默认：

- `usable_for_rag=true`
- `touch_queue_allowed=false`

## 4. 验收结果

| 验收项 | 结论 | 证据 |
|---|---|---|
| 记录 failed_cases | 通过 | 新增 `failed_cases` 表、模型、服务和 API |
| 分类失败原因 | 通过 | `FailedCaseService.classify_failure_reason` |
| 覆盖 fetch_failed | 通过 | 页面读取失败接入 failed case |
| 覆盖 schema_invalid | 通过 | 默认分类和 LLM 校验失败接入 |
| 覆盖 missing_evidence | 通过 | 缺证据文本分类 |
| 覆盖 risk_blocked | 通过 | High/Forbidden 等风险阻断分类 |
| 覆盖 duplicate | 通过 | 重复原因分类 |
| 覆盖 llm_suspected_fabrication | 通过 | 联系方式不在公开文本中分类 |
| 支持后台查询 | 通过 | `GET /failed-cases` |
| schema 校验失败必须有失败记录 | 通过 | LLM extraction/grading 失败路径接入 |
| 疑似编造必须有风险事件或失败案例 | 通过 | 抽取失败路径记录 `llm_suspected_fabrication` |
| 失败案例可用于后续知识库 RAG | 通过 | `usable_for_rag=true` |
| 不自动修复 prompt | 通过 | 仅记录，不生成修复动作 |
| 失败记录不能推进触达队列 | 通过 | `touch_queue_allowed=false` |

## 5. 测试记录

### 5.1 测试先行

首次运行：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_failed_cases_library.py -q
```

结果：

```text
ImportError: cannot import name 'FailedCaseType'
```

### 5.2 实现后测试

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_failed_cases_library.py -q
```

结果：

```text
6 passed in 0.37s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/models/failed_case.py apps/api/app/services/failed_cases.py apps/api/app/schemas/failed_cases.py apps/api/app/api/failed_cases.py apps/api/app/services/llm_lead_extraction.py apps/api/app/services/llm_lead_grading.py apps/api/app/services/public_page_read_agent.py apps/api/app/main.py
```

结果：通过。

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_failed_cases_library.py apps/api/tests/test_llm_lead_extraction.py apps/api/tests/test_llm_lead_grading.py apps/api/tests/test_public_page_read_agent.py apps/api/tests/test_audit_risk_logs_foundation.py apps/api/tests/test_channel_discovery_agent.py -q
```

结果：

```text
35 passed in 0.27s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/alembic/versions/20260529_0017_failed_cases.py
```

结果：通过。

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m alembic heads
```

结果：

```text
20260529_0017 (head)
```

## 6. 两轮独立评审

### 6.1 第一轮：数据闭环和分类完整性评审

结论：通过，发现 1 个分类优先级问题并已修正。

发现项：

- “联系方式不在公开文本中”同时包含“不得写入 staging”，若风险阻断分类优先，会被误归为 `risk_blocked`，不利于识别 LLM 疑似编造。

修正结果：

- 将 `llm_suspected_fabrication` 分类优先级提前到 `risk_blocked` 前。
- 增加分类覆盖测试。

### 6.2 第二轮：安全、RAG 和触达隔离评审

结论：通过，存在真实数据库 migration/联调环境残留验证项。

发现项：

- 失败案例未来要进入知识库 RAG，但不能推动触达队列。
- LLM 抽取和分级失败路径不能只写 AI audit，应该同时进入失败案例库。
- 当前 Codex 沙箱无法连接真实 PostgreSQL/Redis，无法执行真实 migration。

修正结果：

- `build_failed_case_payload` 固定 `touch_queue_allowed=false`。
- `llm_lead_extraction` 与 `llm_lead_grading` 的校验异常路径均调用 `record_failed_case`。
- `public_page_read_agent` 的 failed 页面读取路径记录 `fetch_failed`。
- 将真实库验证阻塞原因记录为残留风险。

## 7. 残留风险

- 当前 Codex 沙箱无法连接真实 PostgreSQL/Redis，`20260529_0017_failed_cases.py` 需在可出网环境执行 `alembic upgrade head` 复验。
- `failed_cases` 已为知识库 RAG 预留 `usable_for_rag`，实际导入知识库由 P1-E5 系列 Story 承接。

## 8. 下一步建议

继续执行：

`docs/stories/phase-1-small-run/P1-E5-S1-pgvector-knowledge-schema.md`

