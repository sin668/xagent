const RISK_LABELS = {
  overdue: '已超时',
  compliance_waiting: '合规等待',
  warning: '临近超时',
  on_track: '正常',
};

function toNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function percentText(value) {
  return `${Math.round(toNumber(value) * 100)}%`;
}

function normalizeQueueItem(item = {}) {
  const grade = item.grade || 'Unknown';
  const slaHours = toNumber(item.sla_hours ?? item.slaHours);
  const riskStatus = item.risk_status || item.riskStatus || 'on_track';

  return {
    customerName: item.customer_name || item.customerName || 'Unknown',
    grade,
    owner: item.owner || 'Unknown',
    status: item.status || 'unknown',
    slaHours,
    slaLabel: `${grade}级 ${slaHours}小时`,
    waitingHours: toNumber(item.waiting_hours ?? item.waitingHours),
    waitingText: `${Math.round(toNumber(item.waiting_hours ?? item.waitingHours))}小时`,
    riskStatus,
    riskLabel: RISK_LABELS[riskStatus] || '待确认',
    complianceStatus: item.compliance_status || item.complianceStatus || null,
    nextAction: item.next_action || item.nextAction || '按 SLA 跟进',
  };
}

export function isSlaRisk(item = {}) {
  return ['overdue', 'compliance_waiting', 'warning'].includes(item.riskStatus);
}

export function buildOutreachSlaDashboardView(payload = {}) {
  const summary = payload.summary || {};
  const queue = Array.isArray(payload.queue) ? payload.queue.map(normalizeQueueItem) : [];

  return {
    summary: {
      sentCount: toNumber(summary.sent_count ?? summary.sentCount),
      repliedCount: toNumber(summary.replied_count ?? summary.repliedCount),
      responseRate: toNumber(summary.response_rate ?? summary.responseRate),
      responseRateText: percentText(summary.response_rate ?? summary.responseRate),
      pendingCount: toNumber(summary.pending_count ?? summary.pendingCount),
      overdueCount: toNumber(summary.overdue_count ?? summary.overdueCount),
      complianceWaitingCount: toNumber(summary.compliance_waiting_count ?? summary.complianceWaitingCount),
      slaRiskCount: toNumber(summary.sla_risk_count ?? summary.slaRiskCount),
    },
    queue,
    riskQueue: queue.filter(isSlaRisk),
  };
}

export function buildOutreachSlaQuery({ owner, grade, channel } = {}) {
  const params = new URLSearchParams();
  if (owner) {
    params.set('owner', owner);
  }
  if (grade) {
    params.set('grade', grade);
  }
  if (channel) {
    params.set('channel', channel);
  }
  const query = params.toString();
  return query ? `?${query}` : '';
}

export async function fetchOutreachSlaDashboard({
  baseUrl = '',
  owner,
  grade,
  channel,
  fetcher = globalThis.fetch,
} = {}) {
  if (typeof fetcher !== 'function') {
    throw new Error('fetcher is required to load outreach SLA dashboard data');
  }

  const normalizedBaseUrl = String(baseUrl || '').replace(/\/$/, '');
  const response = await fetcher(`${normalizedBaseUrl}/dashboard/outreach-sla${buildOutreachSlaQuery({ owner, grade, channel })}`);
  if (!response.ok) {
    throw new Error(`Failed to load outreach SLA dashboard: ${response.status || 'unknown'}`);
  }
  return response.json();
}
