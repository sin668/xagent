const STATUS_LABELS = {
  active: 'active',
  draft: 'draft',
  paused: 'paused',
  archived: 'archived',
};

const VALIDATION_LABELS = {
  validation_passed: '通过',
  validation_failed: '失败',
  validation_pending: '待校验',
};

const PROMPT_GOVERNANCE_ROLES = new Set(['admin', 'tech_admin']);

function statusClass(status) {
  if (status === 'active') return 'green';
  if (status === 'draft' || status === 'paused') return 'amber';
  return 'red';
}

function compactJson(value) {
  return JSON.stringify(value || {}, null, 2);
}

function promptInputText(template = {}) {
  const safeTemplate = template && typeof template === 'object' ? template : {};
  const sections = [];
  if (safeTemplate.systemPromptPreview) {
    sections.push(`System Prompt\n${safeTemplate.systemPromptPreview}`);
  }
  if (safeTemplate.userPromptPreview) {
    sections.push(`User Prompt Template\n${safeTemplate.userPromptPreview}`);
  }
  return sections.join('\n\n') || '暂无 Prompt 输入内容。';
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

function validationStatusLabel(status) {
  return VALIDATION_LABELS[status] || '未校验';
}

function validationErrorsText(errors) {
  if (!errors || typeof errors !== 'object') return '';
  return Object.entries(errors)
    .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(', ') : String(value)}`)
    .join(' / ');
}

function normalizeGovernanceTemplate(item = {}) {
  const template = normalizeTemplate(item);
  const sourceHash = item.source_file_hash || item.sourceFileHash || '';
  const validationStatus = item.validation_status || item.validationStatus || '';
  const validationErrors = item.validation_errors_json || item.validationErrorsJson;
  return {
    ...template,
    sourceFilePath: item.source_file_path || item.sourceFilePath || 'Unknown',
    sourceFileHash: sourceHash || 'Unknown',
    sourceHashShort: sourceHash ? sourceHash.slice(0, 8) : 'Unknown',
    migrationBatchId: item.migration_batch_id || item.migrationBatchId || 'Unknown',
    validationStatus,
    validationStatusLabel: validationStatusLabel(validationStatus),
    validationErrorsText: validationErrorsText(validationErrors),
    publishedBy: item.published_by || item.publishedBy || 'Unknown',
    publishedAt: item.published_at || item.publishedAt || '',
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

export function buildLlmGovernanceView({ health = {}, templates = {}, selectedTemplateId = '' } = {}) {
  const models = health.models && typeof health.models === 'object' ? health.models : {};
  const modelSummary = Object.entries(models)
    .map(([key, value]) => `${key}: ${value || 'Unknown'}`)
    .join(' / ');
  const promptTemplates = Array.isArray(templates.items) ? templates.items.map(normalizeTemplate) : [];
  const defaultTemplates = promptTemplates.filter((template) => template.isDefault);
  const selectedTemplate = promptTemplates.find((template) => template.id === selectedTemplateId)
    || defaultTemplates[0]
    || promptTemplates[0]
    || null;
  const schemaPreview = selectedTemplate || {
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
    promptWorkbench: {
      selectedTemplateId: selectedTemplate?.id || '',
      title: selectedTemplate?.name || '暂无默认 Prompt',
      version: selectedTemplate?.version || '',
      promptInputText: promptInputText(selectedTemplate),
      schemaOutputText: selectedTemplate?.schemaText || '{}',
    },
    fallbackBoundaries: [
      { condition: '网络/超时/限流', decisionLabel: '可 fallback', className: 'blue' },
      { condition: 'schema 校验失败', decisionLabel: '不 fallback', className: 'red' },
      { condition: '疑似编造来源', decisionLabel: '阻断', className: 'red' },
      { condition: '命中 Forbidden', decisionLabel: '阻断', className: 'red' },
    ],
    readOnlyNotice: '第二阶段只读：普通运营不可创建、编辑或删除 prompt template。',
  };
}

export function buildPromptGovernanceView({
  templates = {},
  actorRole = 'operator',
  expectedTaskTypes = [
    'SOURCE_DISCOVERY',
    'LEAD_EXTRACTION',
    'LEAD_GRADING',
    'EMAIL_REPLY_DRAFT',
    'EMAIL_REPLY_AUTO_SEND_CHECK',
    'EMAIL_REPLY_KNOWLEDGE_RETRIEVAL',
    'EMAIL_REPLY_SEND',
  ],
} = {}) {
  const promptTemplates = Array.isArray(templates.items)
    ? templates.items.map(normalizeGovernanceTemplate)
    : [];
  const coveredTaskTypes = new Set(promptTemplates.map((template) => template.taskType));
  const coverageRate = expectedTaskTypes.length > 0
    ? coveredTaskTypes.size / expectedTaskTypes.length
    : 0;
  const draftTemplates = promptTemplates.filter((template) => template.status === 'draft');
  const schemaErrorCount = promptTemplates.filter((template) => template.validationStatus === 'validation_failed').length;
  const canGovern = PROMPT_GOVERNANCE_ROLES.has(String(actorRole || '').trim().toLowerCase());

  return {
    summary: {
      importedPromptCount: promptTemplates.length,
      activeDefaultCount: promptTemplates.filter((template) => template.status === 'active' && template.isDefault).length,
      draftValidationPendingCount: draftTemplates.filter((template) => template.validationStatus !== 'validation_passed').length,
      schemaErrorCount,
      coverageRate,
      coverageRateText: `${Math.round(coverageRate * 100)}%`,
      coverageStatusClass: coverageRate >= 1 ? 'green' : coverageRate > 0 ? 'amber' : 'red',
    },
    templates: promptTemplates,
    canEditDraft: canGovern,
    canPublish: canGovern,
    canRollback: canGovern,
    actionEntrypoints: [
      { label: '校验草稿', enabled: canGovern },
      { label: '发布版本', enabled: canGovern },
      { label: '回滚版本', enabled: canGovern },
    ],
    permissionNotice: canGovern
      ? '当前角色可校验草稿、发布版本和创建回滚草稿，所有操作写入审计。'
      : '当前角色只能查看 Prompt 入库治理，编辑、发布和回滚入口已禁用。',
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

export async function fetchPromptGovernance({
  baseUrl = '',
  actorRole = 'operator',
  fetcher = globalThis.fetch,
} = {}) {
  if (typeof fetcher !== 'function') {
    throw new Error('fetcher is required to load prompt governance');
  }
  const normalizedBaseUrl = String(baseUrl || '').replace(/\/$/, '');
  const response = await fetcher(`${normalizedBaseUrl}/llm-prompt-templates`);
  if (!response.ok) {
    throw new Error(`Failed to load prompt templates: ${response.status || 'unknown'}`);
  }
  return {
    actorRole,
    templates: await response.json(),
  };
}
