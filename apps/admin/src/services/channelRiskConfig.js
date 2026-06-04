const RISK_LABELS = {
  Low: '低风险',
  Medium: '中风险',
  High: '高风险',
  Forbidden: '禁用',
};

const STATUS_LABELS = {
  executable: '自动任务可执行',
  blocked: '自动任务阻断',
};

function normalizeRule(item = {}) {
  const riskLevel = item.risk_level || item.riskLevel || 'Unknown';
  const aiProcessingAllowed = Boolean(item.ai_processing_allowed ?? item.aiProcessingAllowed);
  const collectionAllowed = Boolean(item.collection_allowed ?? item.collectionAllowed);
  const executable = aiProcessingAllowed && !['High', 'Forbidden'].includes(riskLevel);
  const blockReason = executable
    ? ''
    : 'High/Forbidden 渠道或未允许 AI 处理的渠道，自动任务必须阻断并记录原因。';

  return {
    channelName: item.channel_name || item.channelName || 'unknown',
    channelType: item.channel_type || item.channelType || '未分类',
    riskLevel,
    riskLabel: RISK_LABELS[riskLevel] || `${riskLevel} 风险`,
    collectionAllowed,
    aiProcessingAllowed,
    allowedActions: item.allowed_actions || item.allowedActions || '',
    forbiddenActions: item.forbidden_actions || item.forbiddenActions || '',
    policySourceUrl: item.policy_source_url || item.policySourceUrl || '',
    notes: item.notes || '',
    updatedBy: item.updated_by || item.updatedBy || '未记录',
    updatedAt: item.updated_at || item.updatedAt || '',
    status: executable ? 'executable' : 'blocked',
    statusLabel: executable ? STATUS_LABELS.executable : STATUS_LABELS.blocked,
    blockReason,
  };
}

export function isExecutableRiskRule(rule = {}) {
  return Boolean(rule.aiProcessingAllowed) && !['High', 'Forbidden'].includes(rule.riskLevel);
}

export function buildChannelRiskConfigView(payload = {}) {
  const rules = Array.isArray(payload.items) ? payload.items.map(normalizeRule) : [];
  return {
    rules,
    blockedRules: rules.filter((rule) => !isExecutableRiskRule(rule)),
    editableRules: rules,
  };
}

export function buildChannelRiskConfigPayload(form = {}) {
  return {
    channel_type: form.channelType,
    risk_level: form.riskLevel,
    allowed_actions: form.allowedActions,
    forbidden_actions: form.forbiddenActions,
    policy_source_url: form.policySourceUrl || null,
    notes: form.notes || null,
    collection_allowed: Boolean(form.collectionAllowed),
    updated_by: form.updatedBy || 'unknown',
  };
}

export async function fetchChannelRiskRules({
  baseUrl = '',
  fetcher = globalThis.fetch,
} = {}) {
  if (typeof fetcher !== 'function') {
    throw new Error('fetcher is required to load channel risk rules');
  }

  const normalizedBaseUrl = String(baseUrl || '').replace(/\/$/, '');
  const response = await fetcher(`${normalizedBaseUrl}/channel-risks`);
  if (!response.ok) {
    throw new Error(`Failed to load channel risk rules: ${response.status || 'unknown'}`);
  }
  return response.json();
}

export async function updateChannelRiskRule({
  baseUrl = '',
  channelName,
  form,
  fetcher = globalThis.fetch,
} = {}) {
  if (!channelName) {
    throw new Error('channelName is required to update channel risk rule');
  }
  if (typeof fetcher !== 'function') {
    throw new Error('fetcher is required to update channel risk rule');
  }

  const normalizedBaseUrl = String(baseUrl || '').replace(/\/$/, '');
  const response = await fetcher(`${normalizedBaseUrl}/channel-risks/${encodeURIComponent(channelName)}`, {
    method: 'PUT',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(buildChannelRiskConfigPayload(form)),
  });
  if (!response.ok) {
    throw new Error(`Failed to update channel risk rule: ${response.status || 'unknown'}`);
  }
  return response.json();
}
