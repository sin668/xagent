import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  buildInventoryMatchView,
  buildMatchDecisionPayload,
  filterRecommendableMatches,
} from '../src/services/inventoryMatch.js';

const matches = [
  {
    matchId: 'match-byd',
    inventoryExternalId: 'BYD-001',
    brand: 'BYD',
    model: 'Song Plus',
    year: 2023,
    vehicleType: 'SUV',
    conditionSummary: '准新车，检测报告可提供',
    quotedPrice: 23800,
    currency: 'USD',
    exportReady: true,
    validUntil: '2099-01-01T00:00:00Z',
    priorityRecommendable: true,
    recommendationReason: '车型匹配 SUV；年份满足 2022+；车况: 准新车；价格有效期至 2099-01-01；可出口。',
    riskTips: ['C级线索报价前必须合规复核'],
    requiresComplianceReview: true,
  },
  {
    matchId: 'match-old',
    inventoryExternalId: 'OLD-001',
    brand: 'Changan',
    model: 'CS75 Plus',
    year: 2020,
    vehicleType: 'SUV',
    conditionSummary: '旧库存',
    quotedPrice: 21500,
    currency: 'USD',
    exportReady: true,
    validUntil: '2026-05-01T00:00:00Z',
    priorityRecommendable: false,
    recommendationReason: '年份不足。',
    riskTips: ['车源已过期'],
    requiresComplianceReview: true,
  },
];

test('inventory match view exposes reason, expiry, export status, and compliance warning', () => {
  const view = buildInventoryMatchView(matches[0]);

  assert.equal(view.title, 'BYD Song Plus 2023');
  assert.equal(view.reason.includes('车型匹配 SUV'), true);
  assert.equal(view.reason.includes('价格有效期'), true);
  assert.equal(view.exportLabel, '可出口');
  assert.equal(view.expiryLabel, '有效至 2099-01-01');
  assert.equal(view.riskTips.includes('C级线索报价前必须合规复核'), true);
  assert.equal(view.quoteDisclaimer, '推荐车源仅用于人工报价前评估，不等同于正式报价。');
});

test('only priority recommendable matches can be pushed to quote flow', () => {
  assert.deepEqual(
    filterRecommendableMatches(matches).map((item) => item.matchId),
    ['match-byd'],
  );

  const advance = buildMatchDecisionPayload({
    decision: 'advance_quote',
    owner: 'Nikita',
    note: '进入报价前合规复核',
  });
  assert.equal(advance.decision, 'advance_quote');
  assert.equal(advance.formal_quote_allowed, false);

  const notMatch = buildMatchDecisionPayload({
    decision: 'not_match',
    owner: 'Nikita',
    note: '预算不匹配',
  });
  assert.equal(notMatch.decision, 'not_match');
});
