const REVIEW_ROLES = new Set(['operator', 'admin', 'sales', 'customer_service', 'compliance']);
const COMPLIANCE_ROLES = new Set(['operator', 'admin', 'compliance']);

const DECISION_LABELS = {
  auto_send: { label: '自动候选', className: 'green' },
  hold_for_manual_review: { label: '人工确认', className: 'amber' },
  block: { label: '硬拦截', className: 'red' },
};

const STATUS_LABELS = {
  drafted: '待审核',
  manual_review: '人工确认',
  compliance_review: '合规复核',
  rejected: '已拒绝',
  blocked: '已阻断',
  sent: '已发送',
  marked_sent: '已标记发送',
};

function normalizeRole(actorRole) {
  return String(actorRole || '').trim().toLowerCase();
}

function normalizeBaseUrl(baseUrl) {
  return String(baseUrl || '').replace(/\/$/, '');
}

function decisionFromDraft(draft = {}) {
  const summaryDecision = draft.auto_send_decision || draft.autoSendDecision;
  if (summaryDecision === 'auto_send_allowed') return 'auto_send';
  if (summaryDecision === 'manual_review') return 'hold_for_manual_review';
  if (summaryDecision === 'blocked') return 'block';
  const decision = draft.auto_send_decision_json || draft.autoSendDecisionJson || {};
  if (decision.route) return decision.route;
  if (draft.status === 'blocked') return 'block';
  if (draft.manual_review_required ?? draft.manualReviewRequired) return 'hold_for_manual_review';
  if (draft.auto_send_allowed ?? draft.autoSendAllowed) return 'auto_send';
  return 'hold_for_manual_review';
}

function hardBlockReasons(draft = {}) {
  const rootReasons = draft.hard_block_reasons || draft.hardBlockReasons || [];
  if (Array.isArray(rootReasons) && rootReasons.length > 0) return rootReasons;
  const decision = draft.auto_send_decision_json || draft.autoSendDecisionJson || {};
  const reasons = decision.hard_block_reasons || decision.hardBlockReasons || [];
  return Array.isArray(reasons) ? reasons : [];
}

function normalizeKnowledgeHit(hit = {}) {
  const score = hit.similarity_score ?? hit.similarityScore;
  return {
    title: hit.title || hit.knowledge_title || hit.knowledgeTitle || 'Unknown',
    version: hit.version || hit.knowledge_version || hit.knowledgeVersion || 'Unknown',
    similarityScore: Number.isFinite(Number(score)) ? Number(score) : null,
    scoreText: Number.isFinite(Number(score)) ? Number(score).toFixed(2) : 'Unknown',
  };
}

function normalizeQueueItem(draft = {}) {
  const decision = decisionFromDraft(draft);
  const decisionConfig = DECISION_LABELS[decision] || DECISION_LABELS.hold_for_manual_review;
  return {
    id: draft.id,
    customerName: draft.customer_name || draft.customerName || 'Unknown',
    customerId: draft.customer_id || draft.customerId || null,
    messageId: draft.message_id || draft.messageId || null,
    subject: draft.subject || draft.inbound_subject || draft.inboundSubject || draft.thread_subject || draft.threadSubject || 'Unknown',
    language: draft.language || draft.reply_language || draft.replyLanguage || draft.detected_language || draft.detectedLanguage || 'Unknown',
    status: draft.status || 'Unknown',
    statusLabel: STATUS_LABELS[draft.status] || draft.status || 'Unknown',
    decision,
    decisionLabel: decisionConfig.label,
    decisionClass: decisionConfig.className,
    reason: draft.manual_review_reason || draft.manualReviewReason || hardBlockReasons(draft).join(', ') || 'Unknown',
  };
}

function normalizeSelectedDraft(draft = {}) {
  const knowledgeHitsPayload = draft.knowledge_hits_json || draft.knowledgeHitsJson || draft.knowledge_hits || draft.knowledgeHits;
  const knowledgeHits = Array.isArray(knowledgeHitsPayload)
    ? knowledgeHitsPayload.map(normalizeKnowledgeHit)
    : [];
  const replyDraft = draft.reply_draft || draft.replyDraft || {};
  const autoSendCheck = draft.auto_send_check || draft.autoSendCheck || {};
  const hardReasons = hardBlockReasons(draft);
  return {
    id: draft.id || null,
    customerContext: {
      customerName: draft.customer_name || draft.customerName || 'Unknown',
      customerId: draft.customer_id || draft.customerId || null,
      recentOutreachHistory: draft.recent_outreach_history || draft.recentOutreachHistory || [],
      vehicleIntentSummary: draft.vehicle_intent_summary || draft.vehicleIntentSummary || 'Unknown',
    },
    inbound: {
      messageId: draft.message_id || draft.messageId || null,
      subject: draft.subject || draft.inbound_subject || draft.inboundSubject || draft.thread_subject || draft.threadSubject || 'Unknown',
      body: draft.inbound_body || draft.inboundBody || draft.preview || '',
      language: draft.language || draft.detected_language || draft.detectedLanguage || 'Unknown',
    },
    aiSuggestion: {
      subject: draft.ai_suggested_subject || draft.aiSuggestedSubject || replyDraft.subject || draft.subject || 'Unknown',
      body: draft.ai_suggested_body || draft.aiSuggestedBody || replyDraft.body || '',
      promptVersionLabel: draft.prompt_version || draft.promptVersion || replyDraft.prompt_version || 'Unknown',
      model: draft.model || 'Unknown',
    },
    finalReply: {
      subject: draft.final_subject || draft.finalSubject || draft.ai_suggested_subject || draft.aiSuggestedSubject || replyDraft.subject || draft.subject || 'Unknown',
      body: draft.final_body || draft.finalBody || draft.ai_suggested_body || draft.aiSuggestedBody || replyDraft.body || '',
    },
    knowledgeHits,
    risk: {
      manualReviewRequired: Boolean(draft.manual_review_required ?? draft.manualReviewRequired),
      manualReviewReason: draft.manual_review_reason || draft.manualReviewReason || '',
      autoSendAllowed: Boolean(draft.auto_send_allowed ?? draft.autoSendAllowed ?? autoSendCheck.allow_auto_send),
      route: decisionFromDraft(draft),
      hardBlockReasons: hardReasons,
      hardBlockReasonsText: hardReasons.length > 0 ? hardReasons.join(', ') : '无硬拦截',
    },
  };
}

async function parseJsonResponse(response, errorPrefix) {
  if (!response.ok) {
    throw new Error(`${errorPrefix}: ${response.status || 'unknown'}`);
  }
  return response.json();
}

export function buildEmailReplyDraftsQuery({
  status,
  decision,
  manualReviewRequired,
  autoSendAllowed,
  customerId,
  language,
  limit = 100,
} = {}) {
  const params = new URLSearchParams();
  const mappedDecision = decision
    || (status === 'manual_review' ? 'manual_review' : null)
    || (status === 'blocked' ? 'blocked' : null)
    || (autoSendAllowed === true ? 'auto_send_allowed' : null)
    || (manualReviewRequired === true ? 'manual_review' : null);
  if (mappedDecision) params.set('decision', mappedDecision);
  if (customerId) params.set('customer_id', customerId);
  if (language) params.set('language', language);
  params.set('limit', String(limit));
  return `?${params.toString()}`;
}

export function buildEmailReplyReviewView({
  drafts = {},
  actorRole = 'operator',
} = {}) {
  const draftItems = Array.isArray(drafts.items) ? drafts.items : [];
  const queue = draftItems.map(normalizeQueueItem);
  const selectedDraft = normalizeSelectedDraft(draftItems[0] || {});
  const role = normalizeRole(actorRole);
  const canReview = REVIEW_ROLES.has(role);
  const canTransferCompliance = COMPLIANCE_ROLES.has(role);

  return {
    summary: {
      pendingReplyCount: draftItems.length,
      autoSendCandidateCount: draftItems.filter((draft) => decisionFromDraft(draft) === 'auto_send').length,
      manualReviewCount: draftItems.filter((draft) => Boolean(draft.manual_review_required ?? draft.manualReviewRequired)).length,
      hardBlockedCount: draftItems.filter((draft) => decisionFromDraft(draft) === 'block').length,
    },
    queue,
    selectedDraft,
    canEditFinalBody: canReview,
    canConfirmSend: canReview,
    canReject: canReview,
    canBlock: canReview,
    canTransferCompliance,
    actionEntrypoints: [
      { label: '编辑最终正文', enabled: canReview },
      { label: '发送前检查', enabled: canReview },
      { label: '确认发送', enabled: canReview },
      { label: '标记已发送', enabled: canReview },
      { label: '拒绝', enabled: canReview },
      { label: '阻断', enabled: canReview },
      { label: '转合规', enabled: canTransferCompliance },
    ],
    permissionNotice: canReview
      ? '当前角色可编辑最终正文，并必须先调用后端发送前检查，再执行确认发送、标记已发送、拒绝、阻断或转合规。'
      : '当前角色只能查看邮件回复审核台，编辑、发送、阻断和转合规入口已禁用。',
  };
}

export async function fetchEmailReplyReview({
  baseUrl = '',
  actorRole = 'operator',
  filters = {},
  fetcher = globalThis.fetch,
} = {}) {
  if (typeof fetcher !== 'function') {
    throw new Error('fetcher is required to load email reply review');
  }
  const response = await fetcher(`${normalizeBaseUrl(baseUrl)}/email-replies${buildEmailReplyDraftsQuery(filters)}`);
  return {
    actorRole,
    drafts: await parseJsonResponse(response, 'Failed to load email reply drafts'),
  };
}

export async function updateEmailReplyFinalBody({
  baseUrl = '',
  draftId,
  finalSubject,
  finalBody,
  actor,
  fetcher = globalThis.fetch,
} = {}) {
  const response = await fetcher(`${normalizeBaseUrl(baseUrl)}/email-reply/drafts/${draftId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      final_subject: finalSubject,
      final_body: finalBody,
      actor,
    }),
  });
  return parseJsonResponse(response, 'Failed to update email reply final body');
}

export async function requestEmailSendCheck({
  baseUrl = '',
  draftId,
  actor,
  actorRole,
  fetcher = globalThis.fetch,
} = {}) {
  const response = await fetcher(`${normalizeBaseUrl(baseUrl)}/internal/email-reply/auto-send-check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      draft_id: draftId,
      actor,
      actor_role: actorRole,
    }),
  });
  return parseJsonResponse(response, 'Failed to request email send check');
}

export async function triggerEmailReplyReviewAction({
  baseUrl = '',
  draftId,
  action,
  actor,
  actorRole,
  reviewNote,
  fetcher = globalThis.fetch,
} = {}) {
  const allowedActions = new Set(['manual-send', 'mark-sent', 'reject', 'block', 'transfer-compliance']);
  if (!allowedActions.has(action)) {
    throw new Error(`Unsupported email reply review action: ${action}`);
  }
  const response = await fetcher(`${normalizeBaseUrl(baseUrl)}/email-reply/drafts/${draftId}/${action}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      actor,
      actor_role: actorRole,
      review_note: reviewNote,
      send_check_required: true,
    }),
  });
  return parseJsonResponse(response, `Failed to ${action} email reply draft`);
}
