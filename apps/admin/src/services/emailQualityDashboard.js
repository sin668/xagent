const EXPECTED_EMAIL_PROMPT_TASK_TYPES = [
  'EMAIL_REPLY_DRAFT',
  'EMAIL_REPLY_AUTO_SEND_CHECK',
  'EMAIL_REPLY_SEND',
];

function toNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function percentText(value) {
  return `${(toNumber(value) * 100).toFixed(1)}%`;
}

function rate(numerator, denominator) {
  const base = toNumber(denominator);
  return base > 0 ? toNumber(numerator) / base : 0;
}

function normalizeBaseUrl(baseUrl) {
  return String(baseUrl || '').replace(/\/$/, '');
}

function routeFromDraft(draft = {}) {
  const decision = draft.auto_send_decision_json || draft.autoSendDecisionJson || {};
  if (decision.route) return decision.route;
  if (draft.status === 'blocked') return 'block';
  if (draft.auto_send_allowed ?? draft.autoSendAllowed) return 'auto_send';
  return 'hold_for_manual_review';
}

function hardBlockReasons(draft = {}) {
  const decision = draft.auto_send_decision_json || draft.autoSendDecisionJson || {};
  const reasons = decision.hard_block_reasons || decision.hardBlockReasons || [];
  return Array.isArray(reasons) ? reasons.map((item) => String(item).toLowerCase()) : [];
}

function sendAttempts(draft = {}) {
  return Array.isArray(draft.send_attempts || draft.sendAttempts)
    ? (draft.send_attempts || draft.sendAttempts)
    : [];
}

function isDncBlocked(draft = {}) {
  const reasonText = [
    ...hardBlockReasons(draft),
    draft.manual_review_reason || draft.manualReviewReason || '',
  ].join(' ').toLowerCase();
  return routeFromDraft(draft) === 'block' && reasonText.includes('dnc');
}

function isDeGradeBlocked(draft = {}) {
  const reasonText = [
    ...hardBlockReasons(draft),
    draft.manual_review_reason || draft.manualReviewReason || '',
  ].join(' ').toLowerCase();
  return routeFromDraft(draft) === 'block' && (reasonText.includes('d/e') || reasonText.includes('watch') || reasonText.includes('invalid'));
}

function promptCoverage(promptTemplates = {}) {
  const items = Array.isArray(promptTemplates.items) ? promptTemplates.items : [];
  const covered = new Set(
    items
      .filter((item) => item.status === 'active' && Boolean(item.is_default ?? item.isDefault))
      .map((item) => item.task_type || item.taskType),
  );
  return rate(
    EXPECTED_EMAIL_PROMPT_TASK_TYPES.filter((taskType) => covered.has(taskType)).length,
    EXPECTED_EMAIL_PROMPT_TASK_TYPES.length,
  );
}

function aiGenerationSuccessRate(aiAudit = {}) {
  const logs = Array.isArray(aiAudit.ai_audit_logs || aiAudit.aiAuditLogs)
    ? (aiAudit.ai_audit_logs || aiAudit.aiAuditLogs)
    : [];
  const emailReplyLogs = logs.filter((item) => {
    const taskType = String(item.task_type || item.taskType || '').toUpperCase();
    return taskType === 'EMAIL_REPLY' || taskType.startsWith('EMAIL_REPLY_') || taskType === '';
  });
  const denominator = emailReplyLogs.length;
  const successCount = emailReplyLogs.filter((item) => item.status === 'succeeded' && !Boolean(item.risk_blocked ?? item.riskBlocked)).length;
  return rate(successCount, denominator);
}

function normalizeKnowledgeEffect(item = {}) {
  return {
    title: item.knowledge_title || item.knowledgeTitle || item.title || 'Unknown',
    retrievalCount: toNumber(item.retrieval_count ?? item.retrievalCount),
    adoptionRateText: percentText(item.adoption_rate ?? item.adoptionRate),
    averageEditDistanceRatio: item.average_edit_distance_ratio ?? item.averageEditDistanceRatio ?? null,
    suggestion: item.suggest_deprecate || item.suggestDeprecate ? '复盘' : '保留',
    suggestionClass: item.suggest_deprecate || item.suggestDeprecate ? 'amber' : 'green',
  };
}

async function parseJsonResponse(response, errorPrefix) {
  if (!response.ok) {
    throw new Error(`${errorPrefix}: ${response.status || 'unknown'}`);
  }
  return response.json();
}

export function buildEmailQualityDashboardView({
  promptTemplates = {},
  embeddingMetrics = {},
  aiAudit = {},
  drafts = {},
  riskEvents = {},
  knowledgeQuality = {},
} = {}) {
  const draftItems = Array.isArray(drafts.items) ? drafts.items : [];
  const autoSendDrafts = draftItems.filter((draft) => routeFromDraft(draft) === 'auto_send' || Boolean(draft.auto_send_allowed ?? draft.autoSendAllowed));
  const sentAttempts = draftItems.flatMap(sendAttempts).filter((attempt) => ['sent', 'failed', 'bounced'].includes(attempt.status));
  const sentSuccessAttempts = sentAttempts.filter((attempt) => attempt.status === 'sent');
  const bouncedAttempts = sentAttempts.filter((attempt) => attempt.status === 'bounced');
  const successfulDrafts = draftItems.filter((draft) => sendAttempts(draft).some((attempt) => attempt.status === 'sent'));
  const adoptedManualDrafts = successfulDrafts.filter((draft) => Boolean(draft.manual_review_required ?? draft.manualReviewRequired));
  const riskSummary = riskEvents.summary || {};
  const openRiskCount = toNumber(riskSummary.open_count ?? riskSummary.openCount ?? riskSummary.total_count ?? riskSummary.totalCount);
  const dncBlockedCount = draftItems.filter(isDncBlocked).length;
  const deGradeBlockedCount = draftItems.filter(isDeGradeBlocked).length;
  const promptCoverageRate = promptCoverage(promptTemplates);
  const embeddingReadyRate = toNumber(embeddingMetrics.ready_rate ?? embeddingMetrics.readyRate);
  const aiSuccessRate = aiGenerationSuccessRate(aiAudit);
  const manualAdoptionRate = rate(adoptedManualDrafts.length, successfulDrafts.length);
  const autoSendSuccessRate = rate(
    autoSendDrafts.filter((draft) => sendAttempts(draft).some((attempt) => attempt.status === 'sent')).length,
    autoSendDrafts.length,
  );
  const bounceRate = rate(bouncedAttempts.length, sentAttempts.length);
  const hardRiskClear = openRiskCount === 0;
  const qualityReady = promptCoverageRate >= 1 && embeddingReadyRate >= 0.95 && aiSuccessRate >= 0.9 && bounceRate <= 0.02;
  const goCandidate = hardRiskClear && qualityReady;
  const reasons = [];
  if (promptCoverageRate < 1) reasons.push('Prompt 覆盖率未达到 100%');
  if (embeddingReadyRate < 0.95) reasons.push('embedding ready 率低于 95%');
  if (aiSuccessRate < 0.9) reasons.push('AI 生成成功率低于 90%');
  if (bounceRate > 0.02) reasons.push('退信率高于 2%');
  if (openRiskCount > 0) reasons.push('存在未关闭风险事件');

  return {
    summary: {
      promptCoverageRate,
      promptCoverageText: percentText(promptCoverageRate),
      embeddingReadyRate,
      embeddingReadyText: percentText(embeddingReadyRate),
      aiGenerationSuccessRate: aiSuccessRate,
      aiGenerationSuccessText: percentText(aiSuccessRate),
      manualAdoptionRate,
      manualAdoptionText: percentText(manualAdoptionRate),
      autoSendSuccessRate,
      autoSendSuccessText: percentText(autoSendSuccessRate),
      bounceRate,
      bounceRateText: percentText(bounceRate),
    },
    riskGate: {
      dncBlockedCount,
      deGradeBlockedCount,
      riskEventCount: openRiskCount,
      bounceCount: bouncedAttempts.length,
      statusLabel: hardRiskClear ? '硬风险门禁通过' : '需暂停自动发送',
      statusClass: hardRiskClear ? 'green' : 'red',
      riskEvents: riskEvents.items || [],
    },
    knowledgeEffects: Array.isArray(knowledgeQuality.items)
      ? knowledgeQuality.items.map(normalizeKnowledgeEffect)
      : [],
    goNoGo: {
      statusLabel: goCandidate ? 'Go 候选' : openRiskCount > 0 ? '暂停' : '重跑 PoC',
      statusClass: goCandidate ? 'green' : openRiskCount > 0 ? 'red' : 'amber',
      reasons,
    },
    flowNodes: [
      { title: 'Prompt', metricText: `覆盖率 ${percentText(promptCoverageRate)}`, className: promptCoverageRate >= 1 ? 'green' : 'amber' },
      { title: '向量', metricText: `ready ${percentText(embeddingReadyRate)}`, className: embeddingReadyRate >= 0.95 ? 'green' : 'amber' },
      { title: 'Agent', metricText: `生成成功 ${percentText(aiSuccessRate)}`, className: aiSuccessRate >= 0.9 ? 'green' : 'amber' },
      { title: '风险', metricText: `风险事件 ${openRiskCount}`, className: hardRiskClear ? 'green' : 'red' },
      { title: '业务', metricText: `退信 ${percentText(bounceRate)}`, className: bounceRate <= 0.02 ? 'green' : 'amber' },
    ],
  };
}

export async function fetchEmailQualityDashboard({
  baseUrl = '',
  fetcher = globalThis.fetch,
} = {}) {
  if (typeof fetcher !== 'function') {
    throw new Error('fetcher is required to load email quality dashboard');
  }
  const normalizedBaseUrl = normalizeBaseUrl(baseUrl);
  const [promptResponse, embeddingResponse, aiAuditResponse, draftsResponse, riskEventsResponse] = await Promise.all([
    fetcher(`${normalizedBaseUrl}/llm-prompt-templates`),
    fetcher(`${normalizedBaseUrl}/knowledge/embeddings/metrics`),
    fetcher(`${normalizedBaseUrl}/sync/audit-dashboard`),
    fetcher(`${normalizedBaseUrl}/email-reply/drafts?limit=500`),
    fetcher(`${normalizedBaseUrl}/dashboard/risk-events`),
  ]);
  return {
    promptTemplates: await parseJsonResponse(promptResponse, 'Failed to load prompt templates'),
    embeddingMetrics: await parseJsonResponse(embeddingResponse, 'Failed to load embedding metrics'),
    aiAudit: await parseJsonResponse(aiAuditResponse, 'Failed to load AI audit metrics'),
    drafts: await parseJsonResponse(draftsResponse, 'Failed to load email reply drafts'),
    riskEvents: await parseJsonResponse(riskEventsResponse, 'Failed to load risk events'),
  };
}
