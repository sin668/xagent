const CONTENT_TYPE_LABELS = {
  qa_entry: 'Q&A',
  email_reply_template: '邮件模板',
  compliance_phrase: '合规话术',
  vehicle_product_note: '车型说明',
  process_sop: '流程 SOP',
};

const WORKFLOW_LABELS = {
  'active:approved': '已发布',
  'draft:pending': '草稿待审',
  'draft:approved': '待 embedding',
  'deprecated:approved': '已下线',
  'disabled:rejected': '已阻断',
};

const EMBEDDING_LABELS = {
  ready: 'ready',
  pending: 'pending',
  failed: 'failed',
};

const CREATE_OR_EDIT_ROLES = new Set(['operator', 'admin', 'knowledge_admin', 'tech_admin']);
const PUBLISH_ROLES = new Set(['admin', 'knowledge_admin', 'tech_admin']);
const RETRY_EMBEDDING_ROLES = new Set(['admin', 'knowledge_admin', 'tech_admin']);

function normalizeRole(actorRole) {
  return String(actorRole || '').trim().toLowerCase();
}

function toNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function percentText(value) {
  return `${(toNumber(value) * 100).toFixed(1)}%`;
}

function statusClass(status) {
  if (status === 'active') return 'green';
  if (status === 'draft') return 'amber';
  if (status === 'deprecated') return 'blue';
  return 'red';
}

function embeddingStatusFromItem(item = {}) {
  const metadata = item.metadata_json || item.metadataJson || {};
  const explicitStatus = metadata.embedding_status || metadata.embeddingStatus;
  if (explicitStatus) return explicitStatus;
  if (item.status === 'active' && item.review_status === 'approved') return 'ready';
  if (item.status === 'draft' && item.review_status === 'approved') return 'pending';
  if (metadata.embedding_failed || metadata.embeddingFailed) return 'failed';
  return 'pending';
}

function normalizeKnowledgeItem(item = {}) {
  const contentType = item.content_type || item.contentType || 'Unknown';
  const embeddingStatus = embeddingStatusFromItem(item);
  const workflowKey = `${item.status || 'Unknown'}:${item.review_status || item.reviewStatus || 'Unknown'}`;
  return {
    id: item.id,
    collectionId: item.collection_id || item.collectionId,
    title: item.title || 'Unknown',
    body: item.body || '',
    language: item.language || 'Unknown',
    country: item.country || 'Unknown',
    status: item.status || 'Unknown',
    reviewStatus: item.review_status || item.reviewStatus || 'Unknown',
    statusClass: statusClass(item.status),
    workflowLabel: WORKFLOW_LABELS[workflowKey] || workflowKey,
    sourceRef: item.source_ref || item.sourceRef || 'Unknown',
    version: item.version || 'Unknown',
    contentType,
    contentTypeLabel: CONTENT_TYPE_LABELS[contentType] || contentType,
    businessScene: item.business_scene || item.businessScene || 'Unknown',
    riskLevel: item.risk_level || item.riskLevel || 'Unknown',
    autoReplyAllowed: Boolean(item.auto_reply_allowed ?? item.autoReplyAllowed),
    autoReplyLabel: item.auto_reply_allowed ?? item.autoReplyAllowed ? 'yes' : 'no',
    market: item.market || 'Unknown',
    tone: item.tone || 'Unknown',
    ragEligible: Boolean(item.rag_eligible ?? item.ragEligible),
    embeddingStatus,
    embeddingStatusLabel: EMBEDDING_LABELS[embeddingStatus] || embeddingStatus,
    embeddingStatusClass: embeddingStatus === 'ready' ? 'green' : embeddingStatus === 'failed' ? 'red' : 'amber',
  };
}

function normalizeFailureCase(item = {}) {
  return {
    embeddingId: item.embedding_id || item.embeddingId,
    knowledgeTitle: item.knowledge_title || item.knowledgeTitle || 'Unknown',
    embeddingModel: item.embedding_model || item.embeddingModel || 'Unknown',
    errorMessage: item.error_message || item.errorMessage || item.last_error_message || item.lastErrorMessage || '',
    retryCount: toNumber(item.retry_count ?? item.retryCount),
  };
}

export function buildKnowledgeItemsQuery({
  status,
  reviewStatus,
  language,
  contentType,
  businessScene,
  riskLevel,
  autoReplyAllowed,
  market,
  tone,
  limit = 100,
} = {}) {
  const params = new URLSearchParams();
  if (status) params.set('status', status);
  if (reviewStatus) params.set('review_status', reviewStatus);
  if (language) params.set('language', language);
  if (contentType) params.set('content_type', contentType);
  if (businessScene) params.set('business_scene', businessScene);
  if (riskLevel) params.set('risk_level', riskLevel);
  if (autoReplyAllowed !== undefined && autoReplyAllowed !== null) params.set('auto_reply_allowed', String(autoReplyAllowed));
  if (market) params.set('market', market);
  if (tone) params.set('tone', tone);
  params.set('limit', String(limit));
  return `?${params.toString()}`;
}

export function buildKnowledgeGovernanceView({
  items = {},
  embeddingMetrics = {},
  actorRole = 'operator',
} = {}) {
  const normalizedItems = Array.isArray(items.items) ? items.items.map(normalizeKnowledgeItem) : [];
  const role = normalizeRole(actorRole);
  const canCreateOrEdit = CREATE_OR_EDIT_ROLES.has(role);
  const canPublish = PUBLISH_ROLES.has(role);
  const canRetryEmbedding = RETRY_EMBEDDING_ROLES.has(role);
  const readyRate = toNumber(embeddingMetrics.ready_rate ?? embeddingMetrics.readyRate);

  return {
    summary: {
      publishedItemCount: normalizedItems.filter((item) => item.status === 'active' && item.reviewStatus === 'approved').length,
      embeddingReadyCount: toNumber(embeddingMetrics.ready_count ?? embeddingMetrics.readyCount),
      autoReplyAllowedCount: normalizedItems.filter((item) => item.autoReplyAllowed).length,
      reviewDraftCount: normalizedItems.filter((item) => item.status === 'draft' && item.reviewStatus === 'pending').length,
      embeddingReadyRate: readyRate,
      embeddingReadyRateText: percentText(readyRate),
      embeddingStatusClass: readyRate >= 0.95 ? 'green' : readyRate > 0 ? 'amber' : 'red',
      pendingEmbeddingCount: toNumber(embeddingMetrics.pending_count ?? embeddingMetrics.pendingCount),
      failedEmbeddingCount: toNumber(embeddingMetrics.failed_count ?? embeddingMetrics.failedCount),
      totalRetryCount: toNumber(embeddingMetrics.total_retry_count ?? embeddingMetrics.totalRetryCount),
    },
    tabs: [
      { label: '全部', filters: {} },
      { label: 'Q&A', filters: { contentType: 'qa_entry' } },
      { label: '邮件模板', filters: { contentType: 'email_reply_template' } },
      { label: '合规话术', filters: { contentType: 'compliance_phrase' } },
      { label: '车型说明', filters: { contentType: 'vehicle_product_note' } },
      { label: '流程 SOP', filters: { contentType: 'process_sop' } },
      { label: '待 embedding', filters: { embeddingStatus: 'pending' } },
    ],
    items: normalizedItems,
    embeddingFailures: Array.isArray(embeddingMetrics.failed_cases)
      ? embeddingMetrics.failed_cases.map(normalizeFailureCase)
      : [],
    failureReasonGroups: embeddingMetrics.failure_reason_groups || embeddingMetrics.failureReasonGroups || [],
    canCreateOrEdit,
    canPublish,
    canArchive: canPublish,
    canRetryEmbedding,
    actionEntrypoints: [
      { label: '创建草稿', enabled: canCreateOrEdit },
      { label: '提交审核', enabled: canCreateOrEdit },
      { label: '发布', enabled: canPublish },
      { label: '下线', enabled: canPublish },
      { label: '重试 embedding', enabled: canRetryEmbedding },
    ],
    ragTestPanel: {
      defaultQuery: '客户询问合作流程、可供车型和交付方式时，召回可引用知识。',
      defaultFilters: {
        language: 'ru',
        content_types: ['qa_entry', 'email_reply_template'],
        auto_send_context: false,
        limit: 5,
      },
    },
    permissionNotice: canPublish && canRetryEmbedding
      ? '当前角色可创建/编辑草稿、提交审核、发布/下线知识，并可重试失败 embedding。'
      : '当前角色可创建/编辑草稿和提交审核；发布/下线及 embedding 重试入口已按权限禁用。',
  };
}

function normalizeBaseUrl(baseUrl) {
  return String(baseUrl || '').replace(/\/$/, '');
}

async function parseJsonResponse(response, errorPrefix) {
  if (!response.ok) {
    throw new Error(`${errorPrefix}: ${response.status || 'unknown'}`);
  }
  return response.json();
}

export async function fetchKnowledgeGovernance({
  baseUrl = '',
  actorRole = 'operator',
  filters = {},
  fetcher = globalThis.fetch,
} = {}) {
  if (typeof fetcher !== 'function') {
    throw new Error('fetcher is required to load knowledge governance');
  }
  const normalizedBaseUrl = normalizeBaseUrl(baseUrl);
  const itemsResponse = await fetcher(`${normalizedBaseUrl}/knowledge/items${buildKnowledgeItemsQuery(filters)}`);
  const metricsResponse = await fetcher(`${normalizedBaseUrl}/knowledge/embeddings/metrics`);
  return {
    actorRole,
    items: await parseJsonResponse(itemsResponse, 'Failed to load knowledge items'),
    embeddingMetrics: await parseJsonResponse(metricsResponse, 'Failed to load knowledge embedding metrics'),
  };
}

export async function createKnowledgeItemDraft({
  baseUrl = '',
  payload,
  fetcher = globalThis.fetch,
} = {}) {
  const response = await fetcher(`${normalizeBaseUrl(baseUrl)}/knowledge/items`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload || {}),
  });
  return parseJsonResponse(response, 'Failed to create knowledge item draft');
}

export async function triggerKnowledgeAction({
  baseUrl = '',
  itemId,
  embeddingId,
  action,
  actor = 'admin',
  actorRole = 'operator',
  reviewNote = '',
  fetcher = globalThis.fetch,
} = {}) {
  const normalizedBaseUrl = normalizeBaseUrl(baseUrl);
  if (action === 'retry_embedding') {
    const response = await fetcher(`${normalizedBaseUrl}/knowledge/embeddings/${embeddingId}/retry`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    return parseJsonResponse(response, 'Failed to retry knowledge embedding');
  }

  const allowedActions = new Set(['submit-review', 'publish', 'archive', 'block', 'activate-retrieval']);
  if (!allowedActions.has(action)) {
    throw new Error(`Unsupported knowledge action: ${action}`);
  }
  const response = await fetcher(`${normalizedBaseUrl}/knowledge/items/${itemId}/${action}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      actor,
      actor_role: actorRole,
      review_note: reviewNote,
    }),
  });
  return parseJsonResponse(response, `Failed to ${action} knowledge item`);
}

export async function runKnowledgeRagTest({
  baseUrl = '',
  payload,
  fetcher = globalThis.fetch,
} = {}) {
  const response = await fetcher(`${normalizeBaseUrl(baseUrl)}/knowledge/rag-test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload || {}),
  });
  return parseJsonResponse(response, 'Failed to run knowledge rag test');
}
