import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const pagePath = new URL('../src/pages/lead-cleanup/index.vue', import.meta.url);
const stylePath = new URL('../src/styles/leadCleanup.css', import.meta.url);
const srcPagesJsonPath = new URL('../src/pages.json', import.meta.url);
const rootPagesJsonPath = new URL('../pages.json', import.meta.url);

function readText(url) {
  return readFileSync(url, 'utf8');
}

test('清洗建议队列页面注册到两份 uni-app 页面配置', () => {
  const srcPages = JSON.parse(readText(srcPagesJsonPath));
  const rootPages = JSON.parse(readText(rootPagesJsonPath));

  assert.ok(srcPages.pages.some((page) => page.path === 'pages/lead-cleanup/index'));
  assert.ok(rootPages.pages.some((page) => page.path === 'src/pages/lead-cleanup/index'));
});

test('清洗建议队列页面通过 leadCleanupService 调真实 API', () => {
  const page = readText(pagePath);

  assert.match(page, /leadCleanupService/);
  assert.match(page, /\.listCleanupSuggestions\(/);
  assert.match(page, /\.approveSuggestion\(/);
  assert.match(page, /\.rejectSuggestion\(/);
  assert.match(page, /\.executeSuggestion\(/);
  assert.doesNotMatch(page, /Seed|seed|mock/i);
});

test('清洗建议队列页面展示类型、原因、证据、目标线索和权限提示', () => {
  const page = readText(pagePath);

  for (const token of [
    'suggestionTypeLabel',
    'reason',
    'evidenceNote',
    'targetLeadId',
    'targetLeadName',
    'permissionHint',
    'requiresElevatedPermission',
  ]) {
    assert.match(page, new RegExp(token));
  }
});

test('清洗建议队列页面支持 approve、reject、execute 入口但不提供自动删除', () => {
  const page = readText(pagePath);
  const css = readText(stylePath);

  assert.match(page, /approve/);
  assert.match(page, /reject/);
  assert.match(page, /execute/);
  assert.match(css, /\.lead-cleanup-page/);
  assert.doesNotMatch(page, /delete|remove|destroy|自动删除|直接删除|批量删除/i);
  assert.doesNotMatch(page, /自动私信|自动加好友|批量触达|sendMessage|addFriend/i);
});

test('清洗建议队列页面不根据建议类型在前端自动提权', () => {
  const page = readText(pagePath);

  assert.match(page, /currentActorRole/);
  assert.doesNotMatch(page, /actorRoleFor/);
  assert.doesNotMatch(page, /actorRole:\s*'admin'|actorRole:\s*'compliance'/);
});
