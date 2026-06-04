import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  buildAdminOverviewView,
  fetchAdminOverview,
  queueCount,
} from '../src/services/adminOverview.js';

test('admin overview view exposes global metrics, queues, risk events, and blocked reasons', () => {
  const view = buildAdminOverviewView({
    summary: {
      candidate_count: 12,
      b_grade_count: 5,
      c_grade_count: 3,
      bc_grade_count: 8,
      response_rate: 0.25,
      sla_risk_count: 2,
    },
    channel_outputs: [
      {
        channel_name: 'official_website',
        display_name: '官网',
        risk_level: 'Low',
        risk_status: 'active',
        candidate_count: 8,
        b_grade_count: 4,
        c_grade_count: 2,
        bc_grade_count: 6,
        invalid_rate: 0.125,
        investment_recommendation: 'candidate',
      },
    ],
    team_queues: {
      operations: {
        count: 1,
        items: [{ customer_name: 'Moscow Dealer', grade: 'B', owner: 'Ops', status: 'pending_review' }],
      },
      customer_service: {
        count: 2,
        items: [],
      },
      sales: {
        count: 3,
        items: [],
      },
    },
    risk_events: [
      {
        task_type: 'risk_block',
        source_url: 'https://vk.com/example',
        risk_blocked: true,
        risk_block_reason: 'High 风险社媒禁止自动采集。',
      },
    ],
    blocked_tasks: [
      {
        task_type: 'risk_block',
        risk_block_reason: 'High 风险社媒禁止自动采集。',
      },
    ],
  });

  assert.equal(view.summary.candidateCount, 12);
  assert.equal(view.summary.bcGradeCount, 8);
  assert.equal(view.summary.responseRateText, '25%');
  assert.equal(view.summary.slaRiskCount, 2);
  assert.equal(view.channelOutputs[0].bcText, 'B 4 / C 2');
  assert.equal(queueCount(view.teamQueues.customerService), 2);
  assert.equal(view.queueSummaryText, '运营 1 / 客服 2 / 销售 3');
  assert.equal(view.riskEvents[0].riskBlockReason, 'High 风险社媒禁止自动采集。');
  assert.equal(view.blockedTasks[0].reasonVisible, true);
});

test('fetch admin overview uses the backend overview contract', async () => {
  const requestedUrls = [];
  const payload = await fetchAdminOverview({
    baseUrl: 'https://api.example.test',
    fetcher: async (url) => {
      requestedUrls.push(url);
      return {
        ok: true,
        json: async () => ({ summary: {}, channel_outputs: [], team_queues: {}, risk_events: [], blocked_tasks: [] }),
      };
    },
  });

  assert.equal(requestedUrls[0], 'https://api.example.test/dashboard/admin-overview');
  assert.equal(payload.channel_outputs.length, 0);
});
