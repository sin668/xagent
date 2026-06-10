import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const pagePath = new URL('../src/pages/sources/index.vue', import.meta.url);
const stylePath = new URL('../src/styles/sourceCandidates.css', import.meta.url);
const srcPagesJsonPath = new URL('../src/pages.json', import.meta.url);
const rootPagesJsonPath = new URL('../pages.json', import.meta.url);

function readText(url) {
  return readFileSync(url, 'utf8');
}

test('来源候选队列页面注册到 uni-app 页面配置', () => {
  const srcPages = JSON.parse(readText(srcPagesJsonPath));
  const rootPages = JSON.parse(readText(rootPagesJsonPath));

  assert.ok(srcPages.pages.some((page) => page.path === 'pages/sources/index'));
  assert.ok(rootPages.pages.some((page) => page.path === 'src/pages/sources/index'));
});

test('来源候选队列页面通过 sourceCandidates service 调真实 API', () => {
  const page = readText(pagePath);

  assert.match(page, /sourceCandidatesService/);
  assert.match(page, /\.listSourceCandidates\(/);
  assert.doesNotMatch(page, /Seed|seed|mock/i);
});

test('来源候选队列页面支持统计驱动的风险与准入筛选', () => {
  const page = readText(pagePath);

  for (const token of ['riskLevel', 'approvedForExtraction', 'isDuplicate', 'activeSourceStat']) {
    assert.match(page, new RegExp(token));
  }
  for (const label of ['待审 High', '可抽取来源', '重复候选', '阻断来源']) {
    assert.match(page, new RegExp(label));
  }
});

test('来源候选队列页面通过顶部统计筛选并移除中间 Tab 过滤区', () => {
  const page = readText(pagePath);
  const css = readText(stylePath);

  assert.match(page, /sourceStats/);
  assert.match(page, /selectSourceStat/);
  assert.match(page, /source-summary-tile-active/);
  assert.match(page, /goBack/);
  assert.match(page, /source-nav-centered/);
  assert.doesNotMatch(page, /source-chip-row/);
  assert.doesNotMatch(page, /risk-strip/);
  assert.doesNotMatch(page, /filter-grid/);
  assert.match(css, /\.source-nav-centered/);
  assert.match(css, /\.source-summary-tile-active/);
});

test('来源候选队列页面展示 URL/domain、风险、证据和是否可抽取', () => {
  const page = readText(pagePath);

  for (const token of [
    'sourceUrl',
    'normalizedDomain',
    'riskLevel',
    'evidenceNote',
    'approvedForExtraction',
  ]) {
    assert.match(page, new RegExp(token));
  }
});

test('来源候选队列页面样式独立且不包含自动触达动作', () => {
  const page = readText(pagePath);
  const css = readText(stylePath);

  assert.match(page, /sourceCandidates\.css/);
  assert.match(css, /\.source-candidates-page/);
  assert.doesNotMatch(page, /自动私信|自动加好友|批量触达|sendMessage|addFriend/i);
});
