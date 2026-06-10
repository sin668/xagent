function unknown(value) {
  return value == null || value === '' ? 'Unknown' : value;
}

function normalizeStatus(value) {
  const status = String(value || '').toLowerCase();
  if (
    status === 'pending_review'
    || status === 'new'
    || status === 'ready_for_customer_service'
    || status === 'ready_for_sales'
    || status === 'customer_service_following'
    || status === 'sales_following'
  ) {
    return 'pending';
  }
  return status || 'pending';
}

function normalizeGrade(value) {
  return String(value || 'Unknown').toUpperCase();
}

function mapDuplicateSignals(signals = {}) {
  return {
    hasStrongDuplicate: Boolean(signals.has_strong_duplicate),
    blocksPromotion: Boolean(signals.blocks_promotion),
    requiresManualReview: Boolean(signals.requires_manual_review),
    strongDuplicates: signals.strong_duplicates || [],
    suspectedDuplicates: signals.suspected_duplicates || [],
    sourceDuplicates: signals.source_duplicates || [],
  };
}

function duplicateMarkers(signals = {}) {
  const mapped = mapDuplicateSignals(signals);
  const markers = [];
  if (mapped.hasStrongDuplicate || mapped.blocksPromotion) {
    markers.push('强重复阻断');
  } else if (mapped.requiresManualReview) {
    markers.push('疑似重复待复核');
  }
  return markers;
}

function toNumber(value) {
  if (value == null || value === '') {
    return null;
  }
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function hasOwn(object, key) {
  return Object.prototype.hasOwnProperty.call(object, key);
}

function stagingLeadIdFromExternalId(externalId) {
  const value = String(externalId || '').trim();
  return value.startsWith('staging:') ? value.slice('staging:'.length) : '';
}

function buildLeadStatsSummary(summary = {}, payload = {}) {
  const explicitAbcCount = toNumber(summary.abc_grade_count) ?? toNumber(summary.actionable_lead_count);
  const gradeAbcCount = hasOwn(summary, 'a_grade_count')
    ? Number(summary.a_grade_count || 0) + Number(summary.b_grade_count || 0) + Number(summary.c_grade_count || 0)
    : null;

  return {
    abcGradeCount: explicitAbcCount ?? gradeAbcCount,
    sourceCount: toNumber(summary.source_count)
      ?? toNumber(summary.lead_source_count)
      ?? toNumber(summary.source_candidate_count)
      ?? (payload.channel_outputs || []).length,
    cleanedLeadCount: toNumber(summary.cleaned_lead_count)
      ?? toNumber(summary.invalid_watch_count)
      ?? toNumber(summary.invalid_count),
  };
}

function buildSyntheticLeads(summary = {}, queueItems = []) {
  const candidateCount = Number(summary.candidate_count || 0);
  const bCount = Number(summary.b_grade_count || 0);
  const cCount = Number(summary.c_grade_count || 0);
  const queued = queueItems.map((item) => ({
    id: item.customer_id,
    grade: normalizeGrade(item.grade),
    status: normalizeStatus(item.status),
    doNotContact: false,
    followUpDueToday: true,
    channelRisk: 'Low',
  }));
  const leads = [...queued];

  for (let index = leads.filter((lead) => lead.grade === 'B').length; index < bCount; index += 1) {
    leads.push({ id: `api-b-${index}`, grade: 'B', status: 'pending', doNotContact: false, followUpDueToday: true, channelRisk: 'Low' });
  }
  for (let index = leads.filter((lead) => lead.grade === 'C').length; index < cCount; index += 1) {
    leads.push({ id: `api-c-${index}`, grade: 'C', status: 'pending', doNotContact: false, followUpDueToday: true, channelRisk: 'Medium' });
  }
  for (let index = leads.length; index < candidateCount; index += 1) {
    leads.push({ id: `api-lead-${index}`, grade: 'A', status: 'pending', doNotContact: false, followUpDueToday: false, channelRisk: 'Low' });
  }

  return leads;
}

export function mapAdminOverviewToHomeData(payload = {}) {
  const summary = payload.summary || {};
  const teamQueues = payload.team_queues || {};
  const queueItems = [
    ...(teamQueues.customer_service?.items || []),
    ...(teamQueues.sales?.items || []),
  ];

  return {
    leads: buildSyntheticLeads(summary, queueItems),
    leadStatsSummary: buildLeadStatsSummary(summary, payload),
    aiTasks: [
      {
        id: 'api-lead-review',
        title: '后端线索队列同步',
        source: 'apps/api',
        status: 'running',
        channelRisk: 'Low',
        candidateCount: Number(summary.candidate_count || 0),
        estimateText: '实时接口',
        progress: 100,
      },
    ],
    channels: (payload.channel_outputs || []).map((channel) => ({
      name: channel.display_name || channel.channel_name || 'Unknown',
      riskLevel: channel.risk_level || 'Unknown',
      totalLeads: Number(channel.candidate_count || 0),
      bGradeLeads: Number(channel.b_grade_count || 0),
      effectiveRate: 1 - Number(channel.invalid_rate || 0),
    })),
  };
}

export function mapCustomerListToLeadPool(payload = {}) {
  return (payload.items || []).map((customer) => ({
    id: customer.id,
    entityType: 'customer',
    externalId: customer.external_id || '',
    customerName: customer.name || 'Unknown',
    country: customer.country || 'Unknown',
    city: customer.city || 'Unknown',
    customerType: customer.customer_type || 'Unknown',
    channel: customer.primary_channel || 'apps/api',
    grade: normalizeGrade(customer.grade),
    status: normalizeStatus(customer.status),
    riskLevel: customer.risk_level || 'Unknown',
    doNotContact: Boolean(customer.do_not_contact),
    evidenceNote: customer.evidence_note || '',
    contacts: customer.contacts || [],
    sources: customer.sources || [],
    aiRecommendationReason: customer.ai_recommendation_reason || '',
    aiRecommendedGrade: customer.ai_recommended_grade || '',
    sourceUrl: customer.source_url || customer.sources?.[0]?.url || '',
    sourceEvidence: customer.source_evidence || customer.evidence_note || customer.sources?.[0]?.evidence || '',
    handoffTeam: normalizeGrade(customer.grade) === 'C' ? 'export_sales' : 'customer_service',
    complianceReviewStatus: normalizeGrade(customer.grade) === 'C' ? 'required' : '',
    isOverdue: false,
  }));
}

export function mergeCustomerAndStagingLeadPools(customers = [], stagingLeads = []) {
  const customerExternalIds = new Set(
    customers
      .map((lead) => String(lead.externalId || lead.external_id || '').trim())
      .filter(Boolean),
  );
  const customerIdsFromExternalIds = new Set(
    [...customerExternalIds]
      .filter((externalId) => externalId.startsWith('staging:'))
      .map((externalId) => externalId.slice('staging:'.length)),
  );
  const stagedOnly = stagingLeads.filter((lead) => !customerIdsFromExternalIds.has(String(lead.id || '')));
  return [...customers, ...stagedOnly];
}

export function mapStagingLeadListToLeadPool(payload = {}) {
  return (payload.items || []).map((lead) => {
    const grade = normalizeGrade(lead.recommended_grade);
    const contacts = mapContactsFromLead(lead);
    const hasContact = Boolean(lead.has_contact) || contacts.some((contact) => contact.value && contact.value !== 'Unknown');
    const riskMarkers = [...(lead.risk_markers || []), ...duplicateMarkers(lead.duplicate_signals)];
    return {
      id: lead.id,
      entityType: 'staging',
      customerName: lead.customer_name || 'Unknown',
      country: lead.country || 'Unknown',
      city: lead.city || 'Unknown',
      customerType: lead.customer_type || 'Unknown',
      channel: lead.source_url || 'staging',
      grade,
      status: normalizeStatus(lead.review_status),
      queueStatus: lead.queue_status || 'pending_review',
      riskLevel: lead.source_risk_level || 'Unknown',
      requiresSecondaryVerification: Boolean(lead.requires_secondary_verification)
        || lead.source_risk_level === 'High'
        || lead.review_status === 'needs_secondary_verification',
      hasContact,
      contacts,
      evidenceStatus: lead.evidence_status || 'missing',
      riskMarkers,
      duplicateSignals: mapDuplicateSignals(lead.duplicate_signals),
      doNotContact: false,
      evidenceNote: [lead.source_evidence, ...riskMarkers].filter(Boolean).join(' · '),
      aiRecommendationReason: lead.recommended_reason || lead.ai_recommendation_reason || '',
      aiRecommendedGrade: lead.ai_recommended_grade || lead.recommended_grade || '',
      sourceUrl: lead.source_url || '',
      sourceEvidence: lead.source_evidence || '',
      handoffTeam: grade === 'C' ? 'export_sales' : 'customer_service',
      complianceReviewStatus: grade === 'C' ? 'required' : '',
      isOverdue: false,
    };
  });
}

export function mapCustomerSummaryToLeadDetail(customer = {}) {
  const grade = normalizeGrade(customer.grade);
  const stagingLeadId = stagingLeadIdFromExternalId(customer.external_id || customer.externalId);
  return {
    id: customer.id,
    entityType: 'customer',
    customerId: customer.id,
    stagingLeadId,
    customerName: customer.name || 'Unknown',
    country: customer.country || 'Unknown',
    city: customer.city || 'Unknown',
    customerType: customer.customer_type || 'Unknown',
    grade,
    status: normalizeStatus(customer.status),
    riskLevel: customer.risk_level || 'Unknown',
    handoffTeam: grade === 'C' ? 'export_sales' : 'customer_service',
    operatingSummary: customer.operating_summary || 'Unknown',
    aiRecommendation: {
      confidence: null,
      suggestion: customer.ai_recommended_grade ? `AI 推荐等级 ${customer.ai_recommended_grade}` : 'Unknown',
      reason: customer.ai_recommendation_reason || 'Unknown',
      missingInfo: customer.missing_fields ? String(customer.missing_fields).split(/[,\n，]/).filter(Boolean) : [],
      nextAction: '人工复核',
    },
    sources: customer.sources || [],
    contacts: customer.contacts || [],
    followUps: [],
    inventoryMatch: {
      label: '查看匹配车源',
      path: `/pages/inventory/index?leadId=${encodeURIComponent(customer.id || '')}`,
    },
    doNotContact: Boolean(customer.do_not_contact),
    complianceReviewStatus: grade === 'C' ? 'required' : '',
  };
}

export function mapCustomerDetailToLeadDetail(payload = {}) {
  const profile = payload.profile || {};
  const doNotContact = payload.do_not_contact || {};
  const grade = normalizeGrade(profile.grade);
  const stagingLeadId = stagingLeadIdFromExternalId(profile.external_id || profile.externalId || payload.external_id || payload.externalId);
  const sources = Array.isArray(payload.sources) ? payload.sources : [];
  const contacts = Array.isArray(payload.contacts) ? payload.contacts : [];
  const followups = Array.isArray(payload.followups) ? payload.followups : [];
  const firstSource = sources[0] || {};
  const missingFields = Array.isArray(payload.pending_fields) ? payload.pending_fields : [];
  const nextAction = payload.next_action || (doNotContact.enabled ? '勿扰客户，不得触达' : '人工复核');
  const recommendationReason = profile.ai_recommendation_reason
    || payload.ai_recommendation_reason
    || firstSource.evidence_note
    || nextAction
    || 'Unknown';

  return {
    id: payload.id || profile.id,
    entityType: 'customer',
    customerId: payload.id || profile.id,
    stagingLeadId,
    customerName: profile.name || 'Unknown',
    country: profile.country || 'Unknown',
    city: profile.city || 'Unknown',
    customerType: profile.customer_type || 'Unknown',
    grade,
    status: normalizeStatus(profile.status),
    riskLevel: firstSource.risk_level || profile.risk_level || 'Unknown',
    handoffTeam: profile.owner_team || (grade === 'C' ? 'export_sales' : 'customer_service'),
    operatingSummary: profile.operating_summary
      || payload.operating_summary
      || firstSource.evidence_note
      || nextAction
      || 'Unknown',
    aiRecommendation: {
      confidence: null,
      suggestion: profile.ai_recommended_grade ? `AI 推荐等级 ${profile.ai_recommended_grade}` : `当前客户等级 ${grade}`,
      reason: recommendationReason,
      missingInfo: missingFields,
      nextAction,
    },
    sources: sources.map((source) => ({
      type: source.platform || source.type || '客户来源',
      url: source.source_url || source.url || '',
      evidence: source.evidence_note || source.evidence || source.source_title || 'Unknown',
    })),
    contacts: contacts.map((contact) => ({
      type: contact.type || contact.kind || 'Unknown',
      value: contact.value || 'Unknown',
      usage: contact.label || contact.evidence_note || contact.usage || '人工复核后使用',
      sourceUrl: contact.source_url || '',
      evidence: contact.evidence_note || '',
    })),
    followUps: followups.map((followup) => ({
      title: [followup.team, followup.next_action].filter(Boolean).join(' · ') || followup.followup_type || '跟进记录',
      detail: followup.content || followup.next_action || 'Unknown',
    })),
    inventoryMatch: {
      label: '查看匹配车源',
      path: `/pages/inventory/index?leadId=${encodeURIComponent(payload.id || profile.id || '')}`,
    },
    doNotContact: Boolean(doNotContact.enabled),
    doNotContactCustomerId: payload.id || profile.id || '',
    doNotContactReason: doNotContact.reason || '',
    doNotContactMarkedBy: doNotContact.marked_by || '',
    doNotContactMarkedAt: doNotContact.marked_at || '',
    complianceReviewStatus: grade === 'C' || payload.compliance_status?.requires_review ? 'required' : '',
    coreGate: {
      status: 'ready',
      canPromoteToCore: !doNotContact.enabled,
      reasons: doNotContact.enabled ? ['勿扰客户，不得触达'] : ['已是客户详情，可进入人工复核'],
    },
    duplicateSignals: {},
  };
}

function mapContact(contact = {}) {
  return {
    type: contact.type || contact.kind || 'Unknown',
    value: contact.value || 'Unknown',
    usage: contact.usage || contact.note || '人工复核后使用',
  };
}

function mapContactsFromLead(lead = {}) {
  const contacts = lead.contacts_json || lead.contacts || lead.contact_methods || [];
  return Array.isArray(contacts) ? contacts.map(mapContact) : [];
}

export function mapStagingLeadDetailToLeadDetail(payload = {}) {
  const lead = payload.staging_lead || payload;
  const candidate = payload.candidate_url || {};
  const snapshot = payload.latest_page_snapshot || null;
  const audit = payload.ai_audit_summary || {};
  const gate = payload.core_gate || {};
  const grade = normalizeGrade(lead.recommended_grade);
  const riskLevel = lead.source_risk_level || candidate.source_risk_level || 'Unknown';
  const sourceEvidence = lead.source_evidence || '';
  const snapshotEvidence = snapshot?.evidence_note || '';
  const missingInfo = Array.isArray(audit.missing_fields) && audit.missing_fields.length > 0
    ? audit.missing_fields
    : (Array.isArray(lead.missing_fields) ? lead.missing_fields : []);

  return {
    id: lead.id,
    entityType: 'staging',
    stagingLeadId: lead.id,
    customerId: '',
    customerName: lead.customer_name || 'Unknown',
    country: lead.country || 'Unknown',
    city: lead.city || 'Unknown',
    customerType: lead.customer_type || 'Unknown',
    grade,
    status: normalizeStatus(lead.review_status),
    riskLevel,
    handoffTeam: grade === 'C' ? 'export_sales' : 'customer_service',
    operatingSummary: lead.scale_signal || lead.activity_level || 'Unknown',
    aiRecommendation: {
      confidence: null,
      suggestion: audit.recommended_grade || lead.recommended_grade
        ? `AI 推荐等级 ${audit.recommended_grade || lead.recommended_grade}`
        : 'Unknown',
      reason: audit.recommended_reason || lead.recommended_reason || 'Unknown',
      missingInfo,
      nextAction: gate.can_promote_to_core ? '人工复核晋级 core' : '补充来源证据',
    },
    sources: [
      {
        type: '候选来源',
        url: candidate.url || lead.source_url || '',
        evidence: sourceEvidence || candidate.discovery_reason || 'Unknown',
      },
      ...(snapshot
        ? [
            {
              type: `页面快照 · ${snapshot.read_status || 'Unknown'}`,
              url: candidate.url || lead.source_url || '',
              evidence: snapshotEvidence || 'Unknown',
            },
          ]
        : []),
    ],
    contacts: mapContactsFromLead(lead),
    followUps: [
      {
        title: gate.can_promote_to_core ? '可进入人工晋级复核' : '暂不可晋级 core',
        detail: (gate.reasons || ['Unknown']).join('；'),
      },
    ],
    inventoryMatch: {
      label: '查看匹配车源',
      path: `/pages/inventory/index?leadId=${encodeURIComponent(lead.id || '')}`,
    },
    doNotContact: Boolean(payload.has_do_not_contact_match || lead.do_not_contact),
    doNotContactCustomerId: payload.do_not_contact_customer_id || lead.do_not_contact_customer_id || '',
    complianceReviewStatus: grade === 'C' || lead.requires_compliance_review ? 'required' : '',
    coreGate: {
      status: gate.status || 'blocked',
      canPromoteToCore: Boolean(gate.can_promote_to_core),
      reasons: gate.reasons || ['Unknown'],
    },
    duplicateSignals: mapDuplicateSignals(lead.duplicate_signals),
    aiAudit: {
      modelName: audit.model_name || 'Unknown',
      promptVersion: audit.prompt_version || 'Unknown',
      riskBlocked: Boolean(audit.risk_blocked),
      riskBlockReason: audit.risk_block_reason || '',
      executedAt: audit.executed_at || 'Unknown',
    },
    latestPageSnapshot: snapshot
      ? {
          pageTitle: snapshot.page_title || 'Unknown',
          evidenceNote: snapshotEvidence || 'Unknown',
          readStatus: snapshot.read_status || 'Unknown',
          capturedAt: snapshot.captured_at || 'Unknown',
          policyNote: snapshot.robots_or_policy_note || '',
        }
      : null,
  };
}

export function mapInventoryItems(payload = {}) {
  return (payload.items || []).map((item) => ({
    id: item.id,
    brand: unknown(item.brand),
    model: unknown(item.model),
    year: item.year ?? null,
    mileageKm: item.mileage_km ?? null,
    vehicleType: item.vehicle_type || 'Unknown',
    conditionSummary: item.condition_summary || 'Unknown',
    configuration: item.configuration || 'Unknown',
    quotedPrice: toNumber(item.quoted_price),
    currency: item.currency || 'USD',
    quoteStatus: item.quote_status || 'pending',
    exportReady: Boolean(item.export_ready),
    mediaUrls: item.media_urls || [],
    validUntil: item.valid_until || null,
  }));
}

export function mapInventoryMatches(payload = {}) {
  return (payload.items || []).map((item) => ({
    matchId: item.match_id,
    inventoryItemId: item.inventory_item_id,
    inventoryExternalId: item.inventory_external_id,
    brand: unknown(item.brand),
    model: unknown(item.model),
    year: item.year ?? null,
    vehicleType: item.vehicle_type || 'Unknown',
    conditionSummary: item.condition_summary || 'Unknown',
    quotedPrice: toNumber(item.quoted_price),
    currency: item.currency || 'USD',
    exportReady: Boolean(item.export_ready),
    validUntil: item.valid_until || null,
    priorityRecommendable: Boolean(item.priority_recommendable),
    recommendationReason: item.recommendation_reason || 'Unknown',
    riskTips: item.risk_tips || [],
    requiresComplianceReview: Boolean(item.requires_compliance_review),
  }));
}

export function mapComplianceStatus(payload = {}) {
  return {
    customerId: payload.customer_id || '',
    status: payload.status || 'pending',
    reviewer: payload.reviewer || null,
    reviewedAt: payload.reviewed_at || null,
    reason: payload.reason || 'Unknown',
    riskNote: payload.risk_note || 'Unknown',
    quoteContractBlocked: Boolean(payload.quote_contract_blocked),
    aiRiskTip: payload.ai_risk_tip || '',
  };
}

export function mapOutreachDraft(payload = {}) {
  return {
    id: payload.draft_id || payload.template_id || 'Unknown',
    customerName: payload.customer_name || 'Unknown',
    templateId: payload.template_id || 'Unknown',
    templateStatus: payload.template_status || '待业务审核',
    version: payload.version || 'Unknown',
    generatedAt: payload.generated_at || 'Unknown',
    subject: payload.subject || 'Unknown',
    body: payload.body || 'Unknown',
    refusalPath: payload.refusal_path || '',
    riskTips: payload.risk_tips || [],
    audit: {
      model: payload.audit?.model || 'Unknown',
      promptVersion: payload.audit?.prompt_version || 'Unknown',
      inputSaved: Boolean(payload.audit?.input_saved),
      outputSaved: Boolean(payload.audit?.output_saved),
    },
  };
}

export function mapOutreachRecords(payload = {}) {
  return payload.items || [];
}
