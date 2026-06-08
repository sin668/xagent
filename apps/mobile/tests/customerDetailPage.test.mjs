import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const pagePath = new URL('../src/pages/customers/detail.vue', import.meta.url);
const stylePath = new URL('../src/styles/customerDetail.css', import.meta.url);
const srcPagesJsonPath = new URL('../src/pages.json', import.meta.url);
const rootPagesJsonPath = new URL('../pages.json', import.meta.url);

function readText(url) {
  return readFileSync(url, 'utf8');
}

test('客户详情页面注册到两份 uni-app 页面配置', () => {
  const srcPages = JSON.parse(readText(srcPagesJsonPath));
  const rootPages = JSON.parse(readText(rootPagesJsonPath));

  assert.ok(srcPages.pages.some((page) => page.path === 'pages/customers/detail'));
  assert.ok(rootPages.pages.some((page) => page.path === 'src/pages/customers/detail'));
});

test('客户详情页面通过 customersService 调真实客户详情 API 且不读取 staging 或 seed', () => {
  const page = readText(pagePath);

  assert.match(page, /customersService/);
  assert.match(page, /\.getCustomerDetail\(/);
  assert.match(page, /@dcloudio\/uni-app/);
  assert.match(page, /onUniLoad/);
  assert.doesNotMatch(page, /staging-leads|mapStagingLeadDetailToLeadDetail|Seed|seed|mock/i);
});

test('客户详情页面展示客户详情聚合分区和待补全信息', () => {
  const page = readText(pagePath);

  for (const token of [
    '客户画像',
    '联系方式',
    '来源证据',
    '意向车型',
    '触达历史',
    '跟进记录',
    '合规状态',
    '待补全',
    '勿扰客户',
    '人工记录',
    'customerDetail.css',
  ]) {
    assert.match(page, new RegExp(token));
  }
});

test('客户详情页面不包含自动发送、报价合同或自动触达动作', () => {
  const page = readText(pagePath);
  const css = readText(stylePath);

  assert.match(css, /\.customer-detail-page/);
  assert.doesNotMatch(page, /自动发送|自动触达|自动私信|自动加好友|批量触达|sendMessage|addFriend|autoSend|报价合同|合同生成/i);
});

test('线索详情晋级入口使用第三阶段 promote-to-customer 契约', () => {
  const leadDetailPage = readText(new URL('../src/pages/leads/detail.vue', import.meta.url));

  assert.match(leadDetailPage, /\/promote-to-customer/);
  assert.doesNotMatch(leadDetailPage, /\/promote`/);
});
