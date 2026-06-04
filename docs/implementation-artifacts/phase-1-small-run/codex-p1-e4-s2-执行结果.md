# P1-E4-S2 执行结果

Story：`docs/stories/phase-1-small-run/P1-E4-S2-public-page-read-agent.md`  
执行人：Codex  
执行日期：2026-05-29  
状态：已完成本地实现、TDD、定向回归、编译检查和 Story 状态回写；真实 PostgreSQL/Redis 联调验证受当前沙箱出网限制影响，待可出网环境复验

## 1. 执行说明

本 Story 按 `docs/AI协同开发执行标准.md`、第一阶段实施计划和 superpowers TDD/verification 规范执行。用户已明确要求不执行 Story lock 操作，因此本 Story 未执行任何锁命令。

## 2. 修改文件

- `apps/api/app/services/public_page_read_agent.py`
- `apps/api/app/schemas/public_page_read.py`
- `apps/api/app/api/public_page_read.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_public_page_read_agent.py`
- `docs/stories/phase-1-small-run/P1-E4-S2-public-page-read-agent.md`
- `_bmad-output/implementation-artifacts/codex-p1-e4-s2-执行结果.md`

## 3. 实现内容

### 3.1 公开页面读取 Agent

新增 `PublicPageReadAgentService`，用于读取单个候选 URL 的公开页面摘要。

核心能力：

- 仅执行单 URL 公开读取
- 不使用登录、Cookie、认证或绕过策略
- 提取页面标题和正文摘要
- 移除 script/style/noscript/svg/canvas 内容
- 不保存完整 HTML 或完整网页镜像
- 写入 `page_snapshots`
- 写入 Agent 运行审计日志

### 3.2 访问限制识别

已覆盖：

- captcha / recaptcha
- login required / sign in to continue
- access denied / forbidden
- 俄语登录、授权、验证码、安全检查相关提示
- HTTP 401 / 403 / 407 / 429 记录为 blocked
- HTTP 404 / 500 等异常状态码记录为 failed

出现验证码、登录墙或访问策略墙时：

- `read_status=blocked`
- 不保存受限正文
- `robots_or_policy_note` 记录“不尝试登录或绕过访问限制”

### 3.3 High 风险最小证据保存

High 风险页面只保存有限商务证据：

- 保留公开商务联系方式、公司介绍等文本摘要
- 过滤 followers、following、friends、comments、likes、俄语订阅者/好友/评论/点赞等社交关系链文本
- 文本摘要限制为 `600` 字符

### 3.4 API

新增：

```text
POST /public-page-read/run
```

请求：

```json
{
  "candidate_url_id": "uuid",
  "public_html": "<optional public html/text>"
}
```

说明：

- `public_html` 可为空；为空时服务端执行单 URL 公开读取。
- `public_html` 可用于人工或受控工具已读取的公开内容，仍然只保存标题、摘要和证据。

响应包含：

- `snapshot`

## 4. 验收结果

| 验收项 | 结论 | 证据 |
|---|---|---|
| 读取公开页面标题和文本摘要 | 通过 | `build_snapshot_payload` 提取 title/text_excerpt |
| 保存 page_snapshots | 通过 | `read_candidate_page` 调用 `RawCollectionService.create_page_snapshot` |
| 检测登录墙、验证码、访问异常 | 通过 | `contains_access_wall` + HTTP 状态码处理 |
| 支持 read_status | 通过 | success / blocked / failed |
| 不登录 | 通过 | `fetch_public_page` 不带 Cookie、认证或登录流程 |
| 不绕过访问限制 | 通过 | blocked 后停止，不重试绕过 |
| 验证码或登录墙停止并记录 blocked | 通过 | 对应测试覆盖 |
| High 页面只保存公开商务字段和有限证据 | 通过 | High 风险过滤社交关系链并限制摘要长度 |
| 不做大规模爬虫 | 通过 | API 一次只处理一个 candidate URL |
| 不保存完整网页镜像 | 通过 | 只保存 `text_excerpt`，不保存 HTML |
| 不保存评论、粉丝、好友、关系链 | 通过 | High 风险过滤规则和测试覆盖 |

## 5. 测试记录

### 5.1 测试先行

首次运行：

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_public_page_read_agent.py -q
```

结果：

```text
ERROR ModuleNotFoundError: No module named 'app.services.public_page_read_agent'
```

补充 HTTP 异常测试后再次 RED：

```text
FAILED test_http_error_without_access_wall_is_recorded_as_failed
```

### 5.2 实现后测试

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_public_page_read_agent.py -q
```

结果：

```text
6 passed in 0.19s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m py_compile apps/api/app/services/public_page_read_agent.py apps/api/app/schemas/public_page_read.py apps/api/app/api/public_page_read.py apps/api/app/main.py
```

结果：通过。

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_public_page_read_agent.py apps/api/tests/test_page_snapshots_foundation.py apps/api/tests/test_raw_collection_foundation.py apps/api/tests/test_high_risk_public_discovery_isolation.py apps/api/tests/test_staging_lead_detail_evidence.py -q
```

结果：

```text
31 passed in 0.96s
```

```bash
/opt/miniconda3/envs/booking-room/bin/python -m pytest apps/api/tests/test_public_page_read_agent.py apps/api/tests/test_page_snapshots_foundation.py apps/api/tests/test_raw_collection_foundation.py apps/api/tests/test_high_risk_public_discovery_isolation.py apps/api/tests/test_staging_lead_detail_evidence.py apps/api/tests/test_channel_discovery_agent.py apps/api/tests/test_channel_plans_foundation.py apps/api/tests/test_audit_risk_logs_foundation.py -q
```

结果：

```text
53 passed in 0.44s
```

```bash
cd apps/api
/opt/miniconda3/envs/booking-room/bin/python -m alembic heads
```

结果：

```text
20260529_0016 (head)
```

## 6. 两轮独立评审

### 6.1 第一轮：需求和安全边界评审

结论：通过，发现 1 个边界问题并已修正。

发现项：

- HTTP 404/500 等访问异常不能被当作成功公开页面保存摘要。

修正结果：

- 增加 `test_http_error_without_access_wall_is_recorded_as_failed`。
- `build_snapshot_payload` 对非访问墙类 HTTP 4xx/5xx 返回 `read_status=failed`，不保存正文摘要。

### 6.2 第二轮：实现、数据最小化和回归评审

结论：通过，存在真实数据库/Redis 联调环境残留验证项。

发现项：

- High 风险页面不能保存评论、粉丝、好友、点赞等社交关系链。
- 不应新增表或迁移，P1-E1-S3 已提供 `page_snapshots`。
- 当前 Codex 沙箱仍无法连接真实 PostgreSQL/Redis。

修正结果：

- High 风险摘要过滤 social graph 相关行，并限制为 600 字符。
- 未新增 migration，Alembic head 保持 `20260529_0016`。
- 将真实库验证阻塞原因记录为残留风险。

## 7. 残留风险

- 当前 Codex 沙箱无法连接真实 PostgreSQL/Redis，`POST /public-page-read/run` 的真实库写入需在可出网环境复验。
- 服务端真实 URL 读取依赖目标站点可公开访问；遇到验证码、登录墙、403/429 时会按规则停止，不会尝试绕过。

## 8. 下一步建议

继续执行：

`docs/stories/phase-1-small-run/P1-E4-S3-llm-lead-extraction.md`

