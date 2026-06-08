import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  createCustomersService,
  getCustomerDetailViewModel,
  mapCustomerDetail,
} from '../src/services/customers.js';

const customerDetailPayload = {
  id: '4d6a0c8e-1d73-4b7e-a7ff-2fe7d8e5d1ad',
  profile: {
    id: '4d6a0c8e-1d73-4b7e-a7ff-2fe7d8e5d1ad',
    name: 'AutoCity Vladivostok',
    country: 'Russia',
    city: 'Vladivostok',
    customer_type: 'local_dealer_secondary_dealer',
    grade: 'C',
    status: 'ready_for_sales',
    owner: 'sales-a',
    owner_team: 'export_sales',
  },
  contacts: [
    {
      id: 'contact-1',
      type: 'email',
      value: 'sales@autocity-vl.example',
      label: 'primary',
      source_url: 'https://autocity.example/contact',
      evidence_note: '官网联系页公开邮箱',
      is_primary: true,
      is_verified: true,
    },
  ],
  sources: [
    {
      id: 'source-1',
      platform: 'official_website',
      source_url: 'https://autocity.example',
      source_title: 'AutoCity',
      evidence_note: '官网展示车辆销售业务和联系页',
      risk_level: 'Low',
      collected_by: 'ops-a',
    },
  ],
  vehicle_intents: [
    {
      id: 'intent-1',
      brand: 'Toyota',
      model: 'Camry',
      quantity: 3,
      budget_range: '',
      purchase_frequency: 'monthly',
      concerns: ['车况', '手续'],
      status: 'active',
      label: 'Toyota Camry',
    },
  ],
  outreach_history: [
    {
      id: 'outreach-1',
      channel: 'email',
      status: 'ready_for_manual_send',
      response_summary: '草稿待人工发送',
      next_action: '人工发送后记录结果',
      script_version: 'outreach-template-v1',
    },
  ],
  followups: [
    {
      id: 'followup-1',
      owner_id: 'cs-a',
      team: 'customer_service',
      followup_type: 'internal_note',
      content: '确认采购频率和目标价位',
      next_action: '今日待跟进',
      next_followup_at: '2026-06-04T10:00:00+08:00',
      created_by: 'cs-a',
    },
  ],
  compliance_status: {
    requires_review: true,
    latest_status: 'pending',
    latest_reason: 'C级客户报价/合同前必须合规复核',
    reviewer: null,
  },
  do_not_contact: {
    enabled: true,
    reason: '客户拒绝继续联系',
    marked_by: 'cs-a',
    marked_at: '2026-06-04T09:00:00+08:00',
  },
  pending_fields: ['budget_range', 'delivery_city'],
  source_traceability: {
    lead_sources_count: 1,
    contact_evidence_count: 1,
    source_urls: ['https://autocity.example', 'https://autocity.example/contact'],
    has_enrichment_evidence: true,
  },
  completeness_score: 82,
  next_action: '勿扰客户，不得触达',
  next_action_priority: 99,
};

test('客户详情 mapper 展示聚合资料、待补全字段、勿扰和 C 级合规状态', () => {
  const detail = mapCustomerDetail(customerDetailPayload);
  const view = getCustomerDetailViewModel(detail);

  assert.equal(detail.id, '4d6a0c8e-1d73-4b7e-a7ff-2fe7d8e5d1ad');
  assert.equal(view.name, 'AutoCity Vladivostok');
  assert.equal(view.locationText, 'Russia · Vladivostok');
  assert.equal(view.gradeLabel, 'C 级客户');
  assert.equal(view.customerTypeText, 'local_dealer_secondary_dealer');
  assert.equal(view.ownerTeamText, 'export_sales');
  assert.equal(view.contactCountText, '1 条');
  assert.equal(view.sourceCountText, '1 条');
  assert.equal(view.vehicleIntentCountText, '1 条');
  assert.equal(view.outreachCountText, '1 条');
  assert.equal(view.followupCountText, '1 条');
  assert.equal(view.doNotContactLabel, '勿扰客户');
  assert.equal(view.canCreateOutreachDraft, false);
  assert.equal(view.complianceLabel, 'C级合规待复核');
  assert.deepEqual(view.pendingFieldLabels, ['budget_range 待补全', 'delivery_city 待补全']);
  assert.equal(view.contacts[0].displayText, 'email · sales@autocity-vl.example');
  assert.equal(view.sources[0].evidenceText, '官网展示车辆销售业务和联系页');
  assert.equal(view.vehicleIntents[0].displayText, 'Toyota Camry · monthly · 3 台');
  assert.equal(view.outreachHistory[0].title, 'email · ready_for_manual_send');
  assert.equal(view.followups[0].title, 'customer_service · 今日待跟进');
});

test('客户详情服务通过 GET /customers/{id} 获取 core 聚合详情', async () => {
  const calls = [];
  const service = createCustomersService({
    client: {
      get(endpoint) {
        calls.push(endpoint);
        return Promise.resolve(customerDetailPayload);
      },
    },
  });

  const detail = await service.getCustomerDetail('4d6a0c8e-1d73-4b7e-a7ff-2fe7d8e5d1ad');

  assert.deepEqual(calls, ['/customers/4d6a0c8e-1d73-4b7e-a7ff-2fe7d8e5d1ad']);
  assert.equal(detail.profile.name, 'AutoCity Vladivostok');
});
