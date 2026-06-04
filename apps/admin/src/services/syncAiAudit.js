const SYNC_STATUS_LABELS = {
  success: '成功',
  partial: '部分成功',
  failed: '失败',
};

const AI_STATUS_LABELS = {
  succeeded: '已存证',
  blocked: '已阻断',
};

function toNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function normalizeSyncLog(item = {}) {
  const status = item.status || 'unknown';
  return {
    id: item.id || '',
    sourceName: item.source_name || item.sourceName || 'feishu',
    objectName: item.object_name || item.objectName || 'Unknown',
    status,
    statusLabel: SYNC_STATUS_LABELS[status] || '未知',
    successCount: toNumber(item.success_count ?? item.successCount),
    failureCount: toNumber(item.failure_count ?? item.failureCount),
    errorSummary: item.error_summary || item.errorSummary || '',
    startedAt: item.started_at || item.startedAt || '',
    finishedAt: item.finished_at || item.finishedAt || '',
  };
}

function normalizeAiAuditLog(item = {}) {
  const status = item.status || (item.risk_blocked || item.riskBlocked ? 'blocked' : 'succeeded');
  return {
    id: item.id || '',
    customerId: item.customer_id || item.customerId || null,
    taskType: item.task_type || item.taskType || 'unknown',
    modelName: item.model_name || item.modelName || 'Unknown',
    promptVersion: item.prompt_version || item.promptVersion || 'Unknown',
    sourceUrl: item.source_url || item.sourceUrl || '',
    status,
    statusLabel: AI_STATUS_LABELS[status] || '未知',
    risk: item.risk || 'normal',
    riskBlocked: Boolean(item.risk_blocked ?? item.riskBlocked),
    riskBlockReason: item.risk_block_reason || item.riskBlockReason || '',
    executedAt: item.executed_at || item.executedAt || '',
  };
}

export function buildSyncAiAuditView(payload = {}) {
  const summary = payload.summary || {};
  const syncLogs = Array.isArray(payload.sync_logs) ? payload.sync_logs.map(normalizeSyncLog) : [];
  const aiAuditLogs = Array.isArray(payload.ai_audit_logs) ? payload.ai_audit_logs.map(normalizeAiAuditLog) : [];

  return {
    summary: {
      latestSyncAt: summary.latest_sync_at || summary.latestSyncAt || null,
      syncSuccessCount: toNumber(summary.sync_success_count ?? summary.syncSuccessCount),
      syncFailureCount: toNumber(summary.sync_failure_count ?? summary.syncFailureCount),
      aiTaskCount: toNumber(summary.ai_task_count ?? summary.aiTaskCount),
      aiBlockedCount: toNumber(summary.ai_blocked_count ?? summary.aiBlockedCount),
    },
    syncLogs,
    aiAuditLogs,
    blockedAiLogs: aiAuditLogs.filter((item) => item.riskBlocked),
    failedSyncLogs: syncLogs.filter((item) => item.failureCount > 0 || item.status === 'failed'),
  };
}

export function buildSyncAiAuditQuery({ taskType, status } = {}) {
  const params = new URLSearchParams();
  if (taskType) {
    params.set('task_type', taskType);
  }
  if (status) {
    params.set('status', status);
  }
  const query = params.toString();
  return query ? `?${query}` : '';
}

export async function fetchSyncAiAuditDashboard({
  baseUrl = '',
  taskType,
  status,
  fetcher = globalThis.fetch,
} = {}) {
  if (typeof fetcher !== 'function') {
    throw new Error('fetcher is required to load sync AI audit dashboard');
  }

  const normalizedBaseUrl = String(baseUrl || '').replace(/\/$/, '');
  const response = await fetcher(`${normalizedBaseUrl}/sync/audit-dashboard${buildSyncAiAuditQuery({ taskType, status })}`);
  if (!response.ok) {
    throw new Error(`Failed to load sync AI audit dashboard: ${response.status || 'unknown'}`);
  }
  return response.json();
}
