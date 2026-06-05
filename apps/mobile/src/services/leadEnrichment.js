function normalizeGrade(value) {
  return String(value || '').trim().toUpperCase();
}

function normalizeStatus(value) {
  return String(value || '').trim().toLowerCase();
}

function normalizeRisk(value) {
  return String(value || '').trim().toLowerCase();
}

function formatConfidence(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return 'Unknown';
  }
  return `${Math.round(numeric * 100)}%`;
}

function displayValue(value) {
  if (value == null || value === '') {
    return 'Unknown';
  }
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }
  return String(value);
}

function reviewStatusLabel(status) {
  const normalized = normalizeStatus(status);
  if (normalized === 'accepted') {
    return '已采纳';
  }
  if (normalized === 'rejected') {
    return '已拒绝';
  }
  return '待采纳';
}

function resultStatusLabel(status) {
  const normalized = normalizeStatus(status);
  if (normalized === 'completed' || normalized === 'succeeded') {
    return '已完成';
  }
  if (normalized === 'failed') {
    return '失败';
  }
  if (normalized === 'running') {
    return '运行中';
  }
  return '待执行';
}

function enrichmentTypeLabel(type) {
  const normalized = normalizeStatus(type);
  if (normalized === 'manual_enrichment' || normalized === 'manual_supplement') {
    return '人工补录';
  }
  return 'AI 深挖';
}

export function canTriggerDeepEnrichment(lead = {}) {
  const grade = normalizeGrade(lead.grade || lead.recommendedGrade || lead.recommended_grade);
  const status = normalizeStatus(lead.status || lead.reviewStatus || lead.review_status);
  const risk = normalizeRisk(lead.riskLevel || lead.sourceRiskLevel || lead.source_risk_level);

  if (lead.doNotContact || lead.do_not_contact) {
    return { allowed: false, reason: '勿扰线索不允许深挖' };
  }
  if (risk === 'forbidden') {
    return { allowed: false, reason: 'Forbidden 来源不允许深挖' };
  }
  if (status === 'watch' || grade === 'WATCH' || grade === 'D') {
    return { allowed: false, reason: 'Watch 线索不允许深挖' };
  }
  if (status === 'invalid' || grade === 'INVALID' || grade === 'E') {
    return { allowed: false, reason: 'Invalid 线索不允许深挖' };
  }

  return { allowed: true, reason: '' };
}

export function buildLeadEnrichmentViewModel({ lead = {}, resultsPayload = {} } = {}) {
  const gate = canTriggerDeepEnrichment(lead);
  const results = (resultsPayload.items || []).map((result) => ({
    id: result.id,
    typeLabel: enrichmentTypeLabel(result.enrichment_type || result.enrichmentType),
    statusLabel: resultStatusLabel(result.status),
    triggeredBy: result.triggered_by || result.triggeredBy || 'Unknown',
    recommendedAction: result.recommended_action || result.recommendedAction || 'Unknown',
    confidenceText: formatConfidence(result.confidence_score ?? result.confidenceScore),
    evidenceLinks: result.evidence_links || result.evidenceLinks || [],
    missingFields: result.missing_fields || result.missingFields || [],
    createdAt: result.created_at || result.createdAt || 'Unknown',
    fieldCandidates: result.field_candidates || result.fieldCandidates || [],
  }));
  const fieldCandidates = results.flatMap((result) =>
    result.fieldCandidates.map((candidate) => ({
      id: candidate.id,
      resultId: result.id,
      fieldName: candidate.field_name || candidate.fieldName || 'Unknown',
      candidateValue: displayValue(candidate.candidate_value ?? candidate.candidateValue),
      sourceType: candidate.source_type || candidate.sourceType || 'Unknown',
      sourceUrl: candidate.source_url || candidate.sourceUrl || '',
      evidenceNote: candidate.evidence_note || candidate.evidenceNote || 'Unknown',
      confidenceText: formatConfidence(candidate.confidence_score ?? candidate.confidenceScore),
      reviewStatus: normalizeStatus(candidate.review_status || candidate.reviewStatus || 'pending'),
      reviewStatusLabel: reviewStatusLabel(candidate.review_status || candidate.reviewStatus),
      acceptedBy: candidate.accepted_by || candidate.acceptedBy || '',
      rejectedReason: candidate.rejected_reason || candidate.rejectedReason || '',
    })),
  );

  return {
    canTriggerDeepEnrichment: gate.allowed,
    blockReason: gate.reason,
    triggerButtonLabel: gate.allowed ? '深挖线索' : gate.reason || '不可深挖',
    emptyLabel: fieldCandidates.length ? '' : '暂无补全候选',
    results,
    fieldCandidates,
  };
}

export function buildCreateEnrichmentRunPayload({ actor, manualKeywords = [], allowedChannelScope = [], note = null } = {}) {
  return {
    triggered_by: actor || '当前用户',
    manual_keywords: manualKeywords,
    allowed_channel_scope: allowedChannelScope,
    note,
  };
}

export function buildAcceptFieldCandidatePayload({ actor, candidateValue, sourceType, sourceUrl, evidenceNote, confidenceScore } = {}) {
  const payload = {
    accepted_by: actor || '当前用户',
  };
  if (candidateValue !== undefined) payload.candidate_value = candidateValue;
  if (sourceType !== undefined) payload.source_type = sourceType;
  if (sourceUrl !== undefined) payload.source_url = sourceUrl;
  if (evidenceNote !== undefined) payload.evidence_note = evidenceNote;
  if (confidenceScore !== undefined) payload.confidence_score = confidenceScore;
  return payload;
}

export function buildRejectFieldCandidatePayload({ reason } = {}) {
  return {
    rejected_reason: reason || '人工拒绝该候选字段',
  };
}

export function buildManualEnrichmentPayload({ operator, note = null, fields = [] } = {}) {
  return {
    operator: operator || '当前用户',
    note,
    fields: fields.map((field) => ({
      field_name: field.fieldName || field.field_name || 'Unknown',
      candidate_value: field.candidateValue ?? field.candidate_value ?? 'Unknown',
      source_type: field.sourceType || field.source_type || 'manual_public_info',
      source_url: field.sourceUrl ?? field.source_url ?? null,
      evidence_note: field.evidenceNote || field.evidence_note || '人工补录',
      confidence_score: field.confidenceScore ?? field.confidence_score ?? null,
    })),
  };
}

export function createLeadEnrichmentService({ apiClient }) {
  return {
    createEnrichmentRun(leadId, options = {}) {
      return apiClient.post(
        `/staging-leads/${encodeURIComponent(leadId)}/enrichment-runs`,
        buildCreateEnrichmentRunPayload(options),
      );
    },
    listEnrichmentResults(leadId) {
      return apiClient.get(`/staging-leads/${encodeURIComponent(leadId)}/enrichment-results`);
    },
    acceptFieldCandidate(candidateId, options = {}) {
      return apiClient.patch(
        `/lead-enrichment-field-candidates/${encodeURIComponent(candidateId)}/accept`,
        buildAcceptFieldCandidatePayload(options),
      );
    },
    rejectFieldCandidate(candidateId, options = {}) {
      return apiClient.patch(
        `/lead-enrichment-field-candidates/${encodeURIComponent(candidateId)}/reject`,
        buildRejectFieldCandidatePayload(options),
      );
    },
    createManualEnrichment(leadId, options = {}) {
      return apiClient.post(
        `/staging-leads/${encodeURIComponent(leadId)}/manual-enrichment`,
        buildManualEnrichmentPayload(options),
      );
    },
  };
}
