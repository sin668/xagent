export const QUOTE_DISCLAIMER = '推荐车源仅用于人工报价前评估，不等同于正式报价。';

function formatPrice(value, currency = 'USD') {
  if (value == null) {
    return '价格待确认';
  }
  return `${currency} ${Number(value).toLocaleString('en-US')}`;
}

export function buildInventoryMatchView(match = {}) {
  const validUntil = match.validUntil || match.valid_until || '';
  const title = `${match.brand || 'Unknown'} ${match.model || 'Unknown'}${match.year ? ` ${match.year}` : ''}`;
  const exportReady = match.exportReady ?? match.export_ready;
  return {
    matchId: match.matchId || match.match_id,
    title,
    reason: match.recommendationReason || match.recommendation_reason || 'Unknown',
    priceText: formatPrice(match.quotedPrice ?? match.quoted_price, match.currency || 'USD'),
    exportLabel: exportReady ? '可出口' : '不可出口',
    expiryLabel: validUntil ? `有效至 ${validUntil.slice(0, 10)}` : '有效期 Unknown',
    riskTips: match.riskTips || match.risk_tips || [],
    priorityRecommendable: Boolean(match.priorityRecommendable ?? match.priority_recommendable),
    requiresComplianceReview: Boolean(match.requiresComplianceReview ?? match.requires_compliance_review),
    quoteDisclaimer: QUOTE_DISCLAIMER,
  };
}

export function filterRecommendableMatches(matches = []) {
  return matches.filter((match) => Boolean(match.priorityRecommendable ?? match.priority_recommendable));
}

export function buildMatchDecisionPayload({ decision, owner, note }) {
  return {
    decision,
    owner,
    note,
    formal_quote_allowed: false,
  };
}
