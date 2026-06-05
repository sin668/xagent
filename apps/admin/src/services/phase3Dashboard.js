function toNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function percentText(value) {
  return `${(toNumber(value) * 100).toFixed(1)}%`;
}

function riskTargetLabel(targetZero) {
  return targetZero ? '风险违规目标 0 达成' : '风险违规目标 0 未达成';
}

export function buildPhase3DashboardView(payload = {}) {
  const customerAcceptance = payload.customer_acceptance || payload.customerAcceptance || {};
  const enrichment = payload.enrichment || {};
  const cleanup = payload.cleanup || {};
  const risk = payload.risk || {};
  const guardrails = payload.guardrails || {};
  const riskTargetZero = Boolean(risk.risk_violation_target_zero ?? risk.riskViolationTargetZero);

  return {
    customerAcceptance: {
      promotedCustomerCount: toNumber(customerAcceptance.promoted_customer_count ?? customerAcceptance.promotedCustomerCount),
      acceptedFirstFollowupCount: toNumber(
        customerAcceptance.accepted_first_followup_count ?? customerAcceptance.acceptedFirstFollowupCount,
      ),
      effectiveCustomerAcceptanceRate: toNumber(
        customerAcceptance.effective_customer_acceptance_rate ?? customerAcceptance.effectiveCustomerAcceptanceRate,
      ),
      effectiveRateText: percentText(
        customerAcceptance.effective_customer_acceptance_rate ?? customerAcceptance.effectiveCustomerAcceptanceRate,
      ),
      effectiveCustomerAcceptanceRateText: percentText(
        customerAcceptance.effective_customer_acceptance_rate ?? customerAcceptance.effectiveCustomerAcceptanceRate,
      ),
      acceptedText: `${toNumber(customerAcceptance.accepted_first_followup_count ?? customerAcceptance.acceptedFirstFollowupCount)} / ${toNumber(customerAcceptance.promoted_customer_count ?? customerAcceptance.promotedCustomerCount)}`,
    },
    enrichment: {
      enrichmentResultCount: toNumber(enrichment.enrichment_result_count ?? enrichment.enrichmentResultCount),
      succeededEnrichmentCount: toNumber(enrichment.succeeded_enrichment_count ?? enrichment.succeededEnrichmentCount),
      fieldCandidateCount: toNumber(enrichment.field_candidate_count ?? enrichment.fieldCandidateCount),
      acceptedFieldCount: toNumber(enrichment.accepted_field_count ?? enrichment.acceptedFieldCount),
      promotedCustomerCount: toNumber(enrichment.promoted_customer_count ?? enrichment.promotedCustomerCount),
      stagingLeadCount: toNumber(enrichment.staging_lead_count ?? enrichment.stagingLeadCount),
      contactCompleteCustomerCount: toNumber(
        enrichment.contact_complete_customer_count ?? enrichment.contactCompleteCustomerCount,
      ),
      vehicleIntentCustomerCount: toNumber(enrichment.vehicle_intent_customer_count ?? enrichment.vehicleIntentCustomerCount),
      enrichmentSuccessRateText: percentText(enrichment.enrichment_success_rate ?? enrichment.enrichmentSuccessRate),
      fieldAdoptionRateText: percentText(enrichment.field_adoption_rate ?? enrichment.fieldAdoptionRate),
      promotionRateText: percentText(enrichment.promotion_rate ?? enrichment.promotionRate),
      contactCompletenessRateText: percentText(enrichment.contact_completeness_rate ?? enrichment.contactCompletenessRate),
      vehicleIntentRateText: percentText(enrichment.vehicle_intent_rate ?? enrichment.vehicleIntentRate),
    },
    cleanup: {
      createdCount: toNumber(cleanup.created_count ?? cleanup.createdCount),
      approvedCount: toNumber(cleanup.approved_count ?? cleanup.approvedCount),
      executedCount: toNumber(cleanup.executed_count ?? cleanup.executedCount),
      duplicateMergeCount: toNumber(cleanup.duplicate_merge_count ?? cleanup.duplicateMergeCount),
      watchRestoreCount: toNumber(cleanup.watch_restore_count ?? cleanup.watchRestoreCount),
      adoptionRateText: percentText(cleanup.adoption_rate ?? cleanup.adoptionRate),
      duplicateMergeRateText: percentText(cleanup.duplicate_merge_rate ?? cleanup.duplicateMergeRate),
      watchRestoreRateText: percentText(cleanup.watch_restore_rate ?? cleanup.watchRestoreRate),
    },
    risk: {
      riskEventCount: toNumber(risk.risk_event_count ?? risk.riskEventCount),
      riskViolationCount: toNumber(risk.risk_violation_count ?? risk.riskViolationCount),
      riskViolationTargetZero: riskTargetZero,
      targetZeroLabel: riskTargetLabel(riskTargetZero),
      targetZeroClass: riskTargetZero ? 'green' : 'red',
      targetText: `目标 ${toNumber(guardrails.risk_violation_target ?? guardrails.riskViolationTarget)}`,
      statusClass: riskTargetZero ? 'green' : 'red',
      statusText: riskTargetZero ? '达标' : '需处理',
      violationText: `${toNumber(risk.risk_violation_count ?? risk.riskViolationCount)} / ${toNumber(risk.risk_event_count ?? risk.riskEventCount)}`,
    },
    guardrails: {
      autoOutreachAllowed: Boolean(guardrails.auto_outreach_allowed ?? guardrails.autoOutreachAllowed),
      autoFriendRequestAllowed: Boolean(guardrails.auto_friend_request_allowed ?? guardrails.autoFriendRequestAllowed),
      loginBatchCollectionAllowed: Boolean(
        guardrails.login_batch_collection_allowed ?? guardrails.loginBatchCollectionAllowed,
      ),
      riskViolationTarget: toNumber(guardrails.risk_violation_target ?? guardrails.riskViolationTarget),
    },
  };
}

export async function fetchPhase3Dashboard({
  baseUrl = '',
  fetcher = globalThis.fetch,
} = {}) {
  if (typeof fetcher !== 'function') {
    throw new Error('fetcher is required to load phase3 dashboard');
  }

  const normalizedBaseUrl = String(baseUrl || '').replace(/\/$/, '');
  const response = await fetcher(`${normalizedBaseUrl}/phase3-dashboard/metrics`);
  if (!response.ok) {
    throw new Error(`Failed to load phase3 dashboard: ${response.status || 'unknown'}`);
  }
  return response.json();
}
