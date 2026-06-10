import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  mapAdminOverviewToHomeData,
  mapCustomerDetailToLeadDetail,
  mapCustomerListToLeadPool,
  mapCustomerSummaryToLeadDetail,
  mapInventoryItems,
  mergeCustomerAndStagingLeadPools,
  mapOutreachDraft,
  mapOutreachRecords,
  mapStagingLeadDetailToLeadDetail,
  mapStagingLeadListToLeadPool,
} from '../src/services/apiAdapters.js';

test('admin overview maps to existing mobile home dashboard input shape without forbidden channel execution', () => {
  const mapped = mapAdminOverviewToHomeData({
    summary: {
      candidate_count: 12,
      b_grade_count: 5,
      c_grade_count: 3,
      sla_risk_count: 2,
    },
    channel_outputs: [
      {
        channel_name: 'official_website',
        display_name: '官网',
        risk_level: 'Low',
        candidate_count: 8,
        b_grade_count: 4,
        invalid_rate: 0.1,
      },
      {
        channel_name: 'vkontakte',
        display_name: 'VK',
        risk_level: 'High',
        candidate_count: 99,
        b_grade_count: 20,
        invalid_rate: 0.2,
      },
    ],
    team_queues: {
      customer_service: { items: [{ customer_id: 'c1', grade: 'B', status: 'pending' }] },
      sales: { items: [{ customer_id: 'c2', grade: 'C', status: 'pending' }] },
    },
  });

  assert.equal(mapped.leads.length, 12);
  assert.equal(mapped.leads.filter((lead) => lead.grade === 'B').length, 5);
  assert.equal(mapped.leads.filter((lead) => lead.grade === 'C').length, 3);
  assert.equal(mapped.channels[0].name, '官网');
  assert.equal(mapped.channels[1].riskLevel, 'High');
  assert.equal(mapped.aiTasks.some((task) => task.channelRisk === 'High'), false);
});

test('customer list maps backend summaries to lead pool cards with Unknown for missing fields', () => {
  const mapped = mapCustomerListToLeadPool({
    items: [
      {
        id: 'c1',
        name: 'Auto City',
        grade: 'B',
        status: 'pending_review',
        do_not_contact: false,
      },
      {
        id: 'c2',
        name: 'Quiet Dealer',
        grade: 'C',
        status: 'ready_for_sales',
        do_not_contact: true,
      },
    ],
  });

  assert.equal(mapped[0].customerName, 'Auto City');
  assert.equal(mapped[0].status, 'pending');
  assert.equal(mapped[0].city, 'Unknown');
  assert.equal(mapped[1].status, 'pending');
  assert.equal(mapped[1].doNotContact, true);
});

test('customer and staging lead pools merge without duplicated promoted staging leads', () => {
  const customers = mapCustomerListToLeadPool({
    items: [
      {
        id: 'c1',
        external_id: 'staging:s1',
        name: 'Auto City',
        grade: 'B',
        status: 'ready_for_customer_service',
        do_not_contact: false,
        contacts: [{ type: 'telegram', value: '@auto_city' }],
      },
    ],
  });
  const stagingLeads = mapStagingLeadListToLeadPool({
    items: [
      {
        id: 's1',
        customer_name: 'Auto City',
        recommended_grade: 'B',
        review_status: 'approved',
        queue_status: 'eligible',
        has_contact: true,
      },
      {
        id: 's2',
        customer_name: 'Pending Dealer',
        recommended_grade: 'B',
        review_status: 'pending_review',
        queue_status: 'pending_review',
        has_contact: true,
      },
    ],
  });

  const merged = mergeCustomerAndStagingLeadPools(customers, stagingLeads);

  assert.deepEqual(merged.map((lead) => lead.id), ['c1', 's2']);
  assert.equal(merged[0].status, 'pending');
});

test('customer summary maps to detail shape and preserves missing values as Unknown', () => {
  const detail = mapCustomerSummaryToLeadDetail({
    id: 'c1',
    name: 'Auto City',
    grade: 'C',
    status: 'pending_review',
    do_not_contact: false,
  });

  assert.equal(detail.customerName, 'Auto City');
  assert.equal(detail.city, 'Unknown');
  assert.equal(detail.aiRecommendation.reason, 'Unknown');
  assert.equal(detail.complianceReviewStatus, 'required');
});

test('customer detail aggregate maps to lead detail page shape without losing profile fields', () => {
  const detail = mapCustomerDetailToLeadDetail({
    id: 'customer-1',
    profile: {
      id: 'customer-1',
      external_id: 'staging:staging-lead-1',
      name: 'AutoCity Vladivostok',
      country: 'Russia',
      city: 'Vladivostok',
      customer_type: 'local_dealer_secondary_dealer',
      grade: 'C',
      status: 'ready_for_sales',
      owner_team: 'export_sales',
    },
    contacts: [
      {
        type: 'email',
        value: 'sales@autocity-vl.example',
        label: 'primary',
        source_url: 'https://autocity.example/contact',
        evidence_note: '官网联系页公开邮箱',
      },
    ],
    sources: [
      {
        platform: 'official_website',
        source_url: 'https://autocity.example',
        source_title: 'AutoCity',
        evidence_note: '官网展示车辆销售业务和联系页',
        risk_level: 'Low',
      },
    ],
    followups: [
      {
        team: 'customer_service',
        content: '确认采购频率和目标价位',
        next_action: '今日待跟进',
      },
    ],
    do_not_contact: {
      enabled: true,
      reason: '客户拒绝继续联系',
      marked_by: 'cs-a',
      marked_at: '2026-06-04T09:00:00+08:00',
    },
    pending_fields: ['budget_range', 'delivery_city'],
    next_action: '勿扰客户，不得触达',
  });

  assert.equal(detail.id, 'customer-1');
  assert.equal(detail.entityType, 'customer');
  assert.equal(detail.customerId, 'customer-1');
  assert.equal(detail.stagingLeadId, 'staging-lead-1');
  assert.equal(detail.customerName, 'AutoCity Vladivostok');
  assert.equal(detail.country, 'Russia');
  assert.equal(detail.city, 'Vladivostok');
  assert.equal(detail.customerType, 'local_dealer_secondary_dealer');
  assert.equal(detail.grade, 'C');
  assert.equal(detail.status, 'pending');
  assert.equal(detail.riskLevel, 'Low');
  assert.equal(detail.operatingSummary, '官网展示车辆销售业务和联系页');
  assert.deepEqual(detail.aiRecommendation.missingInfo, ['budget_range', 'delivery_city']);
  assert.equal(detail.sources[0].type, 'official_website');
  assert.equal(detail.sources[0].url, 'https://autocity.example');
  assert.equal(detail.sources[0].evidence, '官网展示车辆销售业务和联系页');
  assert.equal(detail.contacts[0].type, 'email');
  assert.equal(detail.contacts[0].value, 'sales@autocity-vl.example');
  assert.equal(detail.contacts[0].usage, 'primary');
  assert.equal(detail.followUps[0].detail, '确认采购频率和目标价位');
  assert.equal(detail.doNotContact, true);
  assert.equal(detail.doNotContactCustomerId, 'customer-1');
  assert.equal(detail.coreGate.canPromoteToCore, false);
});

test('staging lead list maps review fields to mobile lead pool cards', () => {
  const mapped = mapStagingLeadListToLeadPool({
    items: [
      {
        id: 's1',
        customer_name: 'VK Cars Import RU',
        city: 'Moscow',
        customer_type: 'local_dealer_secondary_dealer',
        source_url: 'https://vk.example/dealer',
        source_risk_level: 'High',
        recommended_grade: 'Watch',
        review_status: 'needs_secondary_verification',
        queue_status: 'not_eligible',
        has_contact: false,
        contacts_json: [{ type: 'email', value: 'vk-cars@example.ru', usage: '公开页面邮箱' }],
        evidence_status: 'present',
        risk_markers: ['High 二次复核', 'Watch 不进入触达'],
        duplicate_signals: {
          has_strong_duplicate: true,
          blocks_promotion: true,
          requires_manual_review: true,
          strong_duplicates: [{ reason: '同名同邮箱' }],
          suspected_duplicates: [],
          source_duplicates: [],
        },
      },
    ],
  });

  assert.equal(mapped[0].id, 's1');
  assert.equal(mapped[0].customerName, 'VK Cars Import RU');
  assert.equal(mapped[0].riskLevel, 'High');
  assert.equal(mapped[0].grade, 'WATCH');
  assert.equal(mapped[0].requiresSecondaryVerification, true);
  assert.equal(mapped[0].hasContact, true);
  assert.deepEqual(mapped[0].contacts, [{ type: 'email', value: 'vk-cars@example.ru', usage: '公开页面邮箱' }]);
  assert.equal(mapped[0].evidenceNote.includes('High 二次复核'), true);
  assert.equal(mapped[0].riskMarkers.includes('强重复阻断'), true);
  assert.equal(mapped[0].duplicateSignals.hasStrongDuplicate, true);
});

test('staging lead detail maps evidence, AI audit, missing fields, and core gate to mobile detail shape', () => {
  const detail = mapStagingLeadDetailToLeadDetail({
    staging_lead: {
      id: 's1',
      customer_name: 'Auto City Moscow',
      country: 'Russia',
      city: 'Moscow',
      customer_type: 'local_dealer_secondary_dealer',
      contacts_json: [{ type: 'email', value: 'sales@dealer.example.ru', usage: '人工邮件触达' }],
      source_evidence: '官网公开页面展示进口二手车库存与邮箱。',
      recommended_grade: 'B',
      recommended_reason: '经营类型和公开联系方式清晰。',
      missing_fields: ['月采购量'],
      review_status: 'pending_review',
      source_risk_level: 'Low',
      requires_compliance_review: false,
    },
    candidate_url: {
      url: 'https://dealer.example.ru',
      source_risk_level: 'Low',
    },
    latest_page_snapshot: {
      page_title: 'Auto City Moscow',
      evidence_note: '页面包含库存、地址和公开邮箱。',
      read_status: 'success',
      captured_at: '2026-05-29T10:00:00',
    },
    ai_audit_summary: {
      model_name: 'gpt-test',
      prompt_version: 'lead-grading-v1',
      recommended_grade: 'B',
      recommended_reason: '公开证据完整，适合客服复核。',
      missing_fields: ['月采购量'],
    },
    core_gate: {
      status: 'ready',
      can_promote_to_core: true,
      reasons: ['来源和证据满足进入 core 的最低要求'],
    },
    has_do_not_contact_match: true,
    do_not_contact_customer_id: 'customer-dnc-1',
  });

  assert.equal(detail.id, 's1');
  assert.equal(detail.entityType, 'staging');
  assert.equal(detail.stagingLeadId, 's1');
  assert.equal(detail.customerId, '');
  assert.equal(detail.sources.length, 2);
  assert.equal(detail.sources[0].url, 'https://dealer.example.ru');
  assert.equal(detail.sources[1].evidence, '页面包含库存、地址和公开邮箱。');
  assert.equal(detail.aiRecommendation.reason, '公开证据完整，适合客服复核。');
  assert.deepEqual(detail.aiRecommendation.missingInfo, ['月采购量']);
  assert.equal(detail.coreGate.canPromoteToCore, true);
  assert.equal(detail.coreGate.reasons[0], '来源和证据满足进入 core 的最低要求');
  assert.equal(detail.doNotContact, true);
  assert.equal(detail.doNotContactCustomerId, 'customer-dnc-1');
});

test('inventory, outreach draft, and records map backend snake_case fields to mobile camelCase shape', () => {
  assert.deepEqual(
    mapInventoryItems({
      items: [
        {
          id: 'i1',
          brand: 'BYD',
          model: 'Song Plus',
          mileage_km: 1200,
          quoted_price: '23800',
          media_urls: ['https://example.test/car.jpg'],
          quote_status: 'confirmed',
          export_ready: true,
        },
      ],
    })[0],
    {
      id: 'i1',
      brand: 'BYD',
      model: 'Song Plus',
      year: null,
      mileageKm: 1200,
      vehicleType: 'Unknown',
      conditionSummary: 'Unknown',
      configuration: 'Unknown',
      quotedPrice: 23800,
      currency: 'USD',
      quoteStatus: 'confirmed',
      exportReady: true,
      mediaUrls: ['https://example.test/car.jpg'],
      validUntil: null,
    },
  );

  const draft = mapOutreachDraft({
    customer_id: 'c1',
    customer_name: 'Auto City',
    template_id: 'TMP-1',
    template_status: '可外发',
    version: 'v1',
    generated_at: '2026-05-29T00:00:00Z',
    subject: 'Hello',
    body: 'Body',
    refusal_path: 'Stop',
    risk_tips: ['人工发送'],
    audit: { model: 'gpt', prompt_version: 'p1', input_saved: true, output_saved: true },
  });
  assert.equal(draft.customerName, 'Auto City');
  assert.equal(draft.templateId, 'TMP-1');
  assert.equal(draft.refusalPath, 'Stop');
  assert.equal(draft.audit.promptVersion, 'p1');

  assert.equal(
    mapOutreachRecords({
      items: [{ id: 'r1', response_summary: '已发送', next_action: '等待回复', script_version: 'v1' }],
    })[0].response_summary,
    '已发送',
  );
});
