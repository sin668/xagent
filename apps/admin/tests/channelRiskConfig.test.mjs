import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  buildChannelRiskConfigPayload,
  buildChannelRiskConfigView,
  fetchChannelRiskRules,
  isExecutableRiskRule,
  updateChannelRiskRule,
} from '../src/services/channelRiskConfig.js';

test('channel risk config view exposes editable rules, policy source, operator, and blocked reason', () => {
  const view = buildChannelRiskConfigView({
    items: [
      {
        channel_name: 'official_website',
        channel_type: '官网',
        risk_level: 'Low',
        collection_allowed: true,
        ai_processing_allowed: true,
        allowed_actions: '人工查看公开页面',
        forbidden_actions: '高频访问',
        policy_source_url: 'https://example.com/terms',
        notes: '官网',
        updated_by: 'Compliance Anna',
        updated_at: '2026-05-28T10:00:00',
      },
      {
        channel_name: 'vkontakte',
        channel_type: '社交平台',
        risk_level: 'High',
        collection_allowed: false,
        ai_processing_allowed: false,
        allowed_actions: '政策研究',
        forbidden_actions: '自动私信；登录后批量采集',
        policy_source_url: 'https://example.com/vk',
        notes: '高风险',
        updated_by: 'Compliance Boris',
        updated_at: '2026-05-28T10:30:00',
      },
    ],
  });

  assert.equal(view.rules.length, 2);
  assert.equal(view.rules[0].riskLabel, '低风险');
  assert.equal(view.rules[0].policySourceUrl, 'https://example.com/terms');
  assert.equal(view.rules[0].updatedBy, 'Compliance Anna');
  assert.equal(view.rules[1].statusLabel, '自动任务阻断');
  assert.match(view.rules[1].blockReason, /High\/Forbidden/);
  assert.equal(isExecutableRiskRule(view.rules[0]), true);
  assert.equal(isExecutableRiskRule(view.rules[1]), false);
});

test('channel risk config payload keeps editable policy fields and operator audit', () => {
  const payload = buildChannelRiskConfigPayload({
    channelType: '公开目录',
    riskLevel: 'Forbidden',
    allowedActions: '无',
    forbiddenActions: '所有动作',
    policySourceUrl: 'https://example.com/policy',
    notes: '禁用渠道',
    collectionAllowed: true,
    updatedBy: 'Compliance Chen',
  });

  assert.deepEqual(payload, {
    channel_type: '公开目录',
    risk_level: 'Forbidden',
    allowed_actions: '无',
    forbidden_actions: '所有动作',
    policy_source_url: 'https://example.com/policy',
    notes: '禁用渠道',
    collection_allowed: true,
    updated_by: 'Compliance Chen',
  });
});

test('channel risk config service uses list and update backend contracts', async () => {
  const requested = [];
  await fetchChannelRiskRules({
    baseUrl: 'https://api.example.test',
    fetcher: async (url) => {
      requested.push({ method: 'GET', url });
      return { ok: true, json: async () => ({ items: [] }) };
    },
  });

  await updateChannelRiskRule({
    baseUrl: 'https://api.example.test',
    channelName: 'vkontakte',
    form: {
      channelType: '社交平台',
      riskLevel: 'High',
      allowedActions: '政策研究',
      forbiddenActions: '自动私信',
      updatedBy: 'Compliance Anna',
    },
    fetcher: async (url, options) => {
      requested.push({ method: options.method, url, body: JSON.parse(options.body) });
      return { ok: true, json: async () => ({ channel_name: 'vkontakte' }) };
    },
  });

  assert.equal(requested[0].url, 'https://api.example.test/channel-risks');
  assert.equal(requested[1].method, 'PUT');
  assert.equal(requested[1].url, 'https://api.example.test/channel-risks/vkontakte');
  assert.equal(requested[1].body.updated_by, 'Compliance Anna');
});
