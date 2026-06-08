import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  buildCustomerFollowupPayload,
  buildFollowupTimeline,
  createCustomerFollowupsService,
  getFollowupHardBlockTip,
  mapCustomerFollowup,
} from '../src/services/customerFollowups.js';

const followupRows = [
  {
    id: 'followup-1',
    customer_id: 'customer-1',
    owner_id: 'cs-a',
    team: 'customer_service',
    followup_type: 'email',
    content: '人工发送后记录客户反馈。',
    customer_feedback: '客户询问 Toyota Camry 数量。',
    next_action: '明天确认预算',
    next_followup_at: '2026-06-05T10:00:00+08:00',
    triggered_dnc: false,
    triggered_compliance_review: false,
    created_by: 'cs-a',
    created_at: '2026-06-04T15:00:00+08:00',
  },
];

test('客户跟进 mapper 展示人工跟进记录和下一次跟进时间', () => {
  const mapped = mapCustomerFollowup(followupRows[0]);

  assert.equal(mapped.id, 'followup-1');
  assert.equal(mapped.title, 'customer_service · email');
  assert.equal(mapped.content, '人工发送后记录客户反馈。');
  assert.equal(mapped.customerFeedback, '客户询问 Toyota Camry 数量。');
  assert.equal(mapped.nextAction, '明天确认预算');
  assert.equal(mapped.nextFollowupAt, '2026-06-05T10:00:00+08:00');
  assert.equal(mapped.auditText, '记录人：cs-a · 2026-06-04T15:00:00+08:00');
});

test('客户跟进时间线合并触达历史和跟进记录并保留人工记录提示', () => {
  const timeline = buildFollowupTimeline({
    followups: followupRows.map(mapCustomerFollowup),
    outreachHistory: [
      {
        id: 'outreach-1',
        channel: 'email',
        status: 'ready_for_manual_send',
        responseSummary: '草稿待人工发送',
        nextAction: '人工发送后记录结果',
        createdAt: '2026-06-03T10:00:00+08:00',
      },
    ],
  });

  assert.equal(timeline.length, 2);
  assert.equal(timeline[0].kind, 'followup');
  assert.match(timeline[0].note, /人工记录/);
  assert.equal(timeline[1].kind, 'outreach');
});

test('新增跟进 payload 只写 CRM 跟进记录，不包含发送类字段', () => {
  const payload = buildCustomerFollowupPayload({
    customerId: '11111111-1111-4111-8111-111111111111',
    ownerId: 'cs-a',
    team: 'customer_service',
    followupType: 'email',
    content: '人工记录客户反馈。',
    customerFeedback: '客户要求停止联系。',
    nextAction: '标记勿扰',
    nextFollowupAt: '2026-06-05T10:00:00+08:00',
    triggeredDnc: true,
    triggeredComplianceReview: false,
    createdBy: 'cs-a',
  });

  assert.deepEqual(payload, {
    customer_id: '11111111-1111-4111-8111-111111111111',
    owner_id: 'cs-a',
    team: 'customer_service',
    followup_type: 'email',
    content: '人工记录客户反馈。',
    customer_feedback: '客户要求停止联系。',
    next_action: '标记勿扰',
    next_followup_at: '2026-06-05T10:00:00+08:00',
    triggered_dnc: true,
    triggered_compliance_review: false,
    created_by: 'cs-a',
  });
  assert.ok(!('send_message' in payload));
  assert.ok(!('auto_send' in payload));
});

test('标记勿扰时展示硬阻断影响', () => {
  assert.match(getFollowupHardBlockTip({ triggeredDnc: true }), /勿扰客户不得再次进入触达队列/);
});

test('客户跟进服务调用真实 followups API 列表和新增接口', async () => {
  const calls = [];
  const service = createCustomerFollowupsService({
    client: {
      get(endpoint) {
        calls.push(['get', endpoint]);
        return Promise.resolve(followupRows);
      },
      post(endpoint, payload) {
        calls.push(['post', endpoint, payload]);
        return Promise.resolve({ ...payload, id: 'created-followup' });
      },
    },
  });

  const list = await service.listFollowups('customer-1');
  const created = await service.createFollowup('customer-1', {
    customerId: 'customer-1',
    ownerId: 'cs-a',
    team: 'customer_service',
    followupType: 'internal_note',
    content: '人工记录。',
    createdBy: 'cs-a',
  });

  assert.equal(list[0].id, 'followup-1');
  assert.equal(created.id, 'created-followup');
  assert.equal(calls[0][1], '/customers/customer-1/followups');
  assert.equal(calls[1][1], '/customers/customer-1/followups');
});
