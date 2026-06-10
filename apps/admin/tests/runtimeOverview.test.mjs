import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  buildRuntimeOverviewView,
  fetchRuntimeOverview,
} from '../src/services/runtimeOverview.js';

const overviewPayload = {
  summary: {
    candidate_count: 120,
    response_rate: 0.32,
  },
  channel_outputs: [
    {
      channel_name: 'official_website',
      display_name: '官网 / 公开目录',
      risk_level: 'Low',
      risk_status: 'active',
      candidate_count: 48,
      b_grade_count: 9,
      c_grade_count: 4,
      bc_grade_count: 13,
    },
    {
      channel_name: 'yandex_maps',
      display_name: '地图 / Drom / 公开论坛',
      risk_level: 'Medium',
      risk_status: 'researching',
      candidate_count: 51,
      b_grade_count: 5,
      c_grade_count: 3,
      bc_grade_count: 8,
    },
  ],
  team_queues: {
    operations: { count: 12, items: [] },
    customer_service: { count: 18, items: [] },
    sales: { count: 6, items: [] },
  },
};

const phase2Payload = {
  summary: {
    source_candidate_count: 126,
    auto_extraction_count: 84,
    review_backlog_count: 12,
    llm_cost_total: 18.6,
  },
  high_forbidden_risk_events: [
    {
      id: 'risk-1',
      channel: 'VK',
      risk_level: 'High',
      event_type: 'high_risk_source',
      block_reason: '只读发现，不进入自动任务。',
      created_at: '2026-06-10T09:00:00Z',
    },
  ],
  guardrail: 'High 不入自动任务，C 级必须复核。',
};

const phase3Payload = {
  customer_acceptance: {
    promoted_customer_count: 31,
  },
  enrichment: {
    staging_lead_count: 84,
  },
  cleanup: {
    executed_count: 9,
  },
  risk: {
    risk_violation_count: 0,
  },
};

test('runtime overview view uses real API aggregates for summary cards and overview sections', () => {
  const view = buildRuntimeOverviewView({
    overview: overviewPayload,
    phase2: phase2Payload,
    phase3: phase3Payload,
  });

  assert.equal(view.summaryCards[0].label, '线索来源URL');
  assert.equal(view.summaryCards[0].value, 126);
  assert.equal(view.summaryCards[1].label, '线索池线索');
  assert.equal(view.summaryCards[1].value, 84);
  assert.equal(view.summaryCards[2].label, '晋级客户');
  assert.equal(view.summaryCards[2].value, 31);
  assert.equal(view.summaryCards[3].label, '被清洗线索');
  assert.equal(view.summaryCards[3].value, 9);

  assert.equal(view.channels.length, 2);
  assert.equal(view.funnel[0].value, 126);
  assert.equal(view.funnel[1].value, 84);
  assert.equal(view.hero.statusText, '运行中');
  assert.equal(view.insights.length, 3);
  assert.equal(view.riskEvents.length, 1);
});

test('fetch runtime overview calls three real backend endpoints', async () => {
  const requestedUrls = [];
  const payload = await fetchRuntimeOverview({
    baseUrl: 'https://api.example.test/',
    fetcher: async (url) => {
      requestedUrls.push(url);
      if (url.endsWith('/dashboard/admin-overview')) {
        return { ok: true, json: async () => overviewPayload };
      }
      if (url.endsWith('/dashboard/phase2')) {
        return { ok: true, json: async () => phase2Payload };
      }
      if (url.endsWith('/phase3-dashboard/metrics')) {
        return { ok: true, json: async () => phase3Payload };
      }
      throw new Error(`Unexpected url: ${url}`);
    },
  });

  assert.deepEqual(requestedUrls, [
    'https://api.example.test/dashboard/admin-overview',
    'https://api.example.test/dashboard/phase2',
    'https://api.example.test/phase3-dashboard/metrics',
  ]);
  assert.equal(payload.overview.summary.candidate_count, 120);
  assert.equal(payload.phase2.summary.source_candidate_count, 126);
  assert.equal(payload.phase3.customer_acceptance.promoted_customer_count, 31);
});
