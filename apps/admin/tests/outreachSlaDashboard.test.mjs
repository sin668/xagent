import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  buildOutreachSlaDashboardView,
  buildOutreachSlaQuery,
  fetchOutreachSlaDashboard,
  isSlaRisk,
} from '../src/services/outreachSlaDashboard.js';

test('outreach SLA dashboard view exposes reply rate, overdue count, and risk queue', () => {
  const view = buildOutreachSlaDashboardView({
    summary: {
      sent_count: 3,
      replied_count: 1,
      response_rate: 1 / 3,
      pending_count: 4,
      overdue_count: 2,
      compliance_waiting_count: 1,
      sla_risk_count: 3,
    },
    queue: [
      {
        customer_name: 'B Dealer',
        grade: 'B',
        owner: 'Anna',
        sla_hours: 48,
        waiting_hours: 50,
        risk_status: 'overdue',
        next_action: '立即跟进',
      },
      {
        customer_name: 'C Dealer',
        grade: 'C',
        owner: 'Boris',
        sla_hours: 24,
        waiting_hours: 30,
        risk_status: 'compliance_waiting',
        next_action: '等待合规复核',
      },
    ],
  });

  assert.equal(view.summary.sentCount, 3);
  assert.equal(view.summary.repliedCount, 1);
  assert.equal(view.summary.responseRateText, '33%');
  assert.equal(view.summary.overdueCount, 2);
  assert.equal(view.summary.complianceWaitingCount, 1);
  assert.equal(view.queue[0].slaLabel, 'B级 48小时');
  assert.equal(view.queue[0].riskLabel, '已超时');
  assert.equal(view.queue[1].riskLabel, '合规等待');
  assert.equal(isSlaRisk(view.queue[0]), true);
  assert.equal(isSlaRisk(view.queue[1]), true);
});

test('outreach SLA query supports owner, grade, and channel filters', () => {
  assert.equal(
    buildOutreachSlaQuery({ owner: 'Anna', grade: 'B', channel: 'email' }),
    '?owner=Anna&grade=B&channel=email',
  );
  assert.equal(buildOutreachSlaQuery({}), '');
});

test('fetch outreach SLA dashboard uses backend contract', async () => {
  const requestedUrls = [];
  const payload = await fetchOutreachSlaDashboard({
    baseUrl: 'https://api.example.test',
    owner: 'Anna',
    grade: 'B',
    fetcher: async (url) => {
      requestedUrls.push(url);
      return {
        ok: true,
        json: async () => ({ summary: { sent_count: 0 }, queue: [] }),
      };
    },
  });

  assert.equal(requestedUrls[0], 'https://api.example.test/dashboard/outreach-sla?owner=Anna&grade=B');
  assert.equal(payload.queue.length, 0);
});
