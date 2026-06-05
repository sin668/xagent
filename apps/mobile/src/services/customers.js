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

function normalizeGrade(value) {
  return String(value || 'Unknown').toUpperCase();
}

function unknown(value) {
  return value == null || value === '' ? 'Unknown' : value;
}

function firstIntentLabel(summary = {}) {
  const items = summary.items || [];
  if (items.length > 0) {
    return items.map((item) => item.label || `${item.brand || ''} ${item.model || ''}`.trim()).filter(Boolean).join(' / ');
  }
  return Number(summary.total || 0) > 0 ? `${summary.total} 个车型意向` : '待补全车型意向';
}

function primaryContactText(customer = {}) {
  const summary = customer.contact_summary || customer.contactSummary || {};
  if (summary.primary) {
    return summary.primary;
  }
  const contacts = customer.contacts || [];
  const primary = contacts.find((contact) => contact.is_primary || contact.isPrimary) || contacts[0];
  if (!primary) {
    return '待补全联系方式';
  }
  return `${primary.type || primary.method_type || 'contact'}:${primary.value || 'Unknown'}`;
}

function mapDetailContact(contact = {}) {
  return {
    id: contact.id,
    type: contact.type || 'Unknown',
    value: contact.value || 'Unknown',
    label: contact.label || '',
    sourceUrl: contact.source_url || contact.sourceUrl || '',
    evidenceNote: contact.evidence_note || contact.evidenceNote || '',
    isPrimary: Boolean(contact.is_primary || contact.isPrimary),
    isVerified: Boolean(contact.is_verified || contact.isVerified),
  };
}

function mapDetailSource(source = {}) {
  return {
    id: source.id,
    platform: source.platform || 'Unknown',
    sourceUrl: source.source_url || source.sourceUrl || '',
    sourceTitle: source.source_title || source.sourceTitle || '',
    evidenceNote: source.evidence_note || source.evidenceNote || '',
    evidenceExcerpt: source.evidence_excerpt || source.evidenceExcerpt || '',
    riskLevel: source.risk_level || source.riskLevel || 'Unknown',
    collectedBy: source.collected_by || source.collectedBy || '',
    collectedAt: source.collected_at || source.collectedAt || '',
  };
}

function mapDetailVehicleIntent(intent = {}) {
  const label = intent.label || [intent.brand, intent.model].filter(Boolean).join(' ') || '待确认车型';
  return {
    id: intent.id,
    label,
    brand: intent.brand || '',
    model: intent.model || '',
    yearRange: intent.year_range || intent.yearRange || '',
    vehicleAge: intent.vehicle_age || intent.vehicleAge || '',
    quantity: intent.quantity ?? null,
    budgetRange: intent.budget_range || intent.budgetRange || '',
    purchaseFrequency: intent.purchase_frequency || intent.purchaseFrequency || '',
    deliveryCountry: intent.delivery_country || intent.deliveryCountry || '',
    deliveryCity: intent.delivery_city || intent.deliveryCity || '',
    concerns: intent.concerns || [],
    sourceType: intent.source_type || intent.sourceType || '',
    sourceNote: intent.source_note || intent.sourceNote || '',
    status: intent.status || 'Unknown',
    createdBy: intent.created_by || intent.createdBy || '',
    createdAt: intent.created_at || intent.createdAt || '',
  };
}

function mapDetailOutreach(record = {}) {
  return {
    id: record.id,
    channel: record.channel || 'Unknown',
    status: record.status || 'Unknown',
    sentBy: record.sent_by || record.sentBy || '',
    owner: record.owner || '',
    sentAt: record.sent_at || record.sentAt || '',
    responseSummary: record.response_summary || record.responseSummary || '',
    nextAction: record.next_action || record.nextAction || '',
    triggersDoNotContact: Boolean(record.triggers_do_not_contact || record.triggersDoNotContact),
    createdAt: record.created_at || record.createdAt || '',
    scriptVersion: record.script_version || record.scriptVersion || '',
  };
}

function mapDetailFollowup(record = {}) {
  return {
    id: record.id,
    ownerId: record.owner_id || record.ownerId || '',
    team: record.team || 'Unknown',
    followupType: record.followup_type || record.followupType || '',
    content: record.content || '',
    customerFeedback: record.customer_feedback || record.customerFeedback || '',
    nextAction: record.next_action || record.nextAction || '',
    nextFollowupAt: record.next_followup_at || record.nextFollowupAt || '',
    triggeredDnc: Boolean(record.triggered_dnc || record.triggeredDnc),
    triggeredComplianceReview: Boolean(record.triggered_compliance_review || record.triggeredComplianceReview),
    createdBy: record.created_by || record.createdBy || '',
    createdAt: record.created_at || record.createdAt || '',
  };
}

export function mapCustomer(customer = {}) {
  const vehicleIntentSummary = customer.vehicle_intent_summary || customer.vehicleIntentSummary || {};
  const grade = normalizeGrade(customer.grade);
  const nextActionPriority = Number(customer.next_action_priority ?? customer.nextActionPriority ?? 999);
  const owner = customer.owner || '';

  return {
    id: customer.id,
    externalId: customer.external_id || customer.externalId || '',
    name: customer.name || 'Unknown',
    country: customer.country || 'Unknown',
    city: customer.city || 'Unknown',
    countryCityText: `${customer.country || 'Unknown'} · ${customer.city || 'Unknown'}`,
    customerType: customer.customer_type || customer.customerType || 'Unknown',
    grade,
    status: customer.status || 'Unknown',
    owner,
    ownerTeam: customer.owner_team || customer.ownerTeam || '',
    doNotContact: Boolean(customer.do_not_contact || customer.doNotContact),
    contacts: customer.contacts || [],
    contactSummary: customer.contact_summary || customer.contactSummary || {},
    contactSummaryText: primaryContactText(customer),
    vehicleIntentSummary,
    vehicleIntentText: firstIntentLabel(vehicleIntentSummary),
    hasVehicleIntent: Number(vehicleIntentSummary.total || 0) > 0,
    followupStatus: customer.followup_status || customer.followupStatus || '',
    nextAction: customer.next_action || customer.nextAction || '待分配',
    nextActionPriority,
    completenessScore: customer.completeness_score ?? customer.completenessScore ?? null,
    evidenceNote: customer.evidence_note || customer.evidenceNote || '',
    riskLevel: customer.risk_level || customer.riskLevel || 'Unknown',
  };
}

export function mapCustomerDetail(payload = {}) {
  const profile = payload.profile || {};
  const grade = normalizeGrade(profile.grade);
  return {
    id: payload.id || profile.id,
    profile: {
      id: profile.id || payload.id,
      externalId: profile.external_id || profile.externalId || '',
      name: profile.name || 'Unknown',
      country: profile.country || 'Unknown',
      city: profile.city || 'Unknown',
      customerType: profile.customer_type || profile.customerType || 'Unknown',
      grade,
      status: profile.status || 'Unknown',
      owner: profile.owner || '',
      ownerTeam: profile.owner_team || profile.ownerTeam || '',
      aiRecommendedGrade: profile.ai_recommended_grade || profile.aiRecommendedGrade || '',
      aiRecommendationReason: profile.ai_recommendation_reason || profile.aiRecommendationReason || '',
      createdAt: profile.created_at || profile.createdAt || '',
      updatedAt: profile.updated_at || profile.updatedAt || '',
    },
    contacts: (payload.contacts || []).map(mapDetailContact),
    sources: (payload.sources || []).map(mapDetailSource),
    vehicleIntents: (payload.vehicle_intents || payload.vehicleIntents || []).map(mapDetailVehicleIntent),
    outreachHistory: (payload.outreach_history || payload.outreachHistory || []).map(mapDetailOutreach),
    followups: (payload.followups || []).map(mapDetailFollowup),
    complianceStatus: payload.compliance_status || payload.complianceStatus || {},
    doNotContact: payload.do_not_contact || payload.doNotContact || {},
    pendingFields: payload.pending_fields || payload.pendingFields || [],
    sourceTraceability: payload.source_traceability || payload.sourceTraceability || {},
    contactSummary: payload.contact_summary || payload.contactSummary || {},
    sourceCompleteness: payload.source_completeness || payload.sourceCompleteness || {},
    completenessScore: payload.completeness_score ?? payload.completenessScore ?? null,
    vehicleIntentSummary: payload.vehicle_intent_summary || payload.vehicleIntentSummary || {},
    followupStatus: payload.followup_status || payload.followupStatus || '',
    nextAction: payload.next_action || payload.nextAction || '待分配',
    nextActionPriority: payload.next_action_priority ?? payload.nextActionPriority ?? null,
  };
}

export function getCustomerDetailViewModel(detail = {}) {
  const profile = detail.profile || {};
  const compliance = detail.complianceStatus || {};
  const doNotContact = detail.doNotContact || {};
  const grade = normalizeGrade(profile.grade);
  const requiresCompliance = Boolean(compliance.requires_review || compliance.requiresReview) || grade === 'C';
  const latestComplianceStatus = compliance.latest_status || compliance.latestStatus || '';
  const compliancePending = requiresCompliance && (!latestComplianceStatus || latestComplianceStatus === 'pending');
  const doNotContactEnabled = Boolean(doNotContact.enabled);

  return {
    ...detail,
    name: profile.name || 'Unknown',
    locationText: `${unknown(profile.country)} · ${unknown(profile.city)}`,
    customerTypeText: unknown(profile.customerType),
    gradeLabel: grade === 'UNKNOWN' ? 'Unknown' : `${grade} 级客户`,
    statusText: unknown(profile.status),
    ownerText: profile.owner || '待分配',
    ownerTeamText: profile.ownerTeam || '待分配团队',
    contactCountText: `${(detail.contacts || []).length} 条`,
    sourceCountText: `${(detail.sources || []).length} 条`,
    vehicleIntentCountText: `${(detail.vehicleIntents || []).length} 条`,
    outreachCountText: `${(detail.outreachHistory || []).length} 条`,
    followupCountText: `${(detail.followups || []).length} 条`,
    doNotContactLabel: doNotContactEnabled ? '勿扰客户' : '可人工跟进',
    doNotContactReason: doNotContact.reason || '',
    canCreateOutreachDraft: !doNotContactEnabled,
    complianceLabel: compliancePending ? 'C级合规待复核' : requiresCompliance ? '合规已记录' : '无需合规复核',
    complianceReason: compliance.latest_reason || compliance.latestReason || compliance.latest_risk_note || compliance.latestRiskNote || '',
    pendingFieldLabels: (detail.pendingFields || []).map((field) => `${field} 待补全`),
    contacts: (detail.contacts || []).map((contact) => ({
      ...contact,
      displayText: `${contact.type} · ${contact.value}`,
      evidenceText: contact.evidenceNote || contact.sourceUrl || '待补证据',
    })),
    sources: (detail.sources || []).map((source) => ({
      ...source,
      displayText: `${source.platform} · ${source.riskLevel}`,
      evidenceText: source.evidenceNote || source.evidenceExcerpt || '待补证据',
    })),
    vehicleIntents: (detail.vehicleIntents || []).map((intent) => ({
      ...intent,
      displayText: `${intent.label} · ${intent.purchaseFrequency || '待确认频率'} · ${intent.quantity == null ? '待确认数量' : `${intent.quantity} 台`}`,
      evidenceText: [intent.budgetRange || '预算待补全', ...(intent.concerns || [])].join(' · '),
    })),
    outreachHistory: (detail.outreachHistory || []).map((record) => ({
      ...record,
      title: `${record.channel} · ${record.status}`,
      detailText: `${record.responseSummary || '无摘要'} · 下一步：${record.nextAction || '待确认'} · 人工记录`,
    })),
    followups: (detail.followups || []).map((record) => ({
      ...record,
      title: `${record.team} · ${record.nextAction || '待确认下一步'}`,
      detailText: `${record.content || '无内容'} · 记录人：${record.createdBy || record.ownerId || 'Unknown'}`,
    })),
    sourceTraceabilityText: `${Number(detail.sourceTraceability?.lead_sources_count || 0)} 个来源 · ${Number(detail.sourceTraceability?.contact_evidence_count || 0)} 个联系方式证据`,
    completenessText: detail.completenessScore == null ? '完善度 Unknown' : `完善度 ${detail.completenessScore}%`,
    nextActionText: detail.nextAction || '待分配',
  };
}

export function sortCustomersByNextAction(customers = []) {
  return [...customers].sort((left, right) => {
    const priorityDiff = Number(left.nextActionPriority ?? 999) - Number(right.nextActionPriority ?? 999);
    if (priorityDiff !== 0) {
      return priorityDiff;
    }
    return String(left.name || '').localeCompare(String(right.name || ''));
  });
}

export function filterCustomers(customers = [], filterKey = 'all') {
  if (filterKey === 'today') {
    return customers.filter((customer) => customer.nextAction === '今日待跟进' || customer.followupStatus === 'due_today');
  }
  if (filterKey === 'c_compliance') {
    return customers.filter((customer) => customer.grade === 'C' && /合规/.test(customer.nextAction));
  }
  if (filterKey === 'has_intent') {
    return customers.filter((customer) => customer.hasVehicleIntent);
  }
  if (filterKey === 'unassigned') {
    return customers.filter((customer) => !customer.owner);
  }
  return customers;
}

export function buildCustomerFilterTabs(customers = []) {
  return [
    { key: 'all', label: '全部', count: customers.length },
    { key: 'today', label: '今日待跟进', count: filterCustomers(customers, 'today').length },
    { key: 'c_compliance', label: 'C级待合规', count: filterCustomers(customers, 'c_compliance').length },
    { key: 'has_intent', label: '有车型意向', count: filterCustomers(customers, 'has_intent').length },
    { key: 'unassigned', label: '待分配', count: filterCustomers(customers, 'unassigned').length },
  ];
}

export function getCustomerCardViewModel(customer = {}) {
  const grade = normalizeGrade(customer.grade);
  return {
    ...customer,
    gradeLabel: grade === 'UNKNOWN' ? 'Unknown' : `${grade} 级`,
    gradeClass: grade === 'C' ? 'customer-grade-c' : grade === 'B' ? 'customer-grade-b' : 'customer-grade-a',
    contactSummaryText: customer.contactSummaryText || '待补全联系方式',
    vehicleIntentText: customer.vehicleIntentText || '待补全车型意向',
    nextAction: customer.nextAction || '待分配',
    ownerText: customer.owner || '待分配',
    completenessText: customer.completenessScore == null ? '完善度 Unknown' : `完善度 ${customer.completenessScore}%`,
  };
}

export function createCustomersService({ client = apiClient } = {}) {
  return {
    async listCustomers(filters = {}) {
      const query = buildQuery({
        status: filters.status,
        grade: filters.grade,
        owner: filters.owner,
        country: filters.country,
        city: filters.city,
        limit: filters.limit,
      });
      const payload = await client.get(`/customers${query}`);
      const items = sortCustomersByNextAction((payload.items || []).map(mapCustomer));
      return { items };
    },
    async getCustomerDetail(customerId) {
      const payload = await client.get(`/customers/${encodeURIComponent(customerId)}`);
      return mapCustomerDetail(payload);
    },
  };
}

export const customersService = createCustomersService();
