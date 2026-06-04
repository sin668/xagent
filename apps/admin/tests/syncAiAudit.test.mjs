import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  buildSyncAiAuditQuery,
  buildSyncAiAuditView,
  fetchSyncAiAuditDashboard,
} from '../src/services/syncAiAudit.js';

test('sync ai audit view exposes sync counts, failures, ai status, and blocked reasons', () => {
  const view = buildSyncAiAuditView({
    summary: {
      latest_sync_at: '2026-05-28T10:42:00',
      sync_success_count: 10,
      sync_failure_count: 2,
      ai_task_count: 3,
      ai_blocked_count: 1,
    },
    sync_logs: [
      {
        object_name: '渠道来源',
        status: 'failed',
        success_count: 0,
        failure_count: 2,
        error_summary: '字段 渠道风险等级 缺失',
        finished_at: '2026-05-28T10:42:00',
      },
    ],
    ai_audit_logs: [
      {
        task_type: 'outreach_draft',
        model_name: 'gpt-test',
        prompt_version: 'draft-v1',
        status: 'blocked',
        risk: 'blocked',
        risk_blocked: true,
        risk_block_reason: 'High 风险渠道只允许政策研究和人工小样本。',
        executed_at: '2026-05-28T10:43:00',
      },
    ],
  });

  assert.equal(view.summary.syncSuccessCount, 10);
  assert.equal(view.summary.syncFailureCount, 2);
  assert.equal(view.summary.aiTaskCount, 3);
  assert.equal(view.summary.aiBlockedCount, 1);
  assert.equal(view.syncLogs[0].statusLabel, '失败');
  assert.equal(view.syncLogs[0].errorSummary, '字段 渠道风险等级 缺失');
  assert.equal(view.aiAuditLogs[0].statusLabel, '已阻断');
  assert.equal(view.aiAuditLogs[0].riskBlockReason, 'High 风险渠道只允许政策研究和人工小样本。');
});

test('sync ai audit query supports task type and status filters', () => {
  assert.equal(
    buildSyncAiAuditQuery({ taskType: 'outreach_draft', status: 'blocked' }),
    '?task_type=outreach_draft&status=blocked',
  );
  assert.equal(buildSyncAiAuditQuery({}), '');
});

test('fetch sync ai audit dashboard uses backend contract', async () => {
  const requestedUrls = [];
  const payload = await fetchSyncAiAuditDashboard({
    baseUrl: 'https://api.example.test',
    taskType: 'lead_extraction',
    status: 'succeeded',
    fetcher: async (url) => {
      requestedUrls.push(url);
      return {
        ok: true,
        json: async () => ({ summary: {}, sync_logs: [], ai_audit_logs: [] }),
      };
    },
  });

  assert.equal(
    requestedUrls[0],
    'https://api.example.test/sync/audit-dashboard?task_type=lead_extraction&status=succeeded',
  );
  assert.equal(payload.ai_audit_logs.length, 0);
});
