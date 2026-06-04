import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  buildPhase2DashboardQuery,
  buildPhase2DashboardView,
  fetchPhase2Dashboard,
} from '../src/services/phase2Dashboard.js';

const phase2Payload = {
  summary: {
    source_candidate_count: 312,
    review_backlog_count: 55,
    auto_extraction_count: 184,
    agent_task_count: 9,
    failed_task_count: 2,
    llm_cost_total: 42.8,
    risk_event_count: 6,
    high_forbidden_risk_event_count: 3,
  },
  risk_distribution: {
    Low: 180,
    Medium: 94,
    High: 32,
    Forbidden: 6,
  },
  review_backlog: {
    pending: 12,
    high_risk_review: 38,
    needs_recheck: 5,
  },
  extraction_status_distribution: {
    queued: 60,
    running: 22,
    succeeded: 184,
    failed: 8,
  },
  failure_reasons: [
    {
      reason: 'schema_validation_failed',
      count: 2,
      agent_task_run_ids: ['run-1', 'run-2'],
    },
  ],
  llm_costs: {
    total_cost: 42.8,
    currency: 'CNY',
    items: [
      {
        agent_task_run_id: 'run-2048',
        task_type: 'SOURCE_DISCOVERY',
        status: 'succeeded',
        model: 'deepseek-chat',
        prompt_version: 'source-discovery-v1',
        cost_amount: 1.8,
        cost_currency: 'CNY',
        total_tokens: 4200,
      },
      {
        agent_task_run_id: 'run-2047',
        task_type: 'LEAD_EXTRACTION',
        status: 'running',
        model: 'deepseek-chat',
        prompt_version: 'lead-extraction-v2',
        cost_amount: 3.6,
        cost_currency: 'CNY',
        total_tokens: 9200,
      },
    ],
  },
  high_forbidden_risk_events: [
    {
      id: 'risk-1',
      task_id: 'task-1',
      channel: 'VK',
      risk_level: 'High',
      severity: 'high',
      resolution_status: 'open',
      event_type: 'high_risk_source',
      block_reason: 'High 来源进入人工复核，不得自动抽取。',
      pause_suggested: true,
      created_at: '2026-06-02T10:00:00Z',
    },
    {
      id: 'risk-2',
      task_id: 'task-2',
      channel: 'Forbidden Directory',
      risk_level: 'Forbidden',
      severity: 'critical',
      resolution_status: 'blocked',
      event_type: 'forbidden_source',
      block_reason: 'Forbidden 来源必须阻断。',
      pause_suggested: true,
      created_at: '2026-06-02T10:30:00Z',
    },
  ],
  guardrail: '不自动社交私信、不自动加好友；High/Forbidden 风险必须单独复核。',
};

test('phase2 dashboard view exposes real API metrics, task flow, pause thresholds and risk highlights', () => {
  const view = buildPhase2DashboardView(phase2Payload);

  assert.equal(view.summary.sourceCandidateCount, 312);
  assert.equal(view.summary.extractableSourceCount, 184);
  assert.equal(view.summary.highReviewBacklogCount, 38);
  assert.equal(view.summary.llmCostText, '¥42.80');
  assert.equal(view.summary.failedTaskCount, 2);
  assert.equal(view.summary.highForbiddenRiskEventCount, 3);

  assert.equal(view.taskFlow.length, 5);
  assert.equal(view.taskFlow[0].title, 'Source Discovery');
  assert.equal(view.taskFlow[3].metricText, '184 可抽取');

  assert.equal(view.pauseThresholds.highReviewBacklog.current, 38);
  assert.equal(view.pauseThresholds.highReviewBacklog.limit, 50);
  assert.equal(view.pauseThresholds.highReviewBacklog.percent, 76);
  assert.equal(view.pauseThresholds.schemaFailureRate.label, 'schema 失败率');

  assert.equal(view.llmTaskRuns[0].runId, 'run-2048');
  assert.equal(view.llmTaskRuns[0].costText, '¥1.80');
  assert.equal(view.llmTaskRuns[1].statusLabel, '运行中');

  assert.equal(view.highForbiddenRiskEvents.length, 2);
  assert.equal(view.highForbiddenRiskEvents[0].highlightClass, 'red');
  assert.equal(view.highForbiddenRiskEvents[1].riskLabel, '禁用');
  assert.equal(view.guardrail, phase2Payload.guardrail);
});

test('phase2 dashboard query encodes optional channel prefix', () => {
  assert.equal(buildPhase2DashboardQuery(), '');
  assert.equal(buildPhase2DashboardQuery({ channelPrefix: 'RU-VK' }), '?channel_prefix=RU-VK');
  assert.equal(buildPhase2DashboardQuery({ channelPrefix: 'RU Source' }), '?channel_prefix=RU+Source');
});

test('fetch phase2 dashboard calls backend phase2 endpoint', async () => {
  const requestedUrls = [];
  const payload = await fetchPhase2Dashboard({
    baseUrl: 'https://api.example.test/',
    channelPrefix: 'RU',
    fetcher: async (url) => {
      requestedUrls.push(url);
      return {
        ok: true,
        json: async () => phase2Payload,
      };
    },
  });

  assert.equal(requestedUrls[0], 'https://api.example.test/dashboard/phase2?channel_prefix=RU');
  assert.equal(payload.summary.source_candidate_count, 312);
});
