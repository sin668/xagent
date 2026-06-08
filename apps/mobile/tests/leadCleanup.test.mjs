import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  buildCleanupExecutePayload,
  buildCleanupReviewPayload,
  createLeadCleanupService,
  mapCleanupSuggestion,
} from '../src/services/leadCleanup.js';

const rawSuggestion = {
  id: 'suggestion-1',
  cleanup_run_id: 'run-1',
  staging_lead_id: 'lead-watch-1',
  suggestion_type: 'restore_from_watch',
  target_lead_id: 'lead-target-1',
  confidence_score: 0.87,
  reason: '该 Watch 线索新增公开邮箱和官网证据，具备恢复复核价值。',
  evidence_json: {
    evidence_note: '官网联系页公开邮箱；未登录、未互动。',
    evidence_links: ['https://dealer.example.ru/contact'],
    target_lead_name: 'AutoCity Moscow',
    high_risk_reason: '恢复 Watch 需要合规或管理员确认。',
  },
  recommended_action: '人工复核后恢复为 B 级待补全线索',
  review_status: 'pending',
  created_at: '2026-06-04T10:00:00Z',
  updated_at: '2026-06-04T10:00:00Z',
};

test('清洗建议 mapper 展示 suggestion_type、原因、证据、目标线索和权限提示', () => {
  const mapped = mapCleanupSuggestion(rawSuggestion);

  assert.equal(mapped.id, 'suggestion-1');
  assert.equal(mapped.suggestionType, 'restore_from_watch');
  assert.equal(mapped.suggestionTypeLabel, '恢复 Watch');
  assert.equal(mapped.stagingLeadId, 'lead-watch-1');
  assert.equal(mapped.targetLeadId, 'lead-target-1');
  assert.equal(mapped.targetLeadName, 'AutoCity Moscow');
  assert.equal(mapped.reason, '该 Watch 线索新增公开邮箱和官网证据，具备恢复复核价值。');
  assert.equal(mapped.evidenceNote, '官网联系页公开邮箱；未登录、未互动。');
  assert.equal(mapped.evidenceLinks[0], 'https://dealer.example.ru/contact');
  assert.equal(mapped.confidenceText, '87%');
  assert.equal(mapped.reviewStatusLabel, '待复核');
  assert.equal(mapped.requiresElevatedPermission, true);
  assert.match(mapped.permissionHint, /合规|管理员/);
});

test('清洗建议服务按真实后端查询参数列表、审批、拒绝和执行建议', async () => {
  const calls = [];
  const service = createLeadCleanupService({
    client: {
      get(endpoint) {
        calls.push(['GET', endpoint]);
        return Promise.resolve({ items: [rawSuggestion], total: 1 });
      },
      patch(endpoint, body) {
        calls.push(['PATCH', endpoint, body]);
        return Promise.resolve({ ...rawSuggestion, review_status: 'approved', reviewer_id: body.actor });
      },
      post(endpoint, body) {
        calls.push(['POST', endpoint, body]);
        return Promise.resolve({ ...rawSuggestion, review_status: 'executed', executed_by: body.actor });
      },
    },
  });

  const list = await service.listCleanupSuggestions({
    suggestionType: 'restore_from_watch',
    reviewStatus: 'pending',
    minConfidence: 0.8,
    leadId: '45d1480c-76c9-4297-86e8-f5a1f2e30d96',
    limit: 50,
  });
  await service.approveSuggestion('suggestion-1', { actor: 'ops-anna', actorRole: 'compliance', reviewNote: '证据充分' });
  await service.rejectSuggestion('suggestion-2', { actor: 'ops-anna', actorRole: 'ops', reviewNote: '证据不足' });
  await service.executeSuggestion('suggestion-1', { actor: 'ops-anna', actorRole: 'compliance', executionNote: '人工确认执行' });

  assert.equal(list.total, 1);
  assert.equal(list.items[0].suggestionTypeLabel, '恢复 Watch');
  assert.deepEqual(calls, [
    [
      'GET',
      '/lead-cleanup/suggestions?suggestion_type=restore_from_watch&review_status=pending&confidence=0.8&lead=45d1480c-76c9-4297-86e8-f5a1f2e30d96&limit=50',
    ],
    ['PATCH', '/lead-cleanup/suggestions/suggestion-1/approve', { actor: 'ops-anna', actor_role: 'compliance', review_note: '证据充分' }],
    ['PATCH', '/lead-cleanup/suggestions/suggestion-2/reject', { actor: 'ops-anna', actor_role: 'ops', review_note: '证据不足' }],
    ['POST', '/lead-cleanup/suggestions/suggestion-1/execute', { actor: 'ops-anna', actor_role: 'compliance', execution_note: '人工确认执行' }],
  ]);
});

test('清洗建议 review 和 execute payload 保留操作人、角色和审计备注', () => {
  assert.deepEqual(buildCleanupReviewPayload({ actor: 'ops-anna', actorRole: 'admin', reviewNote: '同意归并' }), {
    actor: 'ops-anna',
    actor_role: 'admin',
    review_note: '同意归并',
  });
  assert.deepEqual(buildCleanupExecutePayload({ actor: 'ops-anna', actorRole: 'admin', executionNote: '执行归并' }), {
    actor: 'ops-anna',
    actor_role: 'admin',
    execution_note: '执行归并',
  });
});
