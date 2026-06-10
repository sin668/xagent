import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const leadIndexVue = readFileSync(new URL('../src/pages/leads/index.vue', import.meta.url), 'utf8');
const homeIndexVue = readFileSync(new URL('../src/pages/home/index.vue', import.meta.url), 'utf8');
const outreachIndexVue = readFileSync(new URL('../src/pages/outreach/index.vue', import.meta.url), 'utf8');
const outreachSendVue = readFileSync(new URL('../src/pages/outreach/send.vue', import.meta.url), 'utf8');
const appVue = readFileSync(new URL('../src/App.vue', import.meta.url), 'utf8');
const homeCss = readFileSync(new URL('../src/styles/home.css', import.meta.url), 'utf8');
const leadDetailCss = readFileSync(new URL('../src/styles/leadDetail.css', import.meta.url), 'utf8');
const leadPoolCss = readFileSync(new URL('../src/styles/leadPool.css', import.meta.url), 'utf8');
const inventoryCss = readFileSync(new URL('../src/styles/inventory.css', import.meta.url), 'utf8');
const sourceCandidatesCss = readFileSync(new URL('../src/styles/sourceCandidates.css', import.meta.url), 'utf8');

test('lead list defaults to all visible staging leads and requests enough rows from backend', () => {
  assert.match(leadIndexVue, /const activeFilter = ref\('all'\)/);
  assert.match(leadIndexVue, /\/staging-leads\?limit=500/);
  assert.doesNotMatch(leadIndexVue, /\/customers\?limit=500/);
  assert.doesNotMatch(leadIndexVue, /mapCustomerListToLeadPool|mergeCustomerAndStagingLeadPools/);
  assert.doesNotMatch(leadIndexVue, /\/staging-leads\?has_contact=true/);
});

test('lead list page shows four clickable top summary metrics instead of middle filter tabs', () => {
  assert.match(leadIndexVue, /lead-summary-card/);
  assert.match(leadIndexVue, /v-for="stat in leadStats"/);
  assert.match(leadIndexVue, /@click="selectSummaryFilter\(stat\)"/);
  assert.match(leadIndexVue, /lead-summary-tile-active/);
  assert.match(leadIndexVue, /有邮箱联系线索/);
  assert.match(leadIndexVue, /有社交媒体联系线索/);
  assert.match(leadIndexVue, /A\/B\/C级线索/);
  assert.match(leadIndexVue, /D\/E级线索/);
  assert.doesNotMatch(leadIndexVue, /v-for="tab in tabs"/);
  assert.doesNotMatch(leadIndexVue, /class="chip-row"/);
  assert.doesNotMatch(leadIndexVue, />有联系方式</);
  assert.doesNotMatch(leadIndexVue, /(^|[^A/])B\/C级线索|High 二次|缺联系方式|Watch\/Invalid|待复核/);
});

test('lead list cards use sectioned mobile layout with conditional actions and clamped text', () => {
  for (const token of [
    'lead-info-section',
    'lead-section-title',
    '联系方式',
    'AI建议',
    'lead-card-actions',
    'card.actions',
    'openLeadAction',
    'submitManualEnrichment',
    'markLeadDoNotContactInline',
    'promoteLeadInline',
    '人工补录',
    'action.label',
  ]) {
    assert.match(leadIndexVue, new RegExp(token));
  }

  assert.doesNotMatch(leadIndexVue, /证据与来源/);
  assert.doesNotMatch(leadIndexVue, /card\.evidence|card\.sourceUrl|lead-source-link/);
  assert.match(leadIndexVue, /clipText\(card\.aiAdvice/);
  assert.match(leadPoolCss, /-webkit-line-clamp:\s*3/);
  assert.match(leadPoolCss, /-webkit-line-clamp:\s*2/);
  assert.match(leadPoolCss, /white-space:\s*nowrap/);
  assert.match(leadPoolCss, /\.pool-card-top\s*[\s\S]*?white-space:\s*nowrap/);
});

test('lead list page replaces search input with source and cleaned lead action buttons', () => {
  assert.match(leadIndexVue, /线索来源/);
  assert.match(leadIndexVue, /被清洗线索/);
  assert.match(leadIndexVue, /openLeadSources/);
  assert.match(leadIndexVue, /openCleanedLeads/);
  assert.match(leadIndexVue, /\/pages\/sources\/index/);
  assert.match(leadIndexVue, /\/pages\/leads\/cleaned/);
  assert.doesNotMatch(leadIndexVue, /搜索车商、城市、Telegram、邮箱/);
});

test('home lead cards use staging lead pool and cleaned leads page counting sources', () => {
  assert.match(homeIndexVue, /mapStagingLeadListToLeadPool/);
  assert.doesNotMatch(homeIndexVue, /mapCustomerListToLeadPool|mergeCustomerAndStagingLeadPools/);
  assert.match(homeIndexVue, /buildLeadPoolStats/);
  assert.match(homeIndexVue, /abcLeadsTotal/);
  assert.match(homeIndexVue, /cleanedLeadsTotal/);
  assert.match(homeIndexVue, /reviewStatus:\s*'executed'/);
  assert.match(homeIndexVue, /limit:\s*100/);
  assert.doesNotMatch(homeIndexVue, /listCleanupSuggestions\(\{[\s\S]*?limit:\s*1\s*[,}]/);
});

test('outreach assistant removes bottom tabbar and uses followup-style safe-area action bar', () => {
  assert.doesNotMatch(outreachIndexVue, /<view class="tabbar"|bottomTabs|openTab|navigateBottomTab/);
  assert.doesNotMatch(outreachIndexVue, /action-bar-above-tabbar/);
  assert.match(outreachIndexVue, /class="followup-action-bar followup-action-bar-above-safe-area"/);
  assert.match(outreachIndexVue, /openEmailSend/);
  assert.match(outreachIndexVue, /\/pages\/outreach\/send\?/);
  assert.match(outreachIndexVue, /\/staging-leads\/\$\{encodeURIComponent\(id\)\}/);
  assert.match(outreachIndexVue, /stagingLead\.contacts_json/);
});

test('outreach email send page is registered and sends editable email draft', () => {
  const srcPages = JSON.parse(readFileSync(new URL('../src/pages.json', import.meta.url), 'utf8'));
  const rootPages = JSON.parse(readFileSync(new URL('../pages.json', import.meta.url), 'utf8'));

  assert.ok(srcPages.pages.some((page) => page.path === 'pages/outreach/send'));
  assert.ok(rootPages.pages.some((page) => page.path === 'src/pages/outreach/send'));
  for (const token of ['邮件发送', '收件人', '主题', '正文', '发送', '取消', 'sendEmail', 'createOutreachEmailService']) {
    assert.match(outreachSendVue, new RegExp(token));
  }
  assert.match(outreachSendVue, /v-model="form\.toEmail"/);
  assert.match(outreachSendVue, /v-model="form\.subject"/);
  assert.match(outreachSendVue, /v-model="form\.body"/);
  assert.match(outreachSendVue, /\/staging-leads\/\$\{encodeURIComponent\(id\)\}/);
  assert.match(outreachSendVue, /stagingLead\.contacts_json/);
});

test('mobile app shell constrains H5 preview to phone width and prevents horizontal overflow', () => {
  assert.match(appVue, /--phone-width:\s*430px/);
  assert.match(appVue, /max-width:\s*var\(--phone-width\)/);
  assert.match(appVue, /border-radius:\s*var\(--phone-radius\)/);
  assert.match(appVue, /overflow-x:\s*hidden/);
  assert.match(appVue, /box-sizing:\s*border-box/);
});

test('fixed bottom bars are constrained to the phone shell instead of viewport width', () => {
  assert.match(homeCss, /\.tabbar\s*{[^}]*width:\s*min\(100vw,\s*var\(--phone-width,\s*430px\)\)/s);
  assert.match(homeCss, /\.tabbar\s*{[^}]*left:\s*50%/s);
  assert.match(homeCss, /\.tabbar\s*{[^}]*transform:\s*translateX\(-50%\)/s);
  assert.match(leadDetailCss, /\.action-bar\s*{[^}]*width:\s*min\(100vw,\s*var\(--phone-width,\s*430px\)\)/s);
});

test('mobile scroll containers isolate horizontal chip scrolling without page overflow', () => {
  for (const css of [leadPoolCss, inventoryCss, sourceCandidatesCss]) {
    assert.match(css, /overflow-x:\s*hidden/);
  }
  assert.doesNotMatch(leadPoolCss, /margin:\s*14px\s+-16px/);
  assert.doesNotMatch(sourceCandidatesCss, /margin:\s*14px\s+-16px/);
});
