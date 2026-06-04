import { apiClient } from './apiClient.js';

function compactParams(params = {}) {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== ''),
  );
}

function buildQuery(params = {}) {
  const entries = Object.entries(compactParams(params));
  if (entries.length === 0) {
    return '';
  }
  return `?${new URLSearchParams(entries).toString()}`;
}

function mapLlmOutputSummary(summary = {}) {
  return {
    taskType: summary.task_type || summary.taskType || 'Unknown',
    country: summary.country || 'Unknown',
    city: summary.city || 'Unknown',
    channelStrategy: summary.channel_strategy || summary.channelStrategy || 'Unknown',
    candidateCount: Number(summary.candidate_count ?? summary.candidateCount ?? 0),
    blockedCount: Number(summary.blocked_count ?? summary.blockedCount ?? 0),
  };
}

export function mapSourceCandidate(candidate = {}) {
  return {
    id: candidate.id,
    sourceUrl: candidate.source_url || candidate.sourceUrl || '',
    normalizedDomain: candidate.normalized_domain || candidate.normalizedDomain || '',
    platform: candidate.platform || 'other',
    channelName: candidate.channel_name || candidate.channelName || 'Unknown',
    country: candidate.country || 'Unknown',
    city: candidate.city || 'Unknown',
    riskLevel: candidate.risk_level || candidate.riskLevel || 'Unknown',
    reviewStatus: candidate.review_status || candidate.reviewStatus || 'pending',
    approvedForExtraction: Boolean(candidate.approved_for_extraction ?? candidate.approvedForExtraction),
    reviewerId: candidate.reviewer_id || candidate.reviewerId || '',
    reviewNote: candidate.review_note || candidate.reviewNote || '',
    reviewedAt: candidate.reviewed_at || candidate.reviewedAt || '',
    discoveryMethod: candidate.discovery_method || candidate.discoveryMethod || 'Unknown',
    discoveryQuery: candidate.discovery_query || candidate.discoveryQuery || '',
    discoveryReason: candidate.discovery_reason || candidate.discoveryReason || 'Unknown',
    evidenceNote: candidate.evidence_note || candidate.evidenceNote || '',
    evidenceLinks: candidate.evidence_links || candidate.evidenceLinks || [],
    llmProvider: candidate.llm_provider || candidate.llmProvider || '',
    llmModel: candidate.llm_model || candidate.llmModel || '',
    llmOutputJson: candidate.llm_output_json || candidate.llmOutputJson || null,
    llmOutputSummary: mapLlmOutputSummary(candidate.llm_output_summary || candidate.llmOutputSummary || {}),
    confidenceScore: candidate.confidence_score ?? candidate.confidenceScore ?? null,
    extractionStatus: candidate.extraction_status || candidate.extractionStatus || 'pending',
    retryCount: Number(candidate.retry_count ?? candidate.retryCount ?? 0),
    dedupeKey: candidate.dedupe_key || candidate.dedupeKey || '',
    duplicateOfId: candidate.duplicate_of_id || candidate.duplicateOfId || null,
    isDuplicate: Boolean(candidate.is_duplicate ?? candidate.isDuplicate),
    createdByTaskRunId: candidate.created_by_task_run_id || candidate.createdByTaskRunId || null,
    createdAt: candidate.created_at || candidate.createdAt || '',
    updatedAt: candidate.updated_at || candidate.updatedAt || '',
    auditTaskRunId: candidate.audit_task_run_id || candidate.auditTaskRunId || null,
  };
}

export function createSourceCandidatesService({ client = apiClient } = {}) {
  return {
    async listSourceCandidates(filters = {}) {
      const query = buildQuery({
        risk_level: filters.riskLevel,
        review_status: filters.reviewStatus,
        country: filters.country,
        city: filters.city,
        platform: filters.platform,
        channel_name: filters.channelName,
        extraction_status: filters.extractionStatus,
        limit: filters.limit,
        offset: filters.offset,
      });
      const payload = await client.get(`/lead-source-candidates${query}`);
      return {
        items: (payload.items || []).map(mapSourceCandidate),
        total: Number(payload.total || 0),
        limit: payload.limit ?? filters.limit ?? null,
        offset: Number(payload.offset || 0),
      };
    },

    async getSourceCandidate(candidateId) {
      const payload = await client.get(`/lead-source-candidates/${encodeURIComponent(candidateId)}`);
      return mapSourceCandidate(payload);
    },

    async reviewSourceCandidate(candidateId, { action, reviewerId, reviewNote }) {
      const payload = await client.post(`/lead-source-candidates/${encodeURIComponent(candidateId)}/review-actions`, {
        action,
        reviewer_id: reviewerId,
        review_note: reviewNote,
      });
      return mapSourceCandidate(payload);
    },
  };
}

export const sourceCandidatesService = createSourceCandidatesService();

