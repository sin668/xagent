# P2-E4-S5 移动端前后端联调与 H5 可用性验证结果

## 基本信息

- Story：`docs/stories/phase-2-small-run/P2-E4-S5-mobile-h5-integration-verification.md`
- 状态：已完成
- 执行日期：2026-06-02
- 执行原则：每次只执行一个 Story；不做锁操作；不做 git 操作；完成前执行验证；完成后执行两轮独立多维度评审。

## 环境启动

### API

使用 `booking-room` 环境启动：

```bash
set -a
source apps/api/.env
set +a
/opt/miniconda3/envs/booking-room/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

验证：

```bash
curl -sS http://127.0.0.1:8000/health
```

结果：

```json
{"status":"ok","service":"vehicle-leads-api"}
```

### 移动端 H5

启动：

```bash
npm --prefix apps/mobile run dev:h5
```

H5 地址：

- `http://localhost:5176/`
- `http://127.0.0.1:5176/`

验证：

```bash
curl -sS http://127.0.0.1:5176/
```

结果：返回 H5 入口 HTML，包含 `<div id="app"></div>` 和 `/src/main.js`。

## 真实 API 联调

### 临时联调样本

真实 PostgreSQL 初始来源候选列表为空。为验证来源详情与审核动作，使用现有后端模型和服务层向真实 PostgreSQL 写入一条临时候选：

- `candidate_id`：`99cdd82c-2b05-44eb-87f5-9f1e1439b6f1`
- `channel_name`：`mobile_h5_integration`
- `country`：`Russia`
- `city`：`Moscow`
- `risk_level`：`Medium`
- `review_status`：`auto_approved`
- `approved_for_extraction`：`true`

该样本已在联调完成后清理，避免污染后端分页测试。

### 来源候选列表 API

请求：

```bash
curl -sS 'http://127.0.0.1:8000/lead-source-candidates?limit=5&offset=0'
```

结果要点：

- `total=1`
- 返回 `integration-1ac638d2.example.ru`
- `risk_level=Medium`
- `review_status=auto_approved`
- `approved_for_extraction=true`

### 来源详情 API

请求：

```bash
curl -sS 'http://127.0.0.1:8000/lead-source-candidates/99cdd82c-2b05-44eb-87f5-9f1e1439b6f1'
```

结果要点：

- 返回 `source_url`
- 返回 `evidence_note`
- 返回 `created_by_task_run_id=9fdebd26-2ad9-4843-93b4-a9bfb91d5fcc`
- 返回 `llm_output_summary.candidate_count=1`

### 审核动作 API

请求：

```bash
curl -sS -X POST \
  'http://127.0.0.1:8000/lead-source-candidates/99cdd82c-2b05-44eb-87f5-9f1e1439b6f1/review-actions' \
  -H 'Content-Type: application/json' \
  -d '{"action":"add_review_note","reviewer_id":"p2-e4-s5-mobile-h5","review_note":"P2-E4-S5 移动端 H5 联调验证：审核动作真实 API 已触发。"}'
```

结果要点：

- `reviewer_id=p2-e4-s5-mobile-h5`
- `review_note` 已写入
- `audit_task_run_id=466fc8ee-df4c-4abe-91b6-7edca669daef`

### Agent 手动启动 API

Source Discovery 请求：

```bash
curl -sS -X POST \
  'http://127.0.0.1:8000/agent-tasks/source-discovery/run' \
  -H 'Content-Type: application/json' \
  -d '{"country":"Russia","cities":["Moscow"],"channel_strategy":"official_website_public_directory_search_engine","keywords":["автосалон"],"limit":20}'
```

结果：

```json
{"agent_task_run_id":"6f67c450-b65f-4c0b-b1a3-374790b08d62","status":"failed","created_count":0,"blocked_count":0,"duplicate_count":0}
```

判定：可以创建任务并返回明确任务状态。失败原因预计与当前 LLM 配置未提供有效 API Key 相关，后续 LLM/调度阶段继续处理。

Lead Extraction 请求：

```bash
curl -sS -X POST \
  'http://127.0.0.1:8000/agent-tasks/lead-extraction/run' \
  -H 'Content-Type: application/json' \
  -d '{"country":"Russia","cities":["Moscow"],"channel_strategy":"approved_sources_only","prompt_template_key":"lead_extraction_default","limit":20}'
```

结果：

```json
{"detail":"Not Found"}
```

判定：返回明确错误，说明后端 `LEAD_EXTRACTION` 手动启动端点当前尚未实现。移动端页面已具备调用契约，后端实现应在后续 P2-E5 相关 Story 中补齐。

## H5 页面可用性

使用 `browse chain` 读取 `html body`。`browse text` 对 uni-app 自定义元素读取为空，不能作为页面空白判断依据。

### 来源候选队列页

地址：

```text
http://127.0.0.1:5176/#/pages/sources/index
```

DOM 证据要点：

- `data-page="pages/sources/index"`
- `来源审核`
- `第二阶段今日来源池`
- `1 新增`
- `integration-1ac638d2.example.ru`
- `Medium`
- `auto_approved`
- `可抽取`
- `公开官网样例，包含 dealer、import vehicles、contacts 等可抽取信号`

判定：页面非空白，且渲染真实 API 数据。

### 来源详情页

地址：

```text
http://127.0.0.1:5176/#/pages/sources/detail?id=99cdd82c-2b05-44eb-87f5-9f1e1439b6f1
```

DOM 证据要点：

- `data-page="pages/sources/detail"`
- `来源详情`
- `审核通过只代表允许抽取，不代表允许触达`
- `integration-1ac638d2.example.ru`
- `Medium 风险`
- `approvedForExtraction true`
- `SOURCE_DISCOVERY`
- `createdByTaskRunId 9fdebd26-2ad9-4843-93b4-a9bfb91d5fcc`
- `只读抽取`
- `添加备注`

判定：详情页可加载真实 API 数据，风险边界文案可见。

### Agent 手动调用页

地址：

```text
http://127.0.0.1:5176/#/pages/agent-run/index
```

DOM 证据要点：

- `data-page="pages/agent-run/index"`
- `启动 Agent`
- `SOURCE_DISCOVERY`
- `LEAD_EXTRACTION`
- `国家`
- `城市`
- `渠道策略`
- `Prompt Template`
- `运行上限`
- `agent_task_runs Unknown`
- `自动私信 禁用`
- `登录采集 禁用`
- `High 抽取 人工审核`
- `Forbidden 阻断`

判定：页面非空白，任务参数和安全边界可见。

## 自动化验证

### 移动端测试

```bash
npm --prefix apps/mobile test
```

结果：`69/69 passed`。

### 移动端 H5 构建

```bash
npm --prefix apps/mobile run build:h5
```

结果：通过，输出 `DONE Build complete.`。

### 后端相关测试

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest \
  apps/api/tests/test_lead_source_candidates_query_api.py \
  apps/api/tests/test_lead_source_candidates_review_api.py \
  apps/api/tests/test_source_discovery_agent_api.py
```

结果：`15 passed`。

## 调试与修正记录

1. API 首次启动失败：
   - 现象：系统 `uvicorn` 使用 Python 3.7，导入 `sqlalchemy.ext.asyncio.async_sessionmaker` 失败。
   - 根因：未使用 `booking-room` 环境。
   - 修正：改用 `/opt/miniconda3/envs/booking-room/bin/uvicorn`。

2. H5 首次启动失败：
   - 现象：沙箱内绑定 `0.0.0.0:5176` 返回 `EPERM`。
   - 根因：端口绑定需要提升权限。
   - 修正：按权限规则提升权限启动 `npm --prefix apps/mobile run dev:h5`。

3. `browse text` 读取为空：
   - 现象：页面明明导航成功，但文本为空。
   - 根因：uni-app H5 使用自定义元素，`text` 抽取不可靠。
   - 修正：改用 `browse chain` 的 `html body`，确认 DOM 已渲染。

4. 后端测试曾失败：
   - 现象：`test_list_lead_source_candidates_supports_limit_and_offset` 中 `total` 从 3 变 4。
   - 根因：临时联调样本污染真实测试库中 `country=Russia` 的分页断言。
   - 修正：清理 `channel_name=mobile_h5_integration` 的候选和对应任务记录，复跑后端测试 `15 passed`。

## 第一轮独立多维度评审

- 结论：通过，无实质阻塞问题。
- 联调完整性：API、H5、来源队列、来源详情、审核动作、Agent 页面均已验证。
- 数据真实性：使用真实 PostgreSQL 临时样本和真实 HTTP API，不依赖移动端 seed 静态页面。
- 风控合规：联调未执行自动私信、自动加好友、登录采集、反爬规避或自动触达。
- 发现项：`LEAD_EXTRACTION` 手动启动后端端点当前未实现，返回 `404 Not Found`。
- 修正结果：记录为明确错误，符合本 Story 验收范围；后续 P2-E5 相关 Story 应补齐后端端点与来源池消费链路。

## 第二轮独立多维度评审

- 结论：通过，连续两轮未发现新增实质阻塞问题。
- 回归风险：移动端测试 `69/69 passed`，后端相关测试 `15 passed`。
- 编译风险：移动端 H5 构建通过。
- 数据污染风险：联调样本已清理，后端分页测试恢复通过。
- 环境风险：归档明确 API 必须使用 `booking-room` 环境启动。
- 范围控制：未执行下一 Story，未实现调度、Redis lock、Lead Extraction 后端端点或 Dashboard。
- 修正结果：无需新增修正。
