import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const pagePath = new URL('../src/pages/customers/index.vue', import.meta.url);
const stylePath = new URL('../src/styles/customers.css', import.meta.url);
const srcPagesJsonPath = new URL('../src/pages.json', import.meta.url);
const rootPagesJsonPath = new URL('../pages.json', import.meta.url);

function readText(url) {
  return readFileSync(url, 'utf8');
}

test('客户工作台页面注册到两份 uni-app 页面配置', () => {
  const srcPages = JSON.parse(readText(srcPagesJsonPath));
  const rootPages = JSON.parse(readText(rootPagesJsonPath));

  assert.ok(srcPages.pages.some((page) => page.path === 'pages/customers/index'));
  assert.ok(rootPages.pages.some((page) => page.path === 'src/pages/customers/index'));
});

test('客户工作台页面通过 customersService 调真实 customers API 且不读取 staging', () => {
  const page = readText(pagePath);

  assert.match(page, /customersService/);
  assert.match(page, /\.listCustomers\(/);
  assert.doesNotMatch(page, /staging-leads|mapStagingLeadListToLeadPool|mergeCustomerAndStagingLeadPools|Seed|seed|mock/i);
});

test('客户工作台页面展示客户核心字段和四个业务筛选', () => {
  const page = readText(pagePath);

  for (const token of [
    'name',
    'countryCityText',
    'gradeLabel',
    'contactSummaryText',
    'vehicleIntentText',
    'nextAction',
    'today',
    'c_compliance',
    'has_intent',
    'unassigned',
  ]) {
    assert.match(page, new RegExp(token));
  }
});

test('客户工作台页面样式独立且不包含自动触达动作', () => {
  const page = readText(pagePath);
  const css = readText(stylePath);

  assert.match(page, /customers\.css/);
  assert.match(css, /\.customers-page/);
  assert.doesNotMatch(page, /自动私信|自动加好友|批量触达|sendMessage|addFriend|autoSend/i);
});
