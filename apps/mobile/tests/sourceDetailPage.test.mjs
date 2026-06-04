import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const detailPagePath = new URL('../src/pages/sources/detail.vue', import.meta.url);
const listPagePath = new URL('../src/pages/sources/index.vue', import.meta.url);
const stylePath = new URL('../src/styles/sourceCandidates.css', import.meta.url);
const srcPagesJsonPath = new URL('../src/pages.json', import.meta.url);
const rootPagesJsonPath = new URL('../pages.json', import.meta.url);

function readText(url) {
  return readFileSync(url, 'utf8');
}

test('来源详情审核页面注册到两份 uni-app 页面配置', () => {
  const srcPages = JSON.parse(readText(srcPagesJsonPath));
  const rootPages = JSON.parse(readText(rootPagesJsonPath));

  assert.ok(srcPages.pages.some((page) => page.path === 'pages/sources/detail'));
  assert.ok(rootPages.pages.some((page) => page.path === 'src/pages/sources/detail'));
});

test('来源列表卡片跳转到来源详情页', () => {
  const page = readText(listPagePath);

  assert.match(page, /\/pages\/sources\/detail\?id=/);
});

test('来源详情页通过 sourceCandidates service 加载详情并提交审核动作', () => {
  const page = readText(detailPagePath);

  assert.match(page, /sourceCandidatesService/);
  assert.match(page, /\.getSourceCandidate\(/);
  assert.match(page, /\.reviewSourceCandidate\(/);
  assert.doesNotMatch(page, /Seed|seed|mock/i);
});

test('来源详情页展示详情、证据、LLM 摘要和审计字段', () => {
  const page = readText(detailPagePath);

  for (const token of [
    'sourceUrl',
    'normalizedDomain',
    'riskLevel',
    'reviewStatus',
    'approvedForExtraction',
    'evidenceNote',
    'llmOutputSummary',
    'createdByTaskRunId',
    'auditTaskRunId',
  ]) {
    assert.match(page, new RegExp(token));
  }
});

test('来源详情页支持五类审核动作并声明审核通过不代表触达', () => {
  const page = readText(detailPagePath);

  for (const action of [
    'approve_for_extraction',
    'reject',
    'mark_high_risk',
    'pause_channel',
    'add_review_note',
  ]) {
    assert.match(page, new RegExp(action));
  }
  assert.match(page, /审核通过只代表允许抽取，不代表允许触达/);
});

test('来源详情页 Forbidden 不展示通过按钮且样式可用', () => {
  const page = readText(detailPagePath);
  const css = readText(stylePath);

  assert.match(page, /canApproveForExtraction/);
  assert.match(page, /riskLevel !== 'Forbidden'/);
  assert.match(css, /\.source-detail-page/);
  assert.doesNotMatch(page, /自动私信|自动加好友|批量触达|sendMessage|addFriend/i);
});
