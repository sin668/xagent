import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  buildRoiMetricsQuery,
  buildRoiMetricsView,
  fetchRoiMetrics,
  roiCanOverrideCompliance,
} from '../src/services/roiMetrics.js';

test('ROI metrics view exposes cost per effective lead, reply, and sales opportunity', () => {
  const view = buildRoiMetricsView({
    summary: {
      total_cost: 200,
      labor_cost: 120,
      ai_api_cost: 20,
      tool_cost: 60,
      effective_lead_count: 2,
      reply_count: 1,
      sales_opportunity_count: 1,
      cost_per_effective_lead: 100,
      cost_per_reply: 200,
      cost_per_sales_opportunity: 200,
    },
    compliance_guardrail: 'ROI 不能作为绕过合规限制的理由。',
  });

  assert.equal(view.summary.totalCostText, '$200');
  assert.equal(view.summary.costPerEffectiveLeadText, '$100');
  assert.equal(view.summary.costPerReplyText, '$200');
  assert.equal(view.summary.costPerSalesOpportunityText, '$200');
  assert.equal(view.guardrail.includes('不能作为绕过合规限制'), true);
  assert.equal(roiCanOverrideCompliance(), false);
});

test('ROI metrics query supports channel and date filters', () => {
  assert.equal(
    buildRoiMetricsQuery({ channel: 'official_website', dateFrom: '2026-05-01', dateTo: '2026-05-28' }),
    '?channel=official_website&date_from=2026-05-01&date_to=2026-05-28',
  );
  assert.equal(buildRoiMetricsQuery({}), '');
});

test('fetch ROI metrics uses backend contract', async () => {
  const requestedUrls = [];
  const payload = await fetchRoiMetrics({
    baseUrl: 'https://api.example.test',
    channel: 'official_website',
    fetcher: async (url) => {
      requestedUrls.push(url);
      return {
        ok: true,
        json: async () => ({ summary: { total_cost: 0 }, compliance_guardrail: 'ROI 不能作为绕过合规限制的理由。' }),
      };
    },
  });

  assert.equal(requestedUrls[0], 'https://api.example.test/dashboard/roi-metrics?channel=official_website');
  assert.equal(payload.summary.total_cost, 0);
});
