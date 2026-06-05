import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

import {
  buildEmailReplyActionPayload,
  createEmailRepliesService,
  filterEmailReplies,
  mapEmailReplyDetail,
  mapEmailReplyItem,
  summarizeEmailReplies,
} from '../src/services/emailReplies.js';

const listPagePath = new URL('../src/pages/email-replies/index.vue', import.meta.url);
const detailPagePath = new URL('../src/pages/email-replies/detail.vue', import.meta.url);
const stylePath = new URL('../src/styles/emailReplies.css', import.meta.url);
const srcPagesJsonPath = new URL('../src/pages.json', import.meta.url);
const rootPagesJsonPath = new URL('../pages.json', import.meta.url);

function readText(url) {
  return readFileSync(url, 'utf8');
}

test('邮件回复页面注册到两份 uni-app 页面配置', () => {
  const srcPages = JSON.parse(readText(srcPagesJsonPath));
  const rootPages = JSON.parse(readText(rootPagesJsonPath));

  assert.ok(srcPages.pages.some((page) => page.path === 'pages/email-replies/index'));
  assert.ok(srcPages.pages.some((page) => page.path === 'pages/email-replies/detail'));
  assert.ok(rootPages.pages.some((page) => page.path === 'src/pages/email-replies/index'));
  assert.ok(rootPages.pages.some((page) => page.path === 'src/pages/email-replies/detail'));
});

test('邮件回复列表和详情页调用真实 API 服务且不使用 seed/mock', () => {
  const listPage = readText(listPagePath);
  const detailPage = readText(detailPagePath);
  const css = readText(stylePath);

  assert.match(listPage, /emailRepliesService/);
  assert.match(listPage, /\.listEmailReplies\(/);
  assert.match(listPage, /\/pages\/email-replies\/detail\?id=/);
  assert.match(detailPage, /\.getEmailReply\(/);
  assert.match(detailPage, /\.confirmManualSend\(/);
  assert.match(detailPage, /\.rejectReply\(/);
  assert.match(css, /\.email-replies-page/);
  assert.doesNotMatch(`${listPage}\n${detailPage}`, /Seed|seed|mock/i);
});

test('邮件回复 mapper 展示自动发送、人工确认和硬拦截状态', () => {
  const auto = mapEmailReplyItem({
    id: 'reply-1',
    customer_name: 'AutoCity',
    customer_grade: 'B',
    subject: 'Re: cooperation',
    auto_send_decision: 'auto_send_allowed',
    knowledge_hits: [{ title: 'FAQ-EN-012', similarity_score: 0.91 }],
  });
  const blocked = mapEmailReplyItem({
    id: 'reply-2',
    auto_send_decision: 'blocked',
    hard_block_reasons: ['DNC', '价格承诺'],
  });

  assert.equal(auto.decisionLabel, '可自动发');
  assert.equal(auto.canAutoSend, true);
  assert.equal(auto.knowledgeSummary, 'FAQ-EN-012');
  assert.equal(auto.similarityText, '91%');
  assert.equal(blocked.decisionLabel, '硬拦截');
  assert.equal(blocked.canAutoSend, false);
  assert.deepEqual(blocked.hardBlocks, ['DNC', '价格承诺']);
});

test('邮件回复详情保留 AI 建议、知识证据、模型审计和自动发送判断', () => {
  const detail = mapEmailReplyDetail({
    id: 'reply-1',
    customer_name: 'Sibir Motors',
    subject: 'Вопрос по цене и доставке',
    inbound_body: 'Просим прислать точную цену и срок доставки.',
    reply_draft: {
      subject: 'Обсуждение поставок',
      body: 'Точная цена требует проверки нашей командой.',
      prompt_version: 'email-reply-v1',
    },
    ai_audit: { model_name: 'gpt-4.1' },
    auto_send_check: {
      decision: 'manual_review',
      allow_auto_send: false,
      reasons: ['价格/付款/交付周期需人工确认'],
    },
    knowledge_hits: [{ knowledge_key: 'COMPLIANCE-RU-009', similarity_score: 0.94, auto_reply_allowed: false }],
  });

  assert.equal(detail.customerName, 'Sibir Motors');
  assert.equal(detail.replySubject, 'Обсуждение поставок');
  assert.equal(detail.modelName, 'gpt-4.1');
  assert.equal(detail.autoSendCheck.allowAutoSend, false);
  assert.deepEqual(detail.autoSendCheck.reasons, ['价格/付款/交付周期需人工确认']);
  assert.equal(detail.knowledgeHits[0].title, 'COMPLIANCE-RU-009');
  assert.equal(detail.knowledgeHits[0].similarityText, '94%');
});

test('邮件回复服务调用后端列表、详情、确认发送和驳回接口', async () => {
  const calls = [];
  const service = createEmailRepliesService({
    client: {
      get(endpoint) {
        calls.push(['GET', endpoint]);
        if (endpoint.startsWith('/email-replies/reply-1')) {
          return Promise.resolve({ id: 'reply-1', subject: 'detail' });
        }
        return Promise.resolve({ items: [{ id: 'reply-1', subject: 'list' }], total: 1 });
      },
      post(endpoint, body) {
        calls.push(['POST', endpoint, body]);
        return Promise.resolve({ id: 'reply-1', subject: 'updated' });
      },
    },
  });

  const list = await service.listEmailReplies({ limit: 50, decision: 'manual_review' });
  const detail = await service.getEmailReply('reply-1');
  await service.confirmManualSend('reply-1', { actor: 'ops-anna', note: '人工确认' });
  await service.rejectReply('reply-1', { actor: 'ops-anna', note: '风险过高' });

  assert.equal(list.total, 1);
  assert.equal(detail.id, 'reply-1');
  assert.deepEqual(calls, [
    ['GET', '/email-replies?limit=50&decision=manual_review'],
    ['GET', '/email-replies/reply-1'],
    [
      'POST',
      '/email-replies/reply-1/confirm-send',
      { actor: 'ops-anna', review_note: '人工确认', manual_confirmed: true },
    ],
    [
      'POST',
      '/email-replies/reply-1/reject',
      { actor: 'ops-anna', review_note: '风险过高', manual_confirmed: true },
    ],
  ]);
});

test('邮件回复筛选和汇总符合第五阶段队列口径', () => {
  const items = [
    mapEmailReplyItem({ id: 'a', auto_send_decision: 'auto_send_allowed' }),
    mapEmailReplyItem({ id: 'b', auto_send_decision: 'manual_review' }),
    mapEmailReplyItem({ id: 'c', auto_send_decision: 'blocked' }),
  ];

  assert.deepEqual(summarizeEmailReplies(items), { total: 3, autoSend: 1, manual: 1, blocked: 1 });
  assert.deepEqual(filterEmailReplies(items, 'auto').map((item) => item.id), ['a']);
  assert.deepEqual(filterEmailReplies(items, 'manual').map((item) => item.id), ['b']);
  assert.deepEqual(filterEmailReplies(items, 'blocked').map((item) => item.id), ['c']);
  assert.deepEqual(buildEmailReplyActionPayload({ actor: 'ops-anna', note: '已确认' }), {
    actor: 'ops-anna',
    review_note: '已确认',
    manual_confirmed: true,
  });
});
