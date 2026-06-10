import { apiClient } from './apiClient.js';

const GRADE_MAP = {
  A: 'A',
  A级: 'A',
  B: 'B',
  B级: 'B',
  C: 'C',
  C级: 'C',
  D: 'Watch',
  D级: 'Watch',
  WATCH: 'Watch',
  Watch: 'Watch',
  E: 'Invalid',
  E级: 'Invalid',
  INVALID: 'Invalid',
  Invalid: 'Invalid',
};

export function normalizeManualGrade(grade) {
  const raw = String(grade || '').trim();
  return GRADE_MAP[raw] || GRADE_MAP[raw.toUpperCase()] || raw;
}

export function buildGradeUpdatePayload({ grade, reason, actor } = {}) {
  return {
    actor: actor || '当前用户',
    reason: reason || '移动端人工调整线索等级。',
    recommended_grade: normalizeManualGrade(grade),
  };
}

export function createStagingLeadActionsService({ client = apiClient } = {}) {
  return {
    updateGrade(leadId, options = {}) {
      return client.patch(
        `/staging-leads/${encodeURIComponent(leadId)}/grade`,
        buildGradeUpdatePayload(options),
      );
    },
  };
}

export const stagingLeadActionsService = createStagingLeadActionsService();
