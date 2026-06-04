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
  const investmentRecommendation = item.investment_recommendation || item.investmentRecommendation || 'watch';

  return {
    channelName: item.channel_name || item.channelName || 'unknown',
    displayName: item.display_name || item.displayName || item.channel_name || 'Unknown',
    riskLevel,
    riskLabel: RISK_LABELS[riskLevel] || `${riskLevel} 风险`,
    riskStatus,
    statusLabel: STATUS_LABELS[riskStatus] || '待确认',
    investmentRecommendation,
    candidateCount: toNumber(item.candidate_count ?? item.candidateCount),
    bGradeCount,
    cGradeCount,
    bcGradeCount,
    bcText: `B ${bGradeCount} / C ${cGradeCount}`,
    invalidCount: toNumber(item.invalid_count ?? item.invalidCount),
    invalidRate: toNumber(item.invalid_rate ?? item.invalidRate),
    invalidRateText: percentText(item.invalid_rate ?? item.invalidRate),
  };
}

export function isInvestableChannel(channel = {}) {
  return channel.investmentRecommendation !== 'blocked' && !['High', 'Forbidden'].includes(channel.riskLevel);
}

export function buildChannelDashboardView(payload = {}) {
  const summary = payload.summary || {};
  const channels = Array.isArray(payload.channels) ? payload.channels.map(normalizeChannel) : [];

  return {
    summary: {
      candidateCount: toNumber(summary.candidate_count ?? summary.candidateCount),
      bcGradeCount: toNumber(summary.bc_grade_count ?? summary.bcGradeCount),
      invalidRate: toNumber(summary.invalid_rate ?? summary.invalidRate),
      invalidRateText: percentText(summary.invalid_rate ?? summary.invalidRate),
    },
    channels,
    investableChannels: channels.filter(isInvestableChannel),
    blockedChannels: channels.filter((channel) => !isInvestableChannel(channel)),
  };
}

export function buildDateRangeQuery({ dateFrom, dateTo } = {}) {
  const params = new URLSearchParams();
  if (dateFrom) {
    params.set('date_from', dateFrom);
  }
  if (dateTo) {
    params.set('date_to', dateTo);
  }
  const query = params.toString();
  return query ? `?${query}` : '';
}

export async function fetchChannelLeadDashboard({
  baseUrl = '',
  dateFrom,
  dateTo,
  fetcher = globalThis.fetch,
} = {}) {
  if (typeof fetcher !== 'function') {
    throw new Error('fetcher is required to load channel dashboard data');
  }

  const normalizedBaseUrl = String(baseUrl || '').replace(/\/$/, '');
  const response = await fetcher(`${normalizedBaseUrl}/dashboard/channel-leads${buildDateRangeQuery({ dateFrom, dateTo })}`);
  if (!response.ok) {
    throw new Error(`Failed to load channel dashboard: ${response.status || 'unknown'}`);
  }
  return response.json();
}
