import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';

import {
  buildPhase3DashboardView,
  fetchPhase3Dashboard,
} from '../src/services/phase3Dashboard.js';

const phase3Payload = {
  customer_acceptance: {
    promoted_customer_count: 3,
    accepted_first_followup_count: 2,
    effective_customer_acceptance_rate: 2 / 3,
  },
  enrichment: {
    staging_lead_count: 4,
    promoted_customer_count: 3,
    enrichment_result_count: 3,
    succeeded_enrichment_count: 2,
    field_candidate_count: 4,
    accepted_field_count: 2,
    contact_complete_customer_count: 2,
    vehicle_intent_customer_count: 1,
    enrichment_success_rate: 2 / 3,
    field_adoption_rate: 2 / 4,
    promotion_rate: 3 / 4,
    contact_completeness_rate: 2 / 3,
    vehicle_intent_rate: 1 / 3,
  },
  cleanup: {
    created_count: 5,
    approved_count: 4,
    executed_count: 3,
    duplicate_merge_count: 2,
    watch_restore_count: 1,
    adoption_rate: 4 / 5,
    duplicate_merge_rate: 2 / 5,
    watch_restore_rate: 1 / 5,
  },
  risk: {
    risk_event_count: 2,
    risk_violation_count: 1,
    risk_violation_target_zero: false,
  },
  guardrails: {
    auto_outreach_allowed: false,
    auto_friend_request_allowed: false,
    login_batch_collection_allowed: false,
    risk_violation_target: 0,
  },
};

test('phase3 dashboard view exposes customer acceptance, enrichment, cleanup and risk metrics', () => {
  const view = buildPhase3DashboardView(phase3Payload);

  assert.equal(view.customerAcceptance.promotedCustomerCount, 3);
  assert.equal(view.customerAcceptance.acceptedFirstFollowupCount, 2);
  assert.equal(view.customerAcceptance.effectiveCustomerAcceptanceRateText, '66.7%');

  assert.equal(view.enrichment.enrichmentSuccessRateText, '66.7%');
  assert.equal(view.enrichment.fieldAdoptionRateText, '50.0%');
  assert.equal(view.enrichment.promotionRateText, '75.0%');
  assert.equal(view.enrichment.contactCompletenessRateText, '66.7%');
  assert.equal(view.enrichment.vehicleIntentRateText, '33.3%');

  assert.equal(view.cleanup.createdCount, 5);
  assert.equal(view.cleanup.adoptionRateText, '80.0%');
  assert.equal(view.cleanup.duplicateMergeRateText, '40.0%');
  assert.equal(view.cleanup.watchRestoreRateText, '20.0%');

  assert.equal(view.risk.riskViolationCount, 1);
  assert.equal(view.risk.targetText, '目标 0');
  assert.equal(view.risk.statusClass, 'red');
  assert.equal(view.risk.statusText, '需处理');

  assert.equal(view.guardrails.autoOutreachAllowed, false);
  assert.equal(view.guardrails.autoFriendRequestAllowed, false);
  assert.equal(view.guardrails.loginBatchCollectionAllowed, false);
});

test('fetch phase3 dashboard calls backend metrics endpoint', async () => {
  const requestedUrls = [];
  const payload = await fetchPhase3Dashboard({
    baseUrl: 'https://api.example.test/',
    fetcher: async (url) => {
      requestedUrls.push(url);
      return {
        ok: true,
        json: async () => phase3Payload,
      };
    },
  });

  assert.equal(requestedUrls[0], 'https://api.example.test/phase3-dashboard/metrics');
  assert.equal(payload.customer_acceptance.promoted_customer_count, 3);
});

test('admin page registers phase3 dashboard without automatic outreach capability', async () => {
  const appSource = await readFile(new URL('../src/App.vue', import.meta.url), 'utf8');
  const phase3Section = await readFile(new URL('../src/pages/Phase3Page.vue', import.meta.url), 'utf8');

  assert.match(appSource, /Phase3Page/);
  assert.match(phase3Section, /id="phase3"/);
  assert.match(phase3Section, /第三阶段指标与风控/);
  assert.match(phase3Section, /有效客户承接率/);
  assert.match(phase3Section, /风险违规目标 0/);
  assert.match(phase3Section, /客户触达/);
  assert.match(phase3Section, /仅人工/);
  assert.doesNotMatch(phase3Section, /自动发送/);
  assert.doesNotMatch(phase3Section, /自动触达|自动私信|自动加好友|自动加好友按钮|sendMessage|addFriend|autoSend/i);
});
