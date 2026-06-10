import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const pagePath = new URL('../src/pages/leads/cleaned.vue', import.meta.url);
const stylePath = new URL('../src/styles/cleanedLeads.css', import.meta.url);
const srcPagesJsonPath = new URL('../src/pages.json', import.meta.url);
const rootPagesJsonPath = new URL('../pages.json', import.meta.url);

function readText(url) {
  return readFileSync(url, 'utf8');
}

test('被清洗线索页面注册到两份 uni-app 页面配置', () => {
  const srcPages = JSON.parse(readText(srcPagesJsonPath));
  const rootPages = JSON.parse(readText(rootPagesJsonPath));

  assert.ok(srcPages.pages.some((page) => page.path === 'pages/leads/cleaned'));
  assert.ok(rootPages.pages.some((page) => page.path === 'src/pages/leads/cleaned'));
});

test('被清洗线索页面通过 leadCleanupService 读取已执行清洗结果', () => {
  const page = readText(pagePath);

  assert.match(page, /leadCleanupService/);
  assert.match(page, /\.listCleanupSuggestions\(/);
  assert.match(page, /reviewStatus:\s*'executed'/);
  assert.match(page, /confirm_invalid/);
  assert.match(page, /mark_abandoned/);
  assert.match(page, /strong_duplicate/);
  assert.match(page, /possible_duplicate/);
  assert.doesNotMatch(page, /\.approveSuggestion|\.rejectSuggestion|\.executeSuggestion/);
  assert.doesNotMatch(page, /Seed|seed|mock/i);
});

test('被清洗线索页面突出总数、关键线索信息和联系方式', () => {
  const page = readText(pagePath);
  const css = readText(stylePath);

  for (const token of [
    '被清洗线索',
    'totalCount',
    'cleanedStats',
    'stagingLeadId',
    'reason',
    'contacts',
    '联系方式',
    'recommendedAction',
    'cleanup-result-card',
  ]) {
    assert.match(page, new RegExp(token));
  }
  assert.doesNotMatch(page, /事实依据/);
  assert.match(page, /leadDisplayName/);
  assert.match(page, /openLeadDetail/);
  assert.match(page, /\/pages\/leads\/detail\?id=/);
  assert.match(css, /\.cleaned-leads-page/);
  assert.match(css, /\.cleanup-result-card/);
});

test('被清洗线索页面在清洗原因上方最多展示两条联系方式', () => {
  const page = readText(pagePath);
  const contactIndex = page.indexOf('class="cleaned-contact-block"');
  const reasonIndex = page.indexOf('class="cleaned-reason-block"');

  assert.ok(contactIndex > 0);
  assert.ok(reasonIndex > 0);
  assert.ok(contactIndex < reasonIndex);
  assert.match(page, /item\.contacts\.slice\(0,\s*2\)/);
});

test('被清洗线索页面支持统计点击筛选并提供返回和居中标题', () => {
  const page = readText(pagePath);
  const css = readText(stylePath);

  assert.match(page, /activeCleanedFilter/);
  assert.match(page, /filteredCleanedLeads/);
  assert.match(page, /selectCleanedStat/);
  assert.match(page, /cleaned-metric-active/);
  assert.match(page, /goBack/);
  assert.match(page, /cleaned-nav-centered/);
  assert.match(css, /\.cleaned-nav-centered/);
  assert.match(css, /\.cleaned-metric-active/);
});

test('被清洗线索页面提供人工调整等级入口', () => {
  const page = readText(pagePath);
  const css = readText(stylePath);

  assert.match(page, /stagingLeadActionsService/);
  assert.match(page, /GRADE_OPTIONS/);
  assert.match(page, /调整等级/);
  assert.match(page, /handleUpdateGrade/);
  assert.match(page, /A级/);
  assert.match(page, /B级/);
  assert.match(page, /C级/);
  assert.match(page, /D级/);
  assert.match(page, /E级/);
  assert.match(css, /\.cleaned-grade-actions/);
});
