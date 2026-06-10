import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const inventoryPage = readFileSync(new URL('../src/pages/inventory/index.vue', import.meta.url), 'utf8');
const leadPage = readFileSync(new URL('../src/pages/leads/index.vue', import.meta.url), 'utf8');
const homePage = readFileSync(new URL('../src/pages/home/index.vue', import.meta.url), 'utf8');

test('inventory page may use inventorySeed when backend inventory is unavailable', () => {
  assert.match(inventoryPage, /import \{ inventorySeed \} from '..\/..\/data\/inventorySeed\.js'/);
  assert.match(inventoryPage, /inventoryItems\.value = inventorySeed/);
});

test('inventory page is the insights tab destination', () => {
  assert.match(inventoryPage, /buildBottomTabs\('insights'\)/);
});

test('seed fallback remains limited to inventory page only', () => {
  assert.doesNotMatch(leadPage, /Seed|seed/i);
  assert.doesNotMatch(homePage, /Seed|seed/i);
});
