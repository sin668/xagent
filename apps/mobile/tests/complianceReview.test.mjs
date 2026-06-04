import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  buildComplianceReviewView,
  canMarkQuoted,
  getAiRiskTip,
} from '../src/services/complianceReview.js';

test('C grade pending compliance review blocks quoted status and exposes risk tip only', () => {
  const view = buildComplianceReviewView({
    grade: 'C',
    status: 'pending',
    reviewer: null,
    riskNote: '付款、物流、清关仍需人工确认',
  });

  assert.equal(view.label, '待合规复核');
  assert.equal(view.quoteContractBlocked, true);
  assert.equal(canMarkQuoted(view), false);
  assert.equal(getAiRiskTip().includes('AI仅提示风险'), true);
  assert.equal(view.aiLegalConclusionAllowed, false);
});

test('approved compliance review shows reviewer, time, decision, and allows quote gate to continue', () => {
  const view = buildComplianceReviewView({
    grade: 'C',
    status: 'approved',
    reviewer: 'Compliance Anna',
    reviewedAt: '2026-05-28T12:00:00Z',
    reason: '贸易路径初步可行',
    riskNote: '付款、物流、清关仍需人工确认',
  });

  assert.equal(view.label, '合规已通过');
  assert.equal(view.reviewerText, 'Compliance Anna · 2026-05-28');
  assert.equal(view.reason, '贸易路径初步可行');
  assert.equal(view.riskNote, '付款、物流、清关仍需人工确认');
  assert.equal(view.quoteContractBlocked, false);
  assert.equal(canMarkQuoted(view), true);
});
