import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  buildAdminApiErrorState,
  buildPhase5AdminIntegrationView,
  fetchPhase5AdminIntegration,
} from '../src/services/adminRealApiIntegration.js';

test('phase5 admin integration view proves prompt, knowledge, and email review use real APIs', () => {
  const view = buildPhase5AdminIntegrationView({
    prompt: { ok: true, status: 200, itemCount: 7, url: '/llm-prompt-templates' },
    knowledge: { ok: true, status: 200, itemCount: 12, url: '/knowledge/items?limit=100' },
    emailReview: { ok: true, status: 200, itemCount: 5, url: '/email-replies?limit=100' },
    emailReplyQuality: { ok: true, status: 200, url: '/dashboard/email-reply-quality' },
    phase5GoNoGo: { ok: true, status: 200, url: '/dashboard/phase5-go-no-go-report' },
    phase5E2E: { ok: true, status: 200, url: '/dashboard/phase5-e2e-integration-report' },
    actorRole: 'operator',
  });

  assert.equal(view.seedFallbackAllowed, false);
  assert.equal(view.realApiReady, true);
  assert.equal(view.integrationRecords.length, 6);
  assert.deepEqual(view.integrationRecords.map((item) => item.name), [
    'Prompt 治理',
    '知识库治理',
    '邮件审核台',
    '邮件回复质量',
    '第五阶段 Go/No-Go',
    '第五阶段端到端联调',
  ]);
  assert.deepEqual(view.integrationRecords.map((item) => item.statusLabel), [
    '真实 API 已联通',
    '真实 API 已联通',
    '真实 API 已联通',
    '真实 API 已联通',
    '真实 API 已联通',
    '真实 API 已联通',
  ]);
  assert.equal(view.permission.roleLabel, 'operator');
  assert.equal(view.permission.notice.includes('真实 API'), true);
});

test('admin api error state gives clear Chinese UI copy for 401 403 422 and 500', () => {
  assert.deepEqual(buildAdminApiErrorState({ status: 401, domainLabel: 'Prompt 治理' }), {
    status: 401,
    statusClass: 'red',
    title: 'Prompt 治理鉴权失败',
    message: '当前会话未通过后台鉴权，请检查登录态或 API Token 后重试。',
  });
  assert.equal(buildAdminApiErrorState({ status: 403, domainLabel: '知识库治理' }).message, '当前角色没有执行该后台操作的权限，请切换具备权限的角色或联系管理员授权。');
  assert.equal(buildAdminApiErrorState({ status: 422, domainLabel: '邮件审核台' }).message, '请求参数未通过后端校验，请检查筛选条件、分页参数和提交字段。');
  assert.equal(buildAdminApiErrorState({ status: 500, domainLabel: '质量指标' }).message, '后端服务处理异常，请查看 apps/api 日志、PostgreSQL 和 Redis 状态后重试。');
});

test('fetch phase5 admin integration checks real backend contracts without seed fallback', async () => {
  const requestedUrls = [];
  const payload = await fetchPhase5AdminIntegration({
    baseUrl: 'https://api.example.test/',
    actorRole: 'tech_admin',
    fetcher: async (url) => {
      requestedUrls.push(url);
      if (url.endsWith('/llm-prompt-templates')) return { ok: true, status: 200, json: async () => ({ items: [{ id: 'p1' }] }) };
      if (url.endsWith('/knowledge/items?limit=100')) return { ok: true, status: 200, json: async () => ({ items: [{ id: 'k1' }, { id: 'k2' }] }) };
      if (url.endsWith('/email-replies?limit=100')) return { ok: true, status: 200, json: async () => ({ items: [] }) };
      if (url.endsWith('/dashboard/email-reply-quality')) return { ok: true, status: 200, json: async () => ({ draft_count: 2 }) };
      if (url.endsWith('/dashboard/phase5-go-no-go-report')) return { ok: true, status: 200, json: async () => ({ conclusion: 'go' }) };
      if (url.endsWith('/dashboard/phase5-e2e-integration-report')) return { ok: true, status: 200, json: async () => ({ overall_status: 'passed' }) };
      throw new Error(`Unexpected URL: ${url}`);
    },
  });

  assert.deepEqual(requestedUrls, [
    'https://api.example.test/llm-prompt-templates',
    'https://api.example.test/knowledge/items?limit=100',
    'https://api.example.test/email-replies?limit=100',
    'https://api.example.test/dashboard/email-reply-quality',
    'https://api.example.test/dashboard/phase5-go-no-go-report',
    'https://api.example.test/dashboard/phase5-e2e-integration-report',
  ]);
  assert.equal(payload.actorRole, 'tech_admin');
  assert.equal(payload.prompt.itemCount, 1);
  assert.equal(payload.knowledge.itemCount, 2);
  assert.equal(payload.emailReview.itemCount, 0);
  assert.equal(payload.emailReplyQuality.status, 200);
  assert.equal(payload.phase5GoNoGo.status, 200);
  assert.equal(payload.phase5E2E.status, 200);
  assert.equal(payload.seedFallbackAllowed, false);
});
