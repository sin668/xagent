import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const leadIndexVue = readFileSync(new URL('../src/pages/leads/index.vue', import.meta.url), 'utf8');
const outreachIndexVue = readFileSync(new URL('../src/pages/outreach/index.vue', import.meta.url), 'utf8');
const appVue = readFileSync(new URL('../src/App.vue', import.meta.url), 'utf8');
const homeCss = readFileSync(new URL('../src/styles/home.css', import.meta.url), 'utf8');
const leadDetailCss = readFileSync(new URL('../src/styles/leadDetail.css', import.meta.url), 'utf8');
const leadPoolCss = readFileSync(new URL('../src/styles/leadPool.css', import.meta.url), 'utf8');
const inventoryCss = readFileSync(new URL('../src/styles/inventory.css', import.meta.url), 'utf8');
const sourceCandidatesCss = readFileSync(new URL('../src/styles/sourceCandidates.css', import.meta.url), 'utf8');

test('lead list defaults to all visible staging leads and requests enough rows from backend', () => {
  assert.match(leadIndexVue, /const activeFilter = ref\('all'\)/);
  assert.match(leadIndexVue, /\/staging-leads\?limit=100/);
  assert.doesNotMatch(leadIndexVue, /\/staging-leads\?has_contact=true/);
});

test('lead list page shows four top summary metrics and the requested filter tabs', () => {
  assert.match(leadIndexVue, /lead-summary-card/);
  assert.match(leadIndexVue, /v-for="stat in leadStats"/);
  assert.match(leadIndexVue, /有邮箱联系线索/);
  assert.match(leadIndexVue, /有社交媒体联系线索/);
  assert.match(leadIndexVue, /A\/B\/C级线索/);
  assert.match(leadIndexVue, /D\/E级线索/);
  assert.doesNotMatch(leadIndexVue, />有联系方式</);
  assert.doesNotMatch(leadIndexVue, /(^|[^A/])B\/C级线索|High 二次|缺联系方式|Watch\/Invalid|待复核/);
});

test('outreach action bar is above bottom tabbar instead of below it', () => {
  assert.doesNotMatch(outreachIndexVue, /tabbar-above-action/);
  assert.match(outreachIndexVue, /class="action-bar action-bar-above-tabbar"/);
  assert.match(leadDetailCss, /\.action-bar-above-tabbar\s*{[^}]*bottom:\s*calc\(82px \+ var\(--safe-bottom,\s*0px\)\)/s);
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
