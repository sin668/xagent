function toNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function moneyText(value, currency = '$') {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return 'N/A';
  }
  return `${currency}${Math.round(toNumber(value) * 100) / 100}`;
}

export function roiCanOverrideCompliance() {
  return false;
}

export function buildRoiMetricsView(payload = {}) {
  const summary = payload.summary || {};

  return {
    summary: {
      totalCost: toNumber(summary.total_cost ?? summary.totalCost),
      totalCostText: moneyText(summary.total_cost ?? summary.totalCost),
      laborCostText: moneyText(summary.labor_cost ?? summary.laborCost),
      aiApiCostText: moneyText(summary.ai_api_cost ?? summary.aiApiCost),
      toolCostText: moneyText(summary.tool_cost ?? summary.toolCost),
      effectiveLeadCount: toNumber(summary.effective_lead_count ?? summary.effectiveLeadCount),
      replyCount: toNumber(summary.reply_count ?? summary.replyCount),
      salesOpportunityCount: toNumber(summary.sales_opportunity_count ?? summary.salesOpportunityCount),
      costPerEffectiveLeadText: moneyText(summary.cost_per_effective_lead ?? summary.costPerEffectiveLead),
      costPerReplyText: moneyText(summary.cost_per_reply ?? summary.costPerReply),
      costPerSalesOpportunityText: moneyText(summary.cost_per_sales_opportunity ?? summary.costPerSalesOpportunity),
    },
    guardrail: payload.compliance_guardrail || 'ROI 不能作为绕过合规限制的理由。',
    complianceOverrideAllowed: roiCanOverrideCompliance(),
  };
}

export function buildRoiMetricsQuery({ channel, dateFrom, dateTo } = {}) {
  const params = new URLSearchParams();
  if (channel) {
    params.set('channel', channel);
  }
  if (dateFrom) {
    params.set('date_from', dateFrom);
  }
  if (dateTo) {
    params.set('date_to', dateTo);
  }
  const query = params.toString();
  return query ? `?${query}` : '';
}

export async function fetchRoiMetrics({
  baseUrl = '',
  channel,
  dateFrom,
  dateTo,
  fetcher = globalThis.fetch,
} = {}) {
  if (typeof fetcher !== 'function') {
    throw new Error('fetcher is required to load ROI metrics');
  }

  const normalizedBaseUrl = String(baseUrl || '').replace(/\/$/, '');
  const response = await fetcher(`${normalizedBaseUrl}/dashboard/roi-metrics${buildRoiMetricsQuery({ channel, dateFrom, dateTo })}`);
  if (!response.ok) {
    throw new Error(`Failed to load ROI metrics: ${response.status || 'unknown'}`);
  }
  return response.json();
}
