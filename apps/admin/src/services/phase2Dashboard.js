const RISK_LABELS = {
  Low: '低风险',
  Medium: '中风险',
  High: '高风险',
  Forbidden: '禁用',
};

const STATUS_LABELS = {
  queued: '排队中',
  running: '运行中',
  succeeded: '成功',
  failed: '失败',
  retry_pending: '待重试',
  manual_review: '人工复核',
  blocked: '已阻断',
  open: '待处理',
};

function toNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function moneyText(value, currency = 'CNY') {
  const amount = toNumber(value).toFixed(2);
  if (currency === 'CNY' || currency === 'RMB') {
    return `¥${amount}`;
  }
  return `${currency} ${amount}`;
}

function percentOf(current, limit) {
  const currentNumber = toNumber(current);
  const limitNumber = toNumber(limit);
  if (limitNumber <= 0) {
    return 0;
  }
  return Math.min(100, Math.round((currentNumber / limitNumber) * 100));
}

function riskClass(riskLevel) {
  if (riskLevel === 'Low') return 'green';
  if (riskLevel === 'Medium') return 'amber';
  return 'red';
}

function normalizeTaskRun(item = {}, currency = 'CNY') {
  const taskType = item.task_type || item.taskType || 'UNKNOWN';
  const status = item.status || 'unknown';
  const costCurrency = item.cost_currency || item.costCurrency || currency;
  return {
    runId: item.agent_task_run_id || item.agentTaskRunId || '',
    taskType,
    status,
    statusLabel: STATUS_LABELS[status] || status,
    statusClass: status === 'succeeded' ? 'green' : status === 'failed' ? 'red' : 'amber',
    provider: item.model || item.provider || 'Unknown',
    promptVersion: item.prompt_version || item.promptVersion || 'Unknown',
    outputText: `${toNumber(item.total_tokens ?? item.totalTokens)} tokens`,
    costAmount: toNumber(item.cost_amount ?? item.costAmount),
    costCurrency,
    costText: moneyText(item.cost_amount ?? item.costAmount, costCurrency),
  };
}

function normalizeRiskEvent(item = {}) {
  const riskLevel = item.risk_level || item.riskLevel || 'Unknown';
  return {
    id: item.id || '',
    taskId: item.task_id || item.taskId || null,
    channel: item.channel || 'Unknown',
    riskLevel,
    riskLabel: RISK_LABELS[riskLevel] || riskLevel,
    severity: item.severity || 'unknown',
    resolutionStatus: item.resolution_status || item.resolutionStatus || 'open',
    eventType: item.event_type || item.eventType || 'unknown',
    blockReason: item.block_reason || item.blockReason || '未填写阻断原因',
    pauseSuggested: Boolean(item.pause_suggested ?? item.pauseSuggested),
    createdAt: item.created_at || item.createdAt || '',
    highlightClass: riskClass(riskLevel),
  };
}

export function buildPhase2DashboardQuery({ channelPrefix } = {}) {
  const params = new URLSearchParams();
  if (channelPrefix) {
    params.set('channel_prefix', channelPrefix);
  }
  const query = params.toString();
  return query ? `?${query}` : '';
}

export function buildPhase2DashboardView(payload = {}) {
  const summary = payload.summary || {};
  const reviewBacklog = payload.review_backlog || {};
  const extractionStatus = payload.extraction_status_distribution || {};
  const failureReasons = Array.isArray(payload.failure_reasons) ? payload.failure_reasons : [];
  const llmCosts = payload.llm_costs || {};
  const currency = llmCosts.currency || 'CNY';
  const sourceCandidateCount = toNumber(summary.source_candidate_count ?? summary.sourceCandidateCount);
  const extractableSourceCount = toNumber(summary.auto_extraction_count ?? summary.autoExtractionCount);
  const highReviewBacklogCount = toNumber(reviewBacklog.high_risk_review ?? reviewBacklog.highRiskReview);
  const failedTaskCount = toNumber(summary.failed_task_count ?? summary.failedTaskCount);
  const agentTaskCount = toNumber(summary.agent_task_count ?? summary.agentTaskCount);
  const schemaFailureCount = failureReasons
    .filter((item) => String(item.reason || '').includes('schema'))
    .reduce((total, item) => total + toNumber(item.count), 0);
  const schemaFailureRate = agentTaskCount > 0 ? schemaFailureCount / agentTaskCount : 0;
  const llmTaskRuns = Array.isArray(llmCosts.items)
    ? llmCosts.items.map((item) => normalizeTaskRun(item, currency))
    : [];
  const highForbiddenRiskEvents = Array.isArray(payload.high_forbidden_risk_events)
    ? payload.high_forbidden_risk_events.map(normalizeRiskEvent)
    : [];

  return {
    summary: {
      sourceCandidateCount,
      extractableSourceCount,
      highReviewBacklogCount,
      reviewBacklogCount: toNumber(summary.review_backlog_count ?? summary.reviewBacklogCount),
      failedTaskCount,
      agentTaskCount,
      llmCostTotal: toNumber(summary.llm_cost_total ?? summary.llmCostTotal ?? llmCosts.total_cost),
      llmCostText: moneyText(summary.llm_cost_total ?? summary.llmCostTotal ?? llmCosts.total_cost, currency),
      riskEventCount: toNumber(summary.risk_event_count ?? summary.riskEventCount),
      highForbiddenRiskEventCount: toNumber(
        summary.high_forbidden_risk_event_count ?? summary.highForbiddenRiskEventCount,
      ),
    },
    taskFlow: [
      {
        title: 'Source Discovery',
        description: '自动发现候选来源，写入来源候选池并保留证据。',
        metricText: `${sourceCandidateCount} 来源候选`,
      },
      {
        title: 'Candidate Pool',
        description: '来源进入 lead_source_candidates，等待风险规则和人工复核。',
        metricText: `${toNumber(reviewBacklog.pending)} 待审`,
      },
      {
        title: 'Human Review',
        description: 'High 人工审核，Forbidden 阻断，不进入自动抽取。',
        metricText: `${highReviewBacklogCount} High 待审`,
      },
      {
        title: 'Extraction',
        description: 'approved 来源进入 LEAD_EXTRACTION 任务流。',
        metricText: `${extractableSourceCount} 可抽取`,
      },
      {
        title: 'Staging/Core',
        description: '抽取后进入 staging 校验、去重、复核，再进入 core。',
        metricText: `${toNumber(extractionStatus.succeeded)} 已成功`,
      },
    ],
    pauseThresholds: {
      failedTasks: {
        label: '任务失败数',
        current: failedTaskCount,
        limit: 3,
        percent: percentOf(failedTaskCount, 3),
        className: failedTaskCount >= 3 ? 'red' : 'amber',
      },
      highReviewBacklog: {
        label: 'High 审核积压',
        current: highReviewBacklogCount,
        limit: 50,
        percent: percentOf(highReviewBacklogCount, 50),
        className: highReviewBacklogCount >= 50 ? 'red' : 'amber',
      },
      schemaFailureRate: {
        label: 'schema 失败率',
        current: schemaFailureRate,
        limit: 0.05,
        percent: Math.min(100, Math.round(schemaFailureRate * 100)),
        text: `${(schemaFailureRate * 100).toFixed(1)}%`,
        className: schemaFailureRate >= 0.05 ? 'red' : 'green',
      },
    },
    llmTaskRuns,
    failureReasons,
    highForbiddenRiskEvents,
    guardrail: payload.guardrail || '第二阶段运行看板必须遵守风险边界和审计要求。',
  };
}

export async function fetchPhase2Dashboard({
  baseUrl = '',
  channelPrefix,
  fetcher = globalThis.fetch,
} = {}) {
  if (typeof fetcher !== 'function') {
    throw new Error('fetcher is required to load phase2 dashboard');
  }

  const normalizedBaseUrl = String(baseUrl || '').replace(/\/$/, '');
  const response = await fetcher(`${normalizedBaseUrl}/dashboard/phase2${buildPhase2DashboardQuery({ channelPrefix })}`);
  if (!response.ok) {
    throw new Error(`Failed to load phase2 dashboard: ${response.status || 'unknown'}`);
  }
  return response.json();
}
