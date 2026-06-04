# P2-E3-S1 执行结果：实现 Source Discovery 输出 schema 校验服务

执行日期：2026-06-02  
Story 文件：`docs/stories/phase-2-small-run/P2-E3-S1-source-discovery-schema-validation.md`  
状态：Done

## 1. 执行范围

本次只执行 P2-E3-S1，不执行下一个 Story。

已完成：

- 创建 `apps/api/app/services/source_discovery_schema.py`。
- 创建 `apps/api/tests/test_source_discovery_schema.py`。
- 实现 `SourceDiscoverySchemaService.validate_output`。
- 实现结构化错误 `SourceDiscoveryValidationError`，默认 `error_type=schema_validation_error`。
- 校验 Source Discovery 顶层字段、候选来源字段、风险等级和 blocked 来源隔离规则。

未执行：

- 未写入 `lead_source_candidates`。
- 未实现来源候选 upsert。
- 未实现 Source Discovery Agent。
- 未实现来源候选查询或审核 API。
- 未执行 P2-E3-S2 或其他后续 Story。

## 2. 修改文件

- `apps/api/app/services/source_discovery_schema.py`
- `apps/api/tests/test_source_discovery_schema.py`
- `docs/stories/phase-2-small-run/P2-E3-S1-source-discovery-schema-validation.md`
- `_bmad-output/implementation-artifacts/codex-p2-e3-s1-执行结果.md`

## 3. TDD 记录

RED：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_source_discovery_schema.py -q
```

结果：

```text
ModuleNotFoundError: No module named 'app.services.source_discovery_schema'
```

失败原因：Source Discovery schema 校验服务尚未实现，符合当前 Story 的 RED 预期。

GREEN：

- 新增 Source Discovery schema 校验服务。
- 补充合法输出、缺字段、非法风险等级、Forbidden 错位、blocked 自动抽取隔离、输入不变性测试。
- 首次实现后发现 normalized output 仍保留 `blocked_candidates[].approved_for_extraction=true`，已修正为 normalized output 不保留该字段，校验结果中的 blocked candidates 强制 `approved_for_extraction=false`。

## 4. 验证命令与结果

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_source_discovery_schema.py -q
```

结果：

```text
12 passed in 0.04s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_source_discovery_schema.py apps/api/tests/test_llm_prompt_templates.py apps/api/tests/test_llm_prompt_templates_api.py apps/api/tests/test_llm_client.py apps/api/tests/test_llm_fallback.py apps/api/tests/test_llm_settings.py apps/api/tests/test_llm_health_api.py -q
```

结果：

```text
35 passed in 4.02s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/source_discovery_schema.py apps/api/tests/test_source_discovery_schema.py
```

结果：通过，退出码 0。

## 5. 验收结果

- 合法 Source Discovery 输出通过。
- 缺 URL 失败。
- 缺 evidence 失败。
- 非法风险等级失败。
- `task_type`、`country`、`city`、`channel_strategy`、`candidates`、`blocked_candidates` 均有校验。
- `blocked_candidates` 不进入自动抽取。
- `Unknown`、`null`、空数组会被保留，不在校验层补造字段。

## 6. 风控结果

- 未调用真实 LLM。
- 未写入数据库。
- 未自动社交私信。
- 未自动加好友。
- 未登录后批量采集。
- 未反爬规避。
- 未抓取非公开数据。
- High/Forbidden 风险边界未被放宽。

## 7. 双轮评审记录

### 第一轮评审：Schema 契约与 Story 范围

结论：通过。

发现项：

- 合法 Source Discovery 输出可通过校验。
- 缺 URL、缺 evidence、非法 risk_level 均失败。
- 顶层字段 `task_type/country/city/channel_strategy/candidates/blocked_candidates` 均有校验。
- `Forbidden` 不允许进入 `candidates`。
- `blocked_candidates` 不进入自动抽取。
- 本 Story 未越界写库、upsert 或实现 Agent。

修正结果：

- 已修正 blocked 来源在 normalized output 中残留 `approved_for_extraction=true` 的问题。

### 第二轮评审：合规边界、不可编造与测试证据

结论：通过。

发现项：

- 目标测试 12 条通过，相关回归测试 35 条通过。
- Python 编译通过。
- `Unknown`、`null`、空数组会被保留，不在校验层补造缺失字段。
- 校验服务不会调用真实 LLM，不抓取网页，不触达客户。
- High/Forbidden 风险边界未被放宽。

修正结果：

- 无新增实质阻塞问题，无需修正。
