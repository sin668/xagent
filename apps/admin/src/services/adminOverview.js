const RISK_LABELS = {
  Low: '低风险',
  Medium: '中风险',
  High: '高风险',
  Forbidden: '禁用',
};

const STATUS_LABELS = {
  active: '可观察',
  researching: '研究中',
  blocked: '已阻断',
};

function toNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function percentText(value) {
  return `${Math.round(toNumber(value) * 100)}%`;
}

function normalizeChannel(item = {}) {
  const bGradeCount = toNumber(item.b_grade_count ?? item.bGradeCount);
  const cGradeCount = toNumber(item.c_grade_count ?? item.cGradeCount);
  const bcGradeCount = toNumber(item.bc_grade_count ?? item.bcGradeCount ?? bGradeCount + cGradeCount);
  const riskLevel = item.risk_level || item.riskLevel || 'Unknown';
  const riskStatus = item.risk_status || item.riskStatus || 'active';

  return {
    channelName: item.channel_name || item.channelName || 'unknown',
    displayName: item.display_name || item.displayName || item.channel_name || 'Unknown',
    riskLevel,
    riskLabel: RISK_LABELS[riskLevel] || `${riskLevel} 风险`,
    riskStatus,
    statusLabel: STATUS_LABELS[riskStatus] || '待确认',
    investmentRecommendation: item.investment_recommendation || item.investmentRecommendation || 'watch',
    candidateCount: toNumber(item.candidate_count ?? item.candidateCount),
    bGradeCount,
    cGradeCount,
    bcGradeCount,
    bcText: `B ${bGradeCount} / C ${cGradeCount}`,
    invalidRateText: percentText(item.invalid_rate ?? item.invalidRate),
  };
}

function normalizeQueueItem(item = {}) {
  return {
    customerId: item.customer_id || item.customerId || '',
    customerName: item.customer_name || item.customerName || 'Unknown',
    grade: item.grade || 'Unknown',
    status: item.status || 'unknown',
    owner: item.owner || '未分配',
    updatedAt: item.updated_at || item.updatedAt || '',
  };
}

function normalizeQueue(queue = {}) {
  const items = Array.isArray(queue.items) ? queue.items.map(normalizeQueueItem) : [];
  return {
    count: toNumber(queue.count ?? items.length),
    items,
  };
}

function normalizeRiskEvent(item = {}) {
  const reason = item.risk_block_reason || item.riskBlockReason || '';
  return {
    id: item.id || '',
    customerId: item.customer_id || item.customerId || null,
    taskType: item.task_type || item.taskType || 'unknown',
    modelName: item.model_name || item.modelName || 'Unknown',
    promptVersion: item.prompt_version || item.promptVersion || 'Unknown',
    sourceUrl: item.source_url || item.sourceUrl || null,
    riskBlocked: Boolean(item.risk_blocked ?? item.riskBlocked),
    riskBlockReason: reason,
    reasonVisible: reason.length > 0,
    executedAt: item.executed_at || item.executedAt || '',
  };
}

export function queueCount(queue = {}) {
  return toNumber(queue.count);
}

export function buildAdminOverviewView(payload = {}) {
  const summary = payload.summary || {};
  const channelOutputs = Array.isArray(payload.channel_outputs)
    ? payload.channel_outputs.map(normalizeChannel)
    : [];
  const teamQueues = payload.team_queues || {};
  const operations = normalizeQueue(teamQueues.operations);
  const customerService = normalizeQueue(teamQueues.customer_service ?? teamQueues.customerService);
  const sales = normalizeQueue(teamQueues.sales);
  const riskEvents = Array.isArray(payload.risk_events) ? payload.risk_events.map(normalizeRiskEvent) : [];
  const blockedTasks = Array.isArray(payload.blocked_tasks) ? payload.blocked_tasks.map(normalizeRiskEvent) : [];

  return {
    summary: {
      candidateCount: toNumber(summary.candidate_count ?? summary.candidateCount),
      bGradeCount: toNumber(summary.b_grade_count ?? summary.bGradeCount),
      cGradeCount: toNumber(summary.c_grade_count ?? summary.cGradeCount),
      bcGradeCount: toNumber(summary.bc_grade_count ?? summary.bcGradeCount),
      responseRate: toNumber(summary.response_rate ?? summary.responseRate),
      responseRateText: percentText(summary.response_rate ?? summary.responseRate),
      slaRiskCount: toNumber(summary.sla_risk_count ?? summary.slaRiskCount),
    },
    channelOutputs,
    teamQueues: {
      operations,
      customerService,
      sales,
    },
    queueSummaryText: `运营 ${operations.count} / 客服 ${customerService.count} / 销售 ${sales.count}`,
    riskEvents,
    blockedTasks,
  };
}

export async function fetchAdminOverview({
  baseUrl = '',
  fetcher = globalThis.fetch,
} = {}) {
  if (typeof fetcher !== 'function') {
    throw new Error('fetcher is required to load admin overview');
  }

  const normalizedBaseUrl = String(baseUrl || '').replace(/\/$/, '');
  const response = await fetcher(`${normalizedBaseUrl}/dashboard/admin-overview`);
  if (!response.ok) {
    throw new Error(`Failed to load admin overview: ${response.status || 'unknown'}`);
  }
  return response.json();
}
