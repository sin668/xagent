import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  buildEmailQualityDashboardView,
  fetchEmailQualityDashboard,
} from '../src/services/emailQualityDashboard.js';

const promptTemplatesPayload = {
  items: [
    { id: 'p1', task_type: 'EMAIL_REPLY_DRAFT', status: 'active', is_default: true },
    { id: 'p2', task_type: 'EMAIL_REPLY_AUTO_SEND_CHECK', status: 'active', is_default: true },
    { id: 'p3', task_type: 'EMAIL_REPLY_SEND', status: 'draft', is_default: false },
  ],
};

const embeddingMetricsPayload = {
  published_knowledge_count: 100,
  embedding_task_count: 102,
  ready_count: 96,
  pending_count: 3,
  failed_count: 3,
  ready_rate: 0.96,
  total_retry_count: 4,
  go_no_go_ready: true,
};

const aiAuditPayload = {
  summary: {
    ai_task_count: 50,
    ai_blocked_count: 2,
  },
  ai_audit_logs: [
    { id: 'a1', task_type: 'EMAIL_REPLY', status: 'succeeded', risk_blocked: false },
    { id: 'a2', task_type: 'EMAIL_REPLY', status: 'succeeded', risk_blocked: false },
    { id: 'a3', task_type: 'EMAIL_REPLY', status: 'blocked', risk_blocked: true, risk_block_reason: 'DNC request' },
  ],
};

const draftsPayload = {
  items: [
    {
      id: 'd1',
      status: 'sent',
      auto_send_allowed: true,
      manual_review_required: false,
      auto_send_decision_json: { route: 'auto_send' },
      send_attempts: [{ status: 'sent' }],
    },
    {
      id: 'd2',
      status: 'manual_sent',
      auto_send_allowed: false,
      manual_review_required: true,
      reviewed_by: 'Ada',
      send_attempts: [{ status: 'sent' }],
    },
    {
      id: 'd3',
      status: 'sent',
      auto_send_allowed: true,
      manual_review_required: false,
      auto_send_decision_json: { route: 'auto_send' },
      send_attempts: [{ status: 'bounced', bounce_reason: 'mailbox unavailable' }],
    },
    {
      id: 'd4',
      status: 'blocked',
      auto_send_allowed: false,
      manual_review_required: true,
      auto_send_decision_json: { route: 'block', hard_block_reasons: ['DNC'] },
      manual_review_reason: 'DNC',
      send_attempts: [],
    },
    {
      id: 'd5',
      status: 'blocked',
      auto_send_allowed: false,
      manual_review_required: true,
      auto_send_decision_json: { route: 'block', hard_block_reasons: ['D/E grade'] },
      manual_review_reason: 'D/E grade',
      send_attempts: [],
    },
  ],
};

const riskEventsPayload = {
  summary: {
    total_count: 1,
    open_count: 1,
  },
  items: [
    {
      id: 'risk-1',
      severity: 'high',
      event_type: 'language_misfire',
      description: 'language uncertain',
      resolution_status: 'open',
    },
  ],
};

test('email quality dashboard view exposes prompt, embedding, agent, business, and risk metrics', () => {
  const view = buildEmailQualityDashboardView({
    promptTemplates: promptTemplatesPayload,
    embeddingMetrics: embeddingMetricsPayload,
    aiAudit: aiAuditPayload,
    drafts: draftsPayload,
    riskEvents: riskEventsPayload,
  });

  assert.equal(view.summary.promptCoverageText, '66.7%');
  assert.equal(view.summary.embeddingReadyText, '96.0%');
  assert.equal(view.summary.aiGenerationSuccessText, '66.7%');
  assert.equal(view.summary.manualAdoptionText, '50.0%');
  assert.equal(view.summary.autoSendSuccessText, '50.0%');
  assert.equal(view.summary.bounceRateText, '33.3%');
  assert.equal(view.riskGate.dncBlockedCount, 1);
  assert.equal(view.riskGate.deGradeBlockedCount, 1);
  assert.equal(view.riskGate.riskEventCount, 1);
  assert.equal(view.riskGate.statusLabel, '需暂停自动发送');
  assert.equal(view.goNoGo.statusLabel, '暂停');
  assert.equal(view.goNoGo.reasons.includes('存在未关闭风险事件'), true);
});

test('email quality dashboard view returns go candidate when all hard gates are green', () => {
  const view = buildEmailQualityDashboardView({
    promptTemplates: {
      items: [
        { task_type: 'EMAIL_REPLY_DRAFT', status: 'active', is_default: true },
        { task_type: 'EMAIL_REPLY_AUTO_SEND_CHECK', status: 'active', is_default: true },
        { task_type: 'EMAIL_REPLY_SEND', status: 'active', is_default: true },
      ],
    },
    embeddingMetrics: { ready_rate: 0.98, ready_count: 98, failed_count: 0 },
    aiAudit: { ai_audit_logs: [{ status: 'succeeded' }, { status: 'succeeded' }] },
    drafts: { items: [{ auto_send_allowed: true, status: 'sent', send_attempts: [{ status: 'sent' }] }] },
    riskEvents: { summary: { total_count: 0, open_count: 0 }, items: [] },
  });

  assert.equal(view.summary.promptCoverageText, '100.0%');
  assert.equal(view.riskGate.statusLabel, '硬风险门禁通过');
  assert.equal(view.goNoGo.statusLabel, 'Go 候选');
  assert.equal(view.goNoGo.statusClass, 'green');
});

test('fetch email quality dashboard calls real metrics APIs', async () => {
  const requestedUrls = [];
  const payload = await fetchEmailQualityDashboard({
    baseUrl: 'https://api.example.test/',
    fetcher: async (url) => {
      requestedUrls.push(url);
      if (url.endsWith('/dashboard/phase5-quality-foundation')) {
        return {
          ok: true,
          json: async () => ({
            prompt_metrics: { prompt_coverage_rate: 1, covered_prompt_file_count: 2 },
            knowledge_metrics: { published_knowledge_count: 3 },
            embedding_metrics: embeddingMetricsPayload,
            go_no_go_ready: true,
            go_no_go_reasons: [],
          }),
        };
      }
      if (url.endsWith('/llm-prompt-templates')) return { ok: true, json: async () => promptTemplatesPayload };
      if (url.endsWith('/knowledge/embeddings/metrics')) return { ok: true, json: async () => embeddingMetricsPayload };
      if (url.endsWith('/sync/audit-dashboard')) return { ok: true, json: async () => aiAuditPayload };
      if (url.endsWith('/email-reply/drafts?limit=500')) return { ok: true, json: async () => draftsPayload };
      if (url.endsWith('/dashboard/risk-events')) return { ok: true, json: async () => riskEventsPayload };
      throw new Error(`Unexpected URL: ${url}`);
    },
  });

  assert.deepEqual(requestedUrls, [
    'https://api.example.test/dashboard/phase5-quality-foundation',
    'https://api.example.test/llm-prompt-templates',
    'https://api.example.test/knowledge/embeddings/metrics',
    'https://api.example.test/sync/audit-dashboard',
    'https://api.example.test/email-reply/drafts?limit=500',
    'https://api.example.test/dashboard/risk-events',
  ]);
  assert.equal(payload.qualityFoundation.prompt_metrics.prompt_coverage_rate, 1);
  assert.equal(payload.embeddingMetrics.ready_rate, 0.96);
  assert.equal(payload.riskEvents.items.length, 1);
});
