const STATUS_LABELS = {
  active: 'active',
  draft: 'draft',
  paused: 'paused',
  archived: 'archived',
};

function statusClass(status) {
  if (status === 'active') return 'green';
  if (status === 'draft' || status === 'paused') return 'amber';
  return 'red';
}

function compactJson(value) {
  return JSON.stringify(value || {}, null, 2);
}

function schemaSummary(schema = {}) {
  const required = Array.isArray(schema.required) ? schema.required : [];
  if (required.length > 0) {
    return `required: ${required.join(', ')}`;
  }
  const properties = schema.properties && typeof schema.properties === 'object'
    ? Object.keys(schema.properties)
    : [];
  return properties.length > 0 ? `properties: ${properties.join(', ')}` : 'schema: empty';
}

function normalizeTemplate(item = {}) {
  const status = item.status || 'unknown';
  return {
    id: item.id || '',
    name: item.name || 'Unknown',
    taskType: item.task_type || item.taskType || 'UNKNOWN',
    provider: item.provider || 'Unknown',
    model: item.model || 'Unknown',
    version: item.version || 'Unknown',
    status,
    statusLabel: STATUS_LABELS[status] || status,
    statusClass: statusClass(status),
    isDefault: Boolean(item.is_default ?? item.isDefault),
    defaultLabel: item.is_default ?? item.isDefault ? 'yes' : 'no',
    createdBy: item.created_by || item.createdBy || 'Unknown',
    updatedAt: item.updated_at || item.updatedAt || '',
    schemaSummary: schemaSummary(item.output_schema_json || item.outputSchemaJson),
    schemaText: compactJson(item.output_schema_json || item.outputSchemaJson),
    systemPromptPreview: item.system_prompt || item.systemPrompt || '',
    userPromptPreview: item.user_prompt_template || item.userPromptTemplate || '',
  };
}

export function buildPromptTemplateQuery({ taskType, status, isDefault } = {}) {
  const params = new URLSearchParams();
  if (taskType) params.set('task_type', taskType);
  if (status) params.set('status', status);
  if (typeof isDefault === 'boolean') params.set('is_default', String(isDefault));
  const query = params.toString();
  return query ? `?${query}` : '';
}

export function buildLlmGovernanceView({ health = {}, templates = {} } = {}) {
  const models = health.models && typeof health.models === 'object' ? health.models : {};
  const modelSummary = Object.entries(models)
    .map(([key, value]) => `${key}: ${value || 'Unknown'}`)
    .join(' / ');
  const promptTemplates = Array.isArray(templates.items) ? templates.items.map(normalizeTemplate) : [];
  const defaultTemplates = promptTemplates.filter((template) => template.isDefault);
  const schemaPreview = defaultTemplates[0] || promptTemplates[0] || {
    name: '暂无默认 Prompt',
    version: '',
    schemaText: '{}',
  };

  return {
    providerHealth: {
      providerName: health.provider || 'Unknown',
      statusLabel: health.configuration_complete ? 'Health OK' : '配置未完成',
      statusClass: health.configuration_complete ? 'green' : 'amber',
      baseUrlConfigured: Boolean(health.base_url_configured ?? health.baseUrlConfigured),
      apiKeyConfigured: Boolean(health.api_key_configured ?? health.apiKeyConfigured),
      apiKeyVisible: false,
      modelSummary,
      models,
    },
    promptTemplates,
    defaultTemplates,
    schemaPreview,
    fallbackBoundaries: [
      { condition: '网络/超时/限流', decisionLabel: '可 fallback', className: 'blue' },
      { condition: 'schema 校验失败', decisionLabel: '不 fallback', className: 'red' },
      { condition: '疑似编造来源', decisionLabel: '阻断', className: 'red' },
      { condition: '命中 Forbidden', decisionLabel: '阻断', className: 'red' },
    ],
    readOnlyNotice: '第二阶段只读：普通运营不可创建、编辑或删除 prompt template。',
  };
}

export async function fetchLlmGovernance({
  baseUrl = '',
  filters,
  fetcher = globalThis.fetch,
} = {}) {
  if (typeof fetcher !== 'function') {
    throw new Error('fetcher is required to load llm governance');
  }

  const normalizedBaseUrl = String(baseUrl || '').replace(/\/$/, '');
  const [healthResponse, templatesResponse] = await Promise.all([
    fetcher(`${normalizedBaseUrl}/llm-health`),
    fetcher(`${normalizedBaseUrl}/llm-prompt-templates${buildPromptTemplateQuery(filters)}`),
  ]);

  if (!healthResponse.ok) {
    throw new Error(`Failed to load llm health: ${healthResponse.status || 'unknown'}`);
  }
  if (!templatesResponse.ok) {
    throw new Error(`Failed to load prompt templates: ${templatesResponse.status || 'unknown'}`);
  }

  return {
    health: await healthResponse.json(),
    templates: await templatesResponse.json(),
  };
}
