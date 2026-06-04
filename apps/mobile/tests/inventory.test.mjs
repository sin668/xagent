import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  buildInventoryCardView,
  filterPriorityInventory,
  getAiQuoteSafety,
} from '../src/services/inventory.js';

const baseItem = {
  id: 'byd-song-plus',
  brand: 'BYD',
  model: 'Song Plus',
  year: 2023,
  mileageKm: 12000,
  conditionSummary: '准新车，检测报告可提供',
  configuration: '旗舰版，四驱，黑色内饰',
  quotedPrice: 23800,
  currency: 'USD',
  quoteStatus: 'confirmed',
  exportReady: true,
  mediaUrls: ['https://example.com/byd.jpg', 'https://example.com/byd.mp4'],
  validUntil: '2099-01-01T00:00:00Z',
};

test('inventory card exposes required vehicle and quote fields', () => {
  const card = buildInventoryCardView(baseItem, { now: '2026-05-28T00:00:00Z' });

  assert.equal(card.title, 'BYD Song Plus 2023');
  assert.equal(card.meta.includes('12,000 km'), true);
  assert.equal(card.conditionSummary, '准新车，检测报告可提供');
  assert.equal(card.configuration, '旗舰版，四驱，黑色内饰');
  assert.equal(card.priceText, 'USD 23,800');
  assert.equal(card.mediaCountText, '2 个图片/视频');
  assert.equal(card.expiryLabel.includes('有效'), true);
  assert.equal(card.canAiQuote, true);
});

test('expired or unconfirmed inventory is not priority recommendable and cannot be quoted by AI', () => {
  const expired = {
    ...baseItem,
    id: 'expired',
    validUntil: '2026-05-01T00:00:00Z',
  };
  const pending = {
    ...baseItem,
    id: 'pending',
    quoteStatus: 'pending',
  };
  const blocked = filterPriorityInventory([baseItem, expired, pending], { now: '2026-05-28T00:00:00Z' });

  assert.deepEqual(
    blocked.map((item) => item.id),
    ['byd-song-plus'],
  );
  assert.equal(getAiQuoteSafety(expired, { now: '2026-05-28T00:00:00Z' }).canAiQuote, false);
  assert.equal(getAiQuoteSafety(pending, { now: '2026-05-28T00:00:00Z' }).blockingReasons.includes('价格未确认'), true);
});
