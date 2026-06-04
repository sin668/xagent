# PoC 阶段 Deploy 与验证 Runbook

创建日期：2026-05-27

## 1. 目标

本 Runbook 用于在 macOS 本地串联当前所有 PoC 阶段产物，帮助团队推进俄罗斯车辆采购 AI 获客 PoC 验证过程。

它覆盖：

- PoC 文档检查。
- 飞书五张表 Excel seed 数据生成。
- 关键词库 Excel 生成。
- FAQ 与俄语触达模板 Excel 生成。
- CSV 校验、去重和失败案例统计脚本。
- PoC 复盘模板和手工仪表盘口径。

## 2. 当前产物地图

### 2.1 文档

| 文件 | 用途 |
|---|---|
| `docs/poc/feishu-fields.md` | 飞书五张表字段字典与创建步骤 |
| `docs/poc/channel-risk-register.md` | 渠道风险登记表与合规 SOP |
| `docs/poc/russian-keyword-library.md` | 俄罗斯车商线索关键词库 |
| `docs/poc/faq-and-outreach-templates.md` | FAQ 与俄语触达模板 |
| `docs/poc/ai-output-schema.md` | AI 抽取/分级输出 JSON schema |
| `docs/poc/manual-dashboard-metrics.md` | PoC 手工仪表盘口径 |
| `docs/poc/poc-retro-template.md` | PoC 复盘报告模板 |

### 2.2 Prompts

| 文件 | 用途 |
|---|---|
| `prompts/lead-extraction.md` | AI 公开网页信息抽取 Prompt |
| `prompts/lead-grading.md` | AI 线索分级建议 Prompt |

### 2.3 脚本

| 文件 | 用途 |
|---|---|
| `scripts/poc/run_poc.sh` | macOS 一键 PoC 总控脚本 |
| `scripts/poc/build_feishu_seed_workbook.mjs` | 生成飞书五张表 seed Excel |
| `scripts/poc/build_russian_keyword_library_workbook.mjs` | 生成关键词库 Excel |
| `scripts/poc/build_faq_outreach_workbook.mjs` | 生成 FAQ/话术 Excel |
| `scripts/poc/validate_leads.py` | CSV 校验、去重和失败案例统计 |

### 2.4 Excel 输出

| 文件 | 用途 |
|---|---|
| `outputs/poc-feishu-seed/俄罗斯车辆采购AI获客PoC-飞书五张表Seed数据.xlsx` | 合并版五张表 seed 数据 |
| `outputs/poc-feishu-seed/客户线索.xlsx` | 客户线索独立表 |
| `outputs/poc-feishu-seed/渠道来源.xlsx` | 渠道来源独立表 |
| `outputs/poc-feishu-seed/车源报价.xlsx` | 车源报价独立表 |
| `outputs/poc-feishu-seed/触达记录.xlsx` | 触达记录独立表 |
| `outputs/poc-feishu-seed/话术库.xlsx` | 话术库独立表 |
| `outputs/poc-keywords/俄罗斯车商线索关键词库初版.xlsx` | 关键词库 |
| `outputs/poc-faq/FAQ与俄语触达模板初版.xlsx` | FAQ 与俄语触达模板 |

## 3. macOS 本地运行方式

### 3.1 一键构建与验证

在项目根目录执行：

```bash
chmod +x scripts/poc/run_poc.sh
scripts/poc/run_poc.sh all
```

该命令会：

1. 重新生成所有 PoC Excel。
2. 跑 CSV 校验脚本的单元测试。
3. 检查关键文档、prompts、脚本和 Excel 是否存在。

成功时应看到：

```text
PoC local deployment bundle is ready
```

### 3.2 只重新生成 Excel

```bash
scripts/poc/run_poc.sh build
```

### 3.3 只运行测试

```bash
scripts/poc/run_poc.sh test
```

预期结果：

```text
Ran 6 tests
OK
```

### 3.4 检查产物是否齐全

```bash
scripts/poc/run_poc.sh check
```

### 3.5 校验真实线索 CSV

从飞书客户线索表导出 CSV 后执行：

```bash
scripts/poc/run_poc.sh validate path/to/客户线索.csv outputs/poc-validation/lead-validation-report.json
```

输出报告包含：

- 必填字段错误。
- 来源链接错误。
- 勿扰状态警告。
- 线索等级合法性。
- 强重复：客户名称 + 联系方式。
- 疑似重复：客户名称 + 城市 + 来源域名。
- 失败案例统计。
- AI 错误分类案例。

脚本不会删除或修改原 CSV。

## 4. PoC 推进流程

### Step 1：准备飞书表格

参考：

- `docs/poc/feishu-fields.md`
- `outputs/poc-feishu-seed/俄罗斯车辆采购AI获客PoC-飞书五张表Seed数据.xlsx`

动作：

1. 在飞书创建 `俄罗斯车辆采购AI获客PoC` 多维表格。
2. 创建五张表：客户线索、渠道来源、车源报价、触达记录、话术库。
3. 使用 Excel seed 数据导入或手动配置字段。
4. 建立视图：待复核、B级、C级、勿扰、无效、待触达、高风险来源。

验收：

- 五张表可录入、可筛选、可分配。
- 勿扰字段存在。
- 来源链接和来源证据备注为必备字段。

### Step 2：配置渠道风险

参考：

- `docs/poc/channel-risk-register.md`
- `outputs/poc-feishu-seed/渠道来源.xlsx`

动作：

1. 导入或复制渠道来源表。
2. 确认 Low/Medium/High/Forbidden 风险等级。
3. 确认允许动作和禁止动作。
4. High 风险渠道只保留政策研究和人工小样本，不进入自动化任务。

验收：

- 自动社交私信、自动加好友、登录后批量采集、反爬规避均被禁止。
- High/Forbidden 不进入 PoC 自动任务。

### Step 3：配置关键词库

参考：

- `docs/poc/russian-keyword-library.md`
- `outputs/poc-keywords/俄罗斯车商线索关键词库初版.xlsx`

动作：

1. 将关键词库导入飞书或作为运营文档使用。
2. 首批 50 条试采优先使用搜索引擎、官网、公开目录、Google/Yandex 地图结果和 Drom 公开页。
3. 排除维修、配件、保险、招聘、媒体、租车、驾校、洗车等非目标。

验收：

- 至少覆盖 Moscow、Saint Petersburg、Vladivostok、Novosibirsk、Kazan。
- 每个关键词有用途、适用渠道、风险建议和有效率字段。

### Step 4：配置 FAQ 和俄语话术

参考：

- `docs/poc/faq-and-outreach-templates.md`
- `outputs/poc-faq/FAQ与俄语触达模板初版.xlsx`

动作：

1. 将 FAQ 与模板导入话术库。
2. 业务负责人审核价格、车况、合作模式相关内容。
3. 合规负责人审核物流、清关、付款、拒绝联系路径。
4. 只有“可外发”状态的话术可供 AI 引用。

验收：

- 俄语话术不承诺最终价格、物流、清关、付款或交付周期。
- 每条触达模板包含拒绝联系路径。

### Step 5：执行首批 50 条试采

参考：

- `prompts/lead-extraction.md`
- `prompts/lead-grading.md`
- `docs/poc/ai-output-schema.md`

动作：

1. 只从 Low/Medium 风险渠道人工收集公开文本和来源链接。
2. 使用 AI 抽取客户名称、城市、联系方式、经营信号和证据。
3. 使用 AI 给出 A/B/C/Invalid/Watch 建议。
4. 人工复核 AI 建议。
5. Invalid 和 Watch 不进入触达队列。
6. C 级必须标记合规复核。

验收：

- 每条线索有来源链接和证据备注。
- AI 缺失字段输出 Unknown、null 或空数组，不编造。
- High/Forbidden 未进入自动任务。

### Step 6：每日 CSV 校验

动作：

1. 从飞书客户线索表导出 CSV。
2. 运行：

```bash
scripts/poc/run_poc.sh validate path/to/客户线索.csv outputs/poc-validation/day-01-report.json
```

3. 线索运营查看重复和失败案例。
4. 将失败案例同步到排除关键词和审核规则。

验收：

- 强重复进入人工复核。
- 疑似重复不自动删除。
- 失败案例不删除来源证据。

### Step 7：小样本人工触达

参考：

- `docs/poc/faq-and-outreach-templates.md`
- `docs/poc/channel-risk-register.md`

动作：

1. 从 B/C 级线索中选择 10-20 条。
2. 使用可外发俄语模板生成草稿。
3. 人工审核后发送。
4. 记录触达渠道、话术版本、发送人、发送时间、回复状态、下一步动作。
5. 客户拒绝后立即标记勿扰。

验收：

- 没有自动社交私信。
- 没有自动加好友。
- 勿扰客户不会再次触达。

### Step 8：手工仪表盘与复盘

参考：

- `docs/poc/manual-dashboard-metrics.md`
- `docs/poc/poc-retro-template.md`

动作：

1. 建立飞书手工仪表盘。
2. 汇总渠道有效率、A/B/C 比例、触达回复、风险事件、客服/销售反馈和 ROI。
3. 做 Go/重跑/暂停决策。

验收：

- Go 进入 MVP。
- 或重跑 PoC。
- 或暂停俄罗斯方向。

## 5. Go / No-Go 门

### Go：进入 MVP

必须同时满足：

- 至少 3 个可持续低/中风险渠道。
- 100-200 条线索中，B 级比例达到 30%-50% 或接近目标且趋势明确。
- 小样本触达有真实回复或明确负反馈。
- 无账号封禁、平台投诉、明显违规采集或批量骚扰。
- 客服/销售认为字段、话术和交付方式可用。
- C 级报价/合同前合规复核路径明确。

### 重跑 PoC

适用：

- B 级比例未达标但高于 20%。
- 有有效渠道但关键词、地区、话术或客户画像需要调整。
- 触达反馈不足但团队认为线索可用。

### 暂停俄罗斯方向

出现任一情况应暂停：

- B 级线索低于 20%。
- 小样本触达几乎无人回复，或多数明确拒绝。
- 出现投诉、封禁、账号限制、访问异常或明显违规风险。
- 销售团队不愿承接。
- 贸易、支付、物流或清关路径不可行。

## 6. 故障处理

### 6.1 run_poc.sh 提示 Node 不存在

默认脚本使用 Codex bundled Node。如果在其他 Mac 上运行，请设置：

```bash
export NODE_BIN="$(which node)"
export NODE_MODULES_DIR="/path/to/node_modules"
scripts/poc/run_poc.sh build
```

注意：生成 Excel 依赖 `@oai/artifact-tool`。如果其他机器没有该依赖，可以只使用已生成的 Excel 文件，不重新构建。

### 6.2 run_poc.sh 提示 Python 不存在

设置本机 Python：

```bash
export PYTHON_BIN="$(which python3)"
scripts/poc/run_poc.sh test
```

### 6.3 validate CSV 中文乱码

建议从飞书导出 UTF-8 CSV。脚本会按 `utf-8-sig` 读取，通常可兼容带 BOM 的 Excel/飞书导出文件。

### 6.4 CSV 校验错误很多

优先检查：

- 字段名是否和 `docs/poc/feishu-fields.md` 一致。
- 来源链接是否以 `http://` 或 `https://` 开头。
- 线索等级是否为 `A/B/C/Invalid/Watch`。
- 勿扰为“是”时是否填写勿扰原因。

## 7. 禁止绕过事项

任何情况下不得为了提高线索数量而绕过：

- 自动社交私信禁令。
- 自动加好友禁令。
- 登录后批量采集禁令。
- 反爬规避禁令。
- High/Forbidden 渠道阻断规则。
- 勿扰客户不再触达规则。
- C 级报价/合同前合规复核规则。

