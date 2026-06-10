const COMPLIANCE_LABELS = {
  required: '待合规复核',
  approved: '合规已通过',
  rejected: '合规未通过',
};

function normalizedGrade(lead) {
  return String(lead?.grade || '').trim().toUpperCase();
}

function isDoNotContact(lead) {
  return Boolean(lead?.doNotContact || lead?.do_not_contact || lead?.status === 'do_not_contact');
}

function hasEmailContact(lead) {
  const contacts = Array.isArray(lead?.contacts) ? lead.contacts : [];
  return contacts.some((contact) => {
    const type = String(contact?.type || '').trim().toLowerCase();
    const value = String(contact?.value || '').trim();
    return Boolean(value) && (type === 'email' || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value));
  });
}

function formatConfidence(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return 'Unknown';
  }

  return `${Math.round(numeric * 100)}%`;
}

function hasEvidence(source) {
  return Boolean(String(source?.url || '').trim() || String(source?.evidence || '').trim());
}

export function canEnterOutreachQueue(lead) {
  const grade = normalizedGrade(lead);
  const status = String(lead?.status || 'pending').toLowerCase();

  return ['A', 'B', 'C'].includes(grade) && status !== 'invalid' && status !== 'watch' && !isDoNotContact(lead);
}

export function markLeadDoNotContact(lead, { actor, reason, markedAt } = {}) {
  return {
    ...lead,
    status: 'do_not_contact',
    doNotContact: true,
    doNotContactReason: reason || 'Unknown',
    doNotContactMarkedBy: actor || 'Unknown',
    doNotContactMarkedAt: markedAt || new Date().toISOString(),
  };
}

export function unmarkLeadDoNotContact(lead, { actor, reason } = {}) {
  return {
    ...lead,
    status: 'pending',
    doNotContact: false,
    doNotContactReason: `取消勿扰：${reason || 'Unknown'}`,
    doNotContactMarkedBy: actor || 'Unknown',
    doNotContactMarkedAt: '',
  };
}

export function buildPromoteStagingPayload({ actor, reviewNote } = {}) {
  return {
    actor: actor || '当前用户',
    accepted_fields_json: {
      customer_name: { source: 'mobile_manual_review' },
      contacts_json: { source: 'mobile_manual_review' },
      source_evidence: { source: 'mobile_manual_review' },
    },
    review_note: reviewNote || '人工复核通过，准入闸门允许晋级 core。',
  };
}

export function buildLeadDetailViewModel(lead = {}) {
  const grade = normalizedGrade(lead);
  const isCGrade = grade === 'C';
  const aiRecommendation = lead.aiRecommendation || {};
  const sources = Array.isArray(lead.sources) ? lead.sources : [];
  const coreGate = lead.coreGate || {
    status: 'ready',
    canPromoteToCore: true,
    reasons: ['来源和证据满足进入 core 的最低要求'],
  };
  const hasViewableEvidence = sources.some(hasEvidence);
  const duplicateSignals = lead.duplicateSignals || {};
  const duplicateBlocksPromotion = Boolean(duplicateSignals.blocksPromotion || duplicateSignals.hasStrongDuplicate);
  const duplicateLabel = duplicateBlocksPromotion
    ? '强重复阻断'
    : duplicateSignals.requiresManualReview
      ? '疑似重复待复核'
      : '';
  const gateAllowsPromotion = Boolean(coreGate.canPromoteToCore) && hasViewableEvidence && !duplicateBlocksPromotion;
  const canEnterQueue = canEnterOutreachQueue(lead) && gateAllowsPromotion;
  const canCreateDraft = canEnterQueue && hasEmailContact(lead);

  return {
    id: lead.id,
    customerName: lead.customerName || 'Unknown',
    basicInfo: `${lead.city || 'Unknown'} · ${lead.customerType || 'Unknown'}`,
    country: lead.country || 'Unknown',
    city: lead.city || 'Unknown',
    customerType: lead.customerType || 'Unknown',
    gradeLabel: grade ? `${grade} 级` : 'Unknown',
    gradeClass: isCGrade ? 'grade-c' : grade === 'B' ? 'grade-b' : 'grade-a',
    riskLabel: lead.riskLevel === 'Low' ? '低风险' : lead.riskLevel === 'Medium' ? '中风险' : `${lead.riskLevel || 'Unknown'} 风险`,
    operatingSummary: lead.operatingSummary || 'Unknown',
    handoffLabel: isCGrade || lead.handoffTeam === 'export_sales' ? '交付销售' : '交付客服',
    complianceLabel: isCGrade ? COMPLIANCE_LABELS[lead.complianceReviewStatus] || '待合规复核' : '',
    aiAdvice: {
      confidenceText: formatConfidence(aiRecommendation.confidence),
      suggestion: aiRecommendation.suggestion || 'Unknown',
      reason: aiRecommendation.reason || 'Unknown',
      missingInfo: Array.isArray(aiRecommendation.missingInfo) ? aiRecommendation.missingInfo : [],
      nextAction: aiRecommendation.nextAction || 'Unknown',
    },
    sources,
    hasViewableEvidence,
    contacts: Array.isArray(lead.contacts) ? lead.contacts : [],
    followUps: Array.isArray(lead.followUps) ? lead.followUps : [],
    doNotContactCustomerId: lead.doNotContactCustomerId || lead.do_not_contact_customer_id || '',
    inventoryEntry: lead.inventoryMatch || {
      label: '查看匹配车源',
      path: `/pages/inventory/index?leadId=${encodeURIComponent(lead.id || '')}`,
    },
    isDoNotContact: isDoNotContact(lead),
    coreGate,
    coreGateLabel: gateAllowsPromotion ? '可进入 core' : '不可进入 core',
    aiAudit: lead.aiAudit || {
      modelName: 'Unknown',
      promptVersion: 'Unknown',
      riskBlocked: false,
      riskBlockReason: '',
      executedAt: 'Unknown',
    },
    latestPageSnapshot: lead.latestPageSnapshot || null,
    duplicateSignals,
    duplicateLabel,
    canEnterOutreachQueue: canEnterQueue,
    canCreateOutreachDraft: canCreateDraft,
    outreachActionLabel: canEnterQueue
      ? '晋级客户'
      : (duplicateBlocksPromotion ? '重复待处理' : (isDoNotContact(lead) ? '已排除触达' : '待补证据')),
    autoSendEnabled: false,
  };
}
