function toNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function percentText(value) {
  return `${Math.round(toNumber(value) * 100)}%`;
}

function normalizeBaseUrl(baseUrl) {
  return String(baseUrl || '').replace(/\/$/, '');
}

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

export function buildRuntimeOverviewView({
  overview = {},
  phase2 = {},
  phase3 = {},
} = {}) {
  const overviewSummary = overview.summary || {};
  const overviewChannels = safeArray(overview.channel_outputs);
  const overviewQueues = overview.team_queues || {};
  const phase2Summary = phase2.summary || {};
  const phase2RiskEvents = safeArray(phase2.high_forbidden_risk_events);
  const phase3CustomerAcceptance = phase3.customer_acceptance || {};
  const phase3Enrichment = phase3.enrichment || {};
  const phase3Cleanup = phase3.cleanup || {};
  const phase3Risk = phase3.risk || {};

  const sourceCandidateCount = toNumber(phase2Summary.source_candidate_count ?? phase2Summary.sourceCandidateCount);
  const stagingLeadCount = toNumber(phase3Enrichment.staging_lead_count ?? phase3Enrichment.stagingLeadCount);
  const promotedCustomerCount = toNumber(
    phase3CustomerAcceptance.promoted_customer_count ?? phase3CustomerAcceptance.promotedCustomerCount,
  );
  const cleanedLeadCount = toNumber(phase3Cleanup.executed_count ?? phase3Cleanup.executedCount);
  const responseRate = toNumber(overviewSummary.response_rate ?? overviewSummary.responseRate);
  const customerServiceCount = toNumber(overviewQueues.customer_service?.count);
  const salesCount = toNumber(overviewQueues.sales?.count);
  const operationsCount = toNumber(overviewQueues.operations?.count);
  const succeededExtractionCount = toNumber(phase2Summary.auto_extraction_count ?? phase2Summary.autoExtractionCount);
  const reviewBacklogCount = toNumber(phase2Summary.review_backlog_count ?? phase2Summary.reviewBacklogCount);
  const llmCostTotal = toNumber(phase2Summary.llm_cost_total ?? phase2Summary.llmCostTotal);
  const llmCostText = `¥${llmCostTotal.toFixed(2)}`;
  const riskViolationCount = toNumber(phase3Risk.risk_violation_count ?? phase3Risk.riskViolationCount);

  return {
    hero: {
      title: '运行总览',
      subtitle: '真实 API 聚合看板：来源发现、线索沉淀、客户晋级与清洗治理',
      statusText: riskViolationCount > 0 ? '需关注' : '运行中',
      statusClass: riskViolationCount > 0 ? 'amber' : 'green',
    },
    summaryCards: [
      { key: 'source_urls', label: '线索来源URL', value: sourceCandidateCount, accentClass: '' },
      { key: 'staging_leads', label: '线索池线索', value: stagingLeadCount, accentClass: 'text-blue' },
      { key: 'promoted_customers', label: '晋级客户', value: promotedCustomerCount, accentClass: 'text-green' },
      { key: 'cleaned_leads', label: '被清洗线索', value: cleanedLeadCount, accentClass: 'text-red' },
    ],
    channels: overviewChannels.map((channel) => ({
      key: channel.channel_name || channel.display_name || 'unknown',
      displayName: channel.display_name || channel.channel_name || 'Unknown',
      riskLevel: channel.risk_level || 'Unknown',
      candidateCount: toNumber(channel.candidate_count),
      coreCount: toNumber(channel.bc_grade_count ?? channel.b_grade_count) + toNumber(channel.c_grade_count),
      statusText: channel.risk_status || 'active',
      riskClass:
        channel.risk_level === 'Low'
          ? 'green'
          : channel.risk_level === 'Medium'
            ? 'amber'
            : channel.risk_level === 'High'
              ? 'red'
              : 'blue',
    })),
    funnel: [
      { key: 'candidate_urls', label: 'candidate_urls', value: sourceCandidateCount, width: 100, barClass: 'bar-blue' },
      {
        key: 'staging_leads',
        label: 'staging_leads',
        value: stagingLeadCount,
        width: sourceCandidateCount > 0 ? Math.round((stagingLeadCount / sourceCandidateCount) * 100) : 0,
        barClass: 'bar-teal',
      },
      {
        key: 'core_customers',
        label: 'core_customers',
        value: promotedCustomerCount,
        width: sourceCandidateCount > 0 ? Math.round((promotedCustomerCount / sourceCandidateCount) * 100) : 0,
        barClass: 'bar-green',
      },
      {
        key: 'human_review_queue',
        label: 'human_review_queue',
        value: reviewBacklogCount,
        width: sourceCandidateCount > 0 ? Math.round((reviewBacklogCount / sourceCandidateCount) * 100) : 0,
        barClass: 'bar-amber',
      },
    ],
    insights: [
      {
        key: 'guardrail',
        title: '硬闸门',
        body:
          phase2.guardrail
          || 'High/Forbidden 不进入自动链路，勿扰强阻断，C 级客户必须合规复核。',
      },
      {
        key: 'ai_quality',
        title: 'AI 质量',
        body: `${succeededExtractionCount} 次自动抽取成功，回复率 ${percentText(responseRate)}，LLM 成本 ${llmCostText}。`,
      },
      {
        key: 'team_load',
        title: '团队承接',
        body: `运营 ${operationsCount}，客服 ${customerServiceCount}，销售 ${salesCount}；晋级客户 ${promotedCustomerCount}。`,
      },
    ],
    riskEvents: phase2RiskEvents,
  };
}

export async function fetchRuntimeOverview({
  baseUrl = '',
  fetcher = globalThis.fetch,
} = {}) {
  if (typeof fetcher !== 'function') {
    throw new Error('fetcher is required to load runtime overview');
  }

  const normalizedBaseUrl = normalizeBaseUrl(baseUrl);
  const [overviewResponse, phase2Response, phase3Response] = await Promise.all([
    fetcher(`${normalizedBaseUrl}/dashboard/admin-overview`),
    fetcher(`${normalizedBaseUrl}/dashboard/phase2`),
    fetcher(`${normalizedBaseUrl}/phase3-dashboard/metrics`),
  ]);

  if (!overviewResponse.ok) {
    throw new Error(`Failed to load runtime overview admin overview: ${overviewResponse.status || 'unknown'}`);
  }
  if (!phase2Response.ok) {
    throw new Error(`Failed to load runtime overview phase2 dashboard: ${phase2Response.status || 'unknown'}`);
  }
  if (!phase3Response.ok) {
    throw new Error(`Failed to load runtime overview phase3 dashboard: ${phase3Response.status || 'unknown'}`);
  }

  const [overview, phase2, phase3] = await Promise.all([
    overviewResponse.json(),
    phase2Response.json(),
    phase3Response.json(),
  ]);

  return { overview, phase2, phase3 };
}
