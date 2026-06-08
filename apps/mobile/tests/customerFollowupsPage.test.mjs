import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const pagePath = new URL('../src/pages/customers/followups.vue', import.meta.url);
const stylePath = new URL('../src/styles/customerFollowups.css', import.meta.url);
const srcPagesJsonPath = new URL('../src/pages.json', import.meta.url);
const rootPagesJsonPath = new URL('../pages.json', import.meta.url);

function readText(url) {
  return readFileSync(url, 'utf8');
}

test('客户跟进记录页面注册到两份 uni-app 页面配置', () => {
  const srcPages = JSON.parse(readText(srcPagesJsonPath));
  const rootPages = JSON.parse(readText(rootPagesJsonPath));

  assert.ok(srcPages.pages.some((page) => page.path === 'pages/customers/followups'));
  assert.ok(rootPages.pages.some((page) => page.path === 'src/pages/customers/followups'));
});

test('客户跟进记录页面通过 customerFollowupsService 调真实 API', () => {
  const page = readText(pagePath);

  assert.match(page, /customerFollowupsService/);
  assert.match(page, /\.listFollowups\(/);
  assert.match(page, /\.createFollowup\(/);
  assert.match(page, /@dcloudio\/uni-app/);
  assert.doesNotMatch(page, /Seed|seed|mock|staging-leads/i);
});

test('客户跟进记录页面展示触达历史、跟进时间线、新增表单和勿扰硬阻断提示', () => {
  const page = readText(pagePath);

  for (const token of [
    '触达与跟进时间线',
    '新增跟进',
    '客户反馈',
    '下一次跟进时间',
    '标记勿扰',
    '勿扰客户不得再次进入触达队列',
    '不可自动发送',
    '保存跟进记录',
    'followup-action-bar-above-safe-area',
  ]) {
    assert.match(page, new RegExp(token));
  }
});

test('客户跟进记录页面按钮不被底部区域遮挡且不包含自动发送动作', () => {
  const page = readText(pagePath);
  const css = readText(stylePath);

  assert.match(css, /\.customer-followups-page/);
  assert.match(css, /\.followup-action-bar-above-safe-area/);
  assert.match(css, /width: min\(100vw, var\(--phone-width, 430px\)\)/);
  assert.doesNotMatch(page, /自动发送消息|自动私信|自动加好友|sendMessage|addFriend|autoSend|auto_send/i);
});
