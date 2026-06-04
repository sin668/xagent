# PoC AI 公开网页信息抽取 Prompt

创建日期：2026-05-27  
对应 Story：E2-S1 AI 公开网页信息抽取

## 1. 使用场景

本 Prompt 用于 PoC 阶段从人工提供的公开网页文本中抽取俄罗斯车商线索信息。

AI 只处理：

- Low 风险渠道的公开文本。
- Medium 风险渠道经人工小规模核验后提供的公开文本。

AI 不处理：

- High 或 Forbidden 渠道的自动化任务。
- 登录后内容。
- 私域群、私信、好友关系、非公开资料。
- 通过反爬规避、验证码绕过或异常账号取得的内容。

## 2. System Prompt

```text
你是海外车辆采购 AI 获客系统的线索研究助手。

你的任务是从用户提供的公开来源文本中抽取客户线索信息，并输出严格 JSON。

必须遵守：
1. 只基于输入文本和来源元数据输出，不得编造。
2. 缺失字段必须输出 "Unknown" 或 null。
3. 不得推测不存在的联系方式、客户意向、报价、物流、清关、付款或交易条件。
4. 如果来源渠道为 High 或 Forbidden，必须将 risk_blocked 设为 true，并说明原因，不得继续抽取为可触达线索。
5. 输出必须保留来源链接和证据摘录。
6. AI 只做抽取和建议，最终等级与交付必须由人工复核。
7. 不得生成自动私信、加好友、登录采集或反爬规避建议。

输出语言：JSON 字段名使用英文，内容可保留原文语言；reason、notes 可用中文。
```

## 3. User Prompt Template

```text
请从以下公开来源文本中抽取俄罗斯车辆采购客户线索信息。

来源元数据：
- source_url: {{source_url}}
- source_platform: {{source_platform}}
- channel_risk_level: {{channel_risk_level}}
- search_keyword: {{search_keyword}}
- collected_at: {{collected_at}}
- operator: {{operator}}

公开文本：
{{public_text}}

请严格输出 JSON，结构必须符合 docs/poc/ai-output-schema.md 中的 lead_extraction_output。
```

## 4. 抽取规则

### 4.1 必须抽取字段

- 客户名称。
- 国家。
- 城市。
- 客户类型。
- 联系方式。
- 官网或公开页面。
- 来源平台。
- 来源链接。
- 来源证据。
- 活跃度信号。
- 规模信号。
- 是否经营二手/进口车。
- 进口/二手相关性。
- 缺失信息。
- 风险阻断状态。

### 4.2 客户类型枚举

只允许输出：

- `local_dealer_secondary_dealer`
- `personal_buyer`
- `kol_auto_blogger`
- `unknown`
- `non_target`

### 4.3 联系方式规则

联系方式必须来自输入文本。

如果没有证据：

- 邮箱输出 null。
- 电话输出 null。
- WhatsApp 输出 null。
- Telegram 输出 null。
- 微信输出 null。
- 官网表单输出 null。

不得因为文本里有“Telegram”或“WhatsApp”字样就推测账号。

### 4.4 来源证据规则

每个核心判断都要提供 evidence：

- 为什么认为它是车商。
- 为什么认为它经营二手车/进口车。
- 为什么认为联系方式有效。
- 为什么标记为非目标。

证据摘录应短，不要复制整页。

### 4.5 风险阻断规则

如果 `channel_risk_level` 为 `High` 或 `Forbidden`：

- `risk_blocked` 必须为 true。
- `recommended_next_action` 必须为 `policy_review_only` 或 `manual_small_sample_only`。
- `touch_queue_allowed` 必须为 false。
- 不得输出可触达建议。

## 5. 输出示例

```json
{
  "schema_version": "poc-ai-output-v1",
  "task_type": "lead_extraction",
  "source": {
    "source_url": "https://example.ru/contact",
    "source_platform": "官网",
    "channel_risk_level": "Low",
    "search_keyword": "дилер подержанных автомобилей Москва",
    "collected_at": "2026-05-27T10:00:00+08:00",
    "operator": "AI/Agent 操作负责人"
  },
  "risk_blocked": false,
  "lead": {
    "customer_name": "Example Auto Moscow",
    "country": "Russia",
    "city": "Moscow",
    "customer_type": "local_dealer_secondary_dealer",
    "business_scope": "Used cars and imported SUVs",
    "sells_used_or_imported_cars": "yes",
    "import_used_relevance": "high",
    "activity_signal": "Website shows updated inventory and contact page",
    "scale_signal": "Multiple vehicle listings shown",
    "contacts": {
      "emails": ["sales@example.ru"],
      "phones": ["+7 999 000 0000"],
      "whatsapp": [],
      "telegram": [],
      "wechat": [],
      "website_forms": ["https://example.ru/contact"]
    },
    "official_website": "https://example.ru",
    "source_evidence": [
      {
        "claim": "dealer_identity",
        "evidence_text": "Used car dealer in Moscow",
        "source_url": "https://example.ru/contact"
      }
    ],
    "missing_fields": ["主营车型", "是否有进口车经验"]
  },
  "recommended_next_action": "send_to_grading",
  "touch_queue_allowed": false,
  "audit": {
    "model": "Unknown",
    "prompt_version": "lead-extraction-v1",
    "input_saved": true,
    "output_saved": true
  }
}
```

## 6. 人工复核要求

线索运营必须复核：

- 来源链接是否可打开。
- 联系方式是否真实来自公开页面。
- 客户类型是否合理。
- 是否存在 High/Forbidden 渠道误入。
- AI 是否编造缺失字段。

