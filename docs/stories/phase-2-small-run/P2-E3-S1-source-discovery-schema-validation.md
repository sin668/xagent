# Story P2-E3-S1：实现 Source Discovery 输出 schema 校验服务

状态：Done  
Sprint：Sprint 2  
优先级：P0  
Epic：P2-E3

## 用户故事

作为第二阶段小范围运行的研发执行者，我希望完成“实现 Source Discovery 输出 schema 校验服务”，以便系统可以按 BMAD 已冻结方案推进真实 LLM、来源发现、审核、抽取、审计和联调闭环。

## 上下文来源

- `docs/product/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行方案与产品技术设计.md`
- `_bmad-output/brainstorming/brainstorming-session-2026-06-02-第二阶段小范围运行-LLM来源发现Agent.md`
- `docs/superpowers/plans/2026-06-02-海外车辆采购AI获客系统-第二阶段小范围运行Codex推进计划.md`
- `docs/AI协同开发执行标准.md`
- `AGENTS.md`

## Story 定义

**目标：** 对 LLM Source Discovery 输出做结构化校验，失败不入库。

**Files:**

- Create: `apps/api/app/services/source_discovery_schema.py`
- Test: `apps/api/tests/test_source_discovery_schema.py`

**Codex 提示词：**

```text
请执行 P2-E3-S1：实现 Source Discovery 输出 schema 校验服务。

要求：
1. 使用 superpowers:test-driven-development。
2. 校验 task_type、country、city、channel_strategy、candidates、blocked_candidates。
3. 每条 candidate 必须有 source_url、platform、risk_level、discovery_reason、evidence_note。
4. risk_level 只允许 Low、Medium、High、Forbidden。
5. 缺失字段必须保留 Unknown、null 或空数组，不允许校验层补造。
6. blocked_candidates 不进入自动抽取。
7. 运行 pytest apps/api/tests/test_source_discovery_schema.py。
8. 完成后执行两轮独立评审，并写入 _bmad-output/implementation-artifacts/codex-p2-e3-s1-执行结果.md。
不要执行下一个 Story。
```

**验收标准：**

- 合法输出通过。
- 缺证据、缺 URL、非法风险等级失败。

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

- 新增 `apps/api/app/services/source_discovery_schema.py`。
- 新增 `apps/api/tests/test_source_discovery_schema.py`。
- 实现 `SourceDiscoverySchemaService.validate_output`。
- 实现结构化错误 `SourceDiscoveryValidationError`，默认 `error_type=schema_validation_error`。
- 校验顶层字段：
  - `task_type`
  - `country`
  - `city`
  - `channel_strategy`
  - `candidates`
  - `blocked_candidates`
- 校验每条 candidate 必填：
  - `source_url`
  - `platform`
  - `risk_level`
  - `discovery_reason`
  - `evidence_note`
- `risk_level` 允许：`Low`、`Medium`、`High`、`Forbidden`。
- `Forbidden` 不允许进入 `candidates`，必须进入 `blocked_candidates`。
- `High` 不允许 `approved_for_extraction=true`。
- `blocked_candidates` 在校验结果中强制 `approved_for_extraction=false`，且 normalized output 不保留输入中的自动抽取字段。
- 缺失占位值 `Unknown`、`null`、空数组会被保留，不在校验层补造字段。

未执行：

- 未写入 `lead_source_candidates`。
- 未实现来源候选 upsert。
- 未实现 Source Discovery Agent。
- 未实现来源候选查询或审核 API。
- 未执行 P2-E3-S2 或其他后续 Story。

## TDD 记录

RED：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_source_discovery_schema.py -q
```

结果：

```text
ModuleNotFoundError: No module named 'app.services.source_discovery_schema'
```

失败原因符合预期：Source Discovery schema 校验服务尚未实现。

GREEN：

- 新增 Source Discovery schema 校验服务。
- 补充合法输出、缺字段、非法风险等级、Forbidden 错位、blocked 自动抽取隔离、输入不变性测试。
- 首次实现后发现 normalized output 仍保留 `blocked_candidates[].approved_for_extraction=true`，已修正为 normalized output 不保留该字段，校验结果中的 blocked candidates 强制 `approved_for_extraction=false`。

## 验证结果

目标测试：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_source_discovery_schema.py -q
```

结果：

```text
12 passed in 0.04s
```

相关回归：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_source_discovery_schema.py apps/api/tests/test_llm_prompt_templates.py apps/api/tests/test_llm_prompt_templates_api.py apps/api/tests/test_llm_client.py apps/api/tests/test_llm_fallback.py apps/api/tests/test_llm_settings.py apps/api/tests/test_llm_health_api.py -q
```

结果：

```text
35 passed in 4.02s
```

编译验证：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/source_discovery_schema.py apps/api/tests/test_source_discovery_schema.py
```

结果：通过，退出码 0。

## 两轮独立评审记录

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
