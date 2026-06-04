export const AI_RISK_TIP = 'AI仅提示风险，不能替代合规复核结论或法律意见。';

const STATUS_LABELS = {
  pending: '待合规复核',
  approved: '合规已通过',
  rejected: '合规未通过',
  not_required: '无需复核',
};

function normalizeStatus(status) {
  return String(status || 'pending').trim().toLowerCase();
}

function normalizeGrade(grade) {
  return String(grade || '').trim().toUpperCase();
}

function formatReviewDate(value) {
  if (!value) {
    return 'Unknown';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value).slice(0, 10) || 'Unknown';
  }

  return date.toISOString().slice(0, 10);
}

export function getAiRiskTip() {
  return AI_RISK_TIP;
}

export function buildComplianceReviewView(review = {}) {
  const grade = normalizeGrade(review.grade);
  const status = normalizeStatus(review.status);
  const isCGrade = grade === 'C';
  const quoteContractBlocked = Boolean(
    review.quoteContractBlocked ?? (isCGrade && status !== 'approved'),
  );
  const reviewer = review.reviewer || null;
  const reviewedAt = review.reviewedAt || review.reviewed_at || null;

  return {
    status,
    label: STATUS_LABELS[status] || '待合规复核',
    reviewer,
    reviewedAt,
    reviewerText: reviewer ? `${reviewer} · ${formatReviewDate(reviewedAt)}` : '待合规复核人员处理',
    reason: review.reason || 'Unknown',
    riskNote: review.riskNote || review.risk_note || 'Unknown',
    quoteContractBlocked,
    aiRiskTip: getAiRiskTip(),
    aiLegalConclusionAllowed: false,
  };
}

export function canMarkQuoted(reviewView = {}) {
  return !Boolean(reviewView.quoteContractBlocked);
}
