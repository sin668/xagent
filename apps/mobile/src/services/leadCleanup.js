import { apiClient } from './apiClient.js';

function compactParams(params = {}) {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== ''),
  );
}

function buildQuery(params = {}) {
  const entries = Object.entries(compactParams(params));
  if (!entries.length) {
    return '';
  }
  return `?${new URLSearchParams(entries).toString()}`;
}

function formatConfidence(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return 'Unknown';
  }
  return `${Math.round(numeric * 100)}%`;
}

const SUGGESTION_TYPE_LABELS = {
  strong_duplicate: '强重复',
  possible_duplicate: '疑似重复',
  merge_contact_method: '归并联系方式',
  merge_source_evidence: '归并来源证据',
  restore_from_watch: '恢复 Watch',
  confirm_invalid: '确认无效',
  mark_abandoned: '放弃线索',
  needs_manual_review: '人工复核',
};

const REVIEW_STATUS_LABELS = {
  pending: '待复核',
  approved: '已通过',
  rejected: '已拒绝',
  executed: '已执行',
};

const HIGH_RISK_TYPES = new Set([
  'strong_duplicate',
  'possible_duplicate',
  'merge_contact_method',
  'merge_source_evidence',
  'restore_from_watch',
]);

function evidenceValue(evidence = {}, key, fallback = '') {
  return evidence[key] ?? evidence[String(key).replace(/[A-Z]/g, (item) => `_${item.toLowerCase()}`)] ?? fallback;
}

export function mapCleanupSuggestion(item = {}) {
  const evidence = item.evidence_json || item.evidenceJson || {};
  const suggestionType = item.suggestion_type || item.suggestionType || 'needs_manual_review';
  const reviewStatus = item.review_status || item.reviewStatus || 'pending';
  const requiresElevatedPermission = HIGH_RISK_TYPES.has(suggestionType);
  const permissionHint = requiresElevatedPermission
    ? String(evidenceValue(evidence, 'high_risk_reason', '高风险动作需要合规或管理员权限提示。'))
    : '普通清洗建议，仍需人工复核。';

  return {
    id: item.id,
    cleanupRunId: item.cleanup_run_id || item.cleanupRunId || '',
    stagingLeadId: item.staging_lead_id || item.stagingLeadId || '',
    suggestionType,
    suggestionTypeLabel: SUGGESTION_TYPE_LABELS[suggestionType] || suggestionType,
    targetLeadId: item.target_lead_id || item.targetLeadId || '',
    targetLeadName: evidenceValue(evidence, 'target_lead_name', item.target_lead_id || item.targetLeadId || 'Unknown'),
    confidenceScore: item.confidence_score ?? item.confidenceScore ?? null,
    confidenceText: formatConfidence(item.confidence_score ?? item.confidenceScore),
    reason: item.reason || 'Unknown',
    evidenceJson: evidence,
    evidenceNote: evidenceValue(evidence, 'evidence_note', item.reason || 'Unknown'),
    evidenceLinks: evidence.evidence_links || evidence.evidenceLinks || [],
    recommendedAction: item.recommended_action || item.recommendedAction || 'Unknown',
    reviewStatus,
    reviewStatusLabel: REVIEW_STATUS_LABELS[reviewStatus] || reviewStatus,
    reviewerId: item.reviewer_id || item.reviewerId || '',
    reviewedAt: item.reviewed_at || item.reviewedAt || '',
    executedBy: item.executed_by || item.executedBy || '',
    executedAt: item.executed_at || item.executedAt || '',
    executionNote: item.execution_note || item.executionNote || '',
    createdAt: item.created_at || item.createdAt || '',
    updatedAt: item.updated_at || item.updatedAt || '',
    requiresElevatedPermission,
    permissionHint,
  };
}

export function buildCleanupReviewPayload({ actor, actorRole, reviewNote } = {}) {
  return {
    actor: actor || '当前用户',
    actor_role: actorRole || 'ops',
    review_note: reviewNote || '移动端人工复核清洗建议。',
  };
}

export function buildCleanupExecutePayload({ actor, actorRole, executionNote } = {}) {
  return {
    actor: actor || '当前用户',
    actor_role: actorRole || 'ops',
    execution_note: executionNote || '移动端人工确认执行清洗建议。',
  };
}

export function createLeadCleanupService({ client = apiClient } = {}) {
  return {
    async listCleanupSuggestions(filters = {}) {
      const query = buildQuery({
        suggestion_type: filters.suggestionType,
        review_status: filters.reviewStatus,
        confidence: filters.minConfidence,
        max_confidence: filters.maxConfidence,
        lead: filters.leadId,
        limit: filters.limit,
      });
      const payload = await client.get(`/lead-cleanup/suggestions${query}`);
      return {
        items: (payload.items || []).map(mapCleanupSuggestion),
        total: Number(payload.total || 0),
      };
    },

    async approveSuggestion(suggestionId, options = {}) {
      const payload = await client.patch(
        `/lead-cleanup/suggestions/${encodeURIComponent(suggestionId)}/approve`,
        buildCleanupReviewPayload(options),
      );
      return mapCleanupSuggestion(payload);
    },

    async rejectSuggestion(suggestionId, options = {}) {
      const payload = await client.patch(
        `/lead-cleanup/suggestions/${encodeURIComponent(suggestionId)}/reject`,
        buildCleanupReviewPayload(options),
      );
      return mapCleanupSuggestion(payload);
    },

    async executeSuggestion(suggestionId, options = {}) {
      const payload = await client.post(
        `/lead-cleanup/suggestions/${encodeURIComponent(suggestionId)}/execute`,
        buildCleanupExecutePayload(options),
      );
      return mapCleanupSuggestion(payload);
    },
  };
}

export const leadCleanupService = createLeadCleanupService();
