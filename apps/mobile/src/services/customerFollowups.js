import { apiClient } from './apiClient.js';

function toBoolean(value) {
  return Boolean(value);
}

export function mapCustomerFollowup(record = {}) {
  const team = record.team || 'Unknown';
  const followupType = record.followup_type || record.followupType || 'Unknown';
  const nextAction = record.next_action || record.nextAction || '待确认下一步';
  const content = record.content || '无内容';
  const feedback = record.customer_feedback || record.customerFeedback || '无客户反馈';
  const nextFollowupAt = record.next_followup_at || record.nextFollowupAt || '';
  const createdBy = record.created_by || record.createdBy || record.owner_id || record.ownerId || 'Unknown';
  const createdAt = record.created_at || record.createdAt || 'Unknown';
  const triggeredDnc = toBoolean(record.triggered_dnc || record.triggeredDnc);
  const triggeredComplianceReview = toBoolean(record.triggered_compliance_review || record.triggeredComplianceReview);

  return {
    id: record.id,
    customerId: record.customer_id || record.customerId || '',
    ownerId: record.owner_id || record.ownerId || '',
    team,
    followupType,
    content,
    customerFeedback: feedback,
    nextAction,
    nextFollowupAt,
    triggeredDnc,
    triggeredComplianceReview,
    createdBy,
    createdAt,
    title: `${team} · ${followupType}`,
    detailText: `${content} · 客户反馈：${feedback}`,
    nextFollowupText: nextFollowupAt ? `下次跟进：${nextFollowupAt}` : '下次跟进：待设置',
    auditText: `记录人：${createdBy} · ${createdAt}`,
    dncWarning: triggeredDnc ? '已标记勿扰，后续主动跟进硬阻断' : '',
    complianceWarning: triggeredComplianceReview ? '触发合规复核' : '',
  };
}

export function buildFollowupTimeline({ followups = [], outreachHistory = [] } = {}) {
  const followupItems = followups.map((item) => ({
    id: item.id,
    kind: 'followup',
    title: item.title || `${item.team} · ${item.followupType}`,
    note: `${item.detailText || item.content || '无内容'} · ${item.nextFollowupText || ''} · 人工记录`,
    createdAt: item.createdAt || item.created_at || '',
  }));
  const outreachItems = outreachHistory.map((item) => ({
    id: item.id,
    kind: 'outreach',
    title: `${item.channel || 'Unknown'} · ${item.status || 'Unknown'}`,
    note: `${item.responseSummary || item.response_summary || '无摘要'} · 下一步：${item.nextAction || item.next_action || '待确认'} · 人工记录`,
    createdAt: item.createdAt || item.created_at || item.sentAt || item.sent_at || '',
  }));

  return [...followupItems, ...outreachItems].sort((left, right) => String(right.createdAt).localeCompare(String(left.createdAt)));
}

export function getFollowupHardBlockTip({ triggeredDnc = false, triggeredComplianceReview = false } = {}) {
  if (triggeredDnc) {
    return '标记勿扰后，勿扰客户不得再次进入触达队列，不得生成触达草稿，不得新增主动触达。';
  }
  if (triggeredComplianceReview) {
    return '触发合规复核后，报价、合同、付款、物流、清关和交付周期前必须先完成合规复核。';
  }
  return '跟进记录仅保存人工记录，不会发送消息。';
}

export function buildCustomerFollowupPayload({
  customerId,
  ownerId = 'mobile-user',
  team = 'customer_service',
  followupType = 'internal_note',
  content = '',
  customerFeedback = '',
  nextAction = '',
  nextFollowupAt = '',
  triggeredDnc = false,
  triggeredComplianceReview = false,
  createdBy = 'mobile-user',
} = {}) {
  if (triggeredDnc && !String(customerFeedback || '').trim()) {
    throw new Error('标记勿扰必须填写客户反馈');
  }
  return {
    customer_id: customerId,
    owner_id: ownerId,
    team,
    followup_type: followupType,
    content,
    customer_feedback: customerFeedback || null,
    next_action: nextAction || null,
    next_followup_at: nextFollowupAt || null,
    triggered_dnc: Boolean(triggeredDnc),
    triggered_compliance_review: Boolean(triggeredComplianceReview),
    created_by: createdBy,
  };
}

export function createCustomerFollowupsService({ client = apiClient } = {}) {
  return {
    async listFollowups(customerId) {
      const payload = await client.get(`/customers/${encodeURIComponent(customerId)}/followups`);
      return (payload || []).map(mapCustomerFollowup);
    },
    async createFollowup(customerId, payload) {
      const created = await client.post(`/customers/${encodeURIComponent(customerId)}/followups`, buildCustomerFollowupPayload({
        ...payload,
        customerId: payload.customerId || payload.customer_id || customerId,
      }));
      return mapCustomerFollowup(created);
    },
  };
}

export const customerFollowupsService = createCustomerFollowupsService();
