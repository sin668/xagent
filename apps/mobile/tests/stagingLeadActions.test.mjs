import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  buildGradeUpdatePayload,
  createStagingLeadActionsService,
  normalizeManualGrade,
} from '../src/services/stagingLeadActions.js';

test('人工调级把移动端 A/B/C/D/E 映射为后端枚举', () => {
  assert.equal(normalizeManualGrade('A级'), 'A');
  assert.equal(normalizeManualGrade('B'), 'B');
  assert.equal(normalizeManualGrade('C级'), 'C');
  assert.equal(normalizeManualGrade('D级'), 'Watch');
  assert.equal(normalizeManualGrade('E'), 'Invalid');
});

test('人工调级 payload 保留操作人和原因', () => {
  assert.deepEqual(buildGradeUpdatePayload({ grade: 'D级', reason: '质量不足', actor: 'ops-anna' }), {
    actor: 'ops-anna',
    reason: '质量不足',
    recommended_grade: 'Watch',
  });
});

test('staging lead actions service 调用真实调级端点', async () => {
  const calls = [];
  const service = createStagingLeadActionsService({
    client: {
      patch(endpoint, body) {
        calls.push([endpoint, body]);
        return Promise.resolve({ staging_lead_id: 'lead-1', recommended_grade: body.recommended_grade });
      },
    },
  });

  const result = await service.updateGrade('lead-1', { grade: 'E级', reason: '无联系方式' });

  assert.equal(result.recommended_grade, 'Invalid');
  assert.deepEqual(calls, [
    [
      '/staging-leads/lead-1/grade',
      {
        actor: '当前用户',
        reason: '无联系方式',
        recommended_grade: 'Invalid',
      },
    ],
  ]);
});
