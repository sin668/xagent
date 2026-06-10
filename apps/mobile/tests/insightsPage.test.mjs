import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const pagePath = new URL('../src/pages/insights/index.vue', import.meta.url);
const srcPagesJsonPath = new URL('../src/pages.json', import.meta.url);
const rootPagesJsonPath = new URL('../pages.json', import.meta.url);

function readText(url) {
  return readFileSync(url, 'utf8');
}

test('洞察页面注册到两份 uni-app 页面配置并作为底部 Tab 入口', () => {
  const srcPages = JSON.parse(readText(srcPagesJsonPath));
  const rootPages = JSON.parse(readText(rootPagesJsonPath));
  const page = readText(pagePath);

  assert.ok(srcPages.pages.some((item) => item.path === 'pages/insights/index'));
  assert.ok(rootPages.pages.some((item) => item.path === 'src/pages/insights/index'));
  assert.match(page, /buildBottomTabs\('insights'\)/);
});

test('洞察页面提供来源、清洗建议和被清洗线索入口', () => {
  const page = readText(pagePath);

  assert.match(page, /线索来源/);
  assert.match(page, /清洗建议/);
  assert.match(page, /被清洗线索/);
  assert.match(page, /\/pages\/sources\/index/);
  assert.match(page, /\/pages\/lead-cleanup\/index/);
  assert.match(page, /\/pages\/leads\/cleaned/);
  assert.doesNotMatch(page, /自动私信|自动触达|自动发送/);
});
