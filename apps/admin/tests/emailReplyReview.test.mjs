import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  buildEmailReplyReviewView,
  buildEmailReplyDraftsQuery,
  fetchEmailReplyReview,
  updateEmailReplyFinalBody,
  requestEmailSendCheck,
  triggerEmailReplyReviewAction,
} from '../src/services/emailReplyReview.js';

const draftsPayload = {
  items: [
    {
      id: 'draft-manual',
      customer_name: 'Sibir Motors',
      customer_id: 'customer-1',
      message_id: 'message-1',
      thread_subject: 'Цена и доставка',
      inbound_subject: 'Цена и доставка',
      inbound_body: 'Please share price, payment and delivery terms.',
      detected_language: 'ru',
      reply_language: 'ru',
      ai_suggested_subject: 'Обсуждение поставок',
      ai_suggested_body: 'Здравствуйте! Спасибо за ваш запрос.',
      final_subject: 'Обсуждение поставок',
      final_body: 'Здравствуйте! Требуется проверка цены и условий.',
      knowledge_hits_json: [
        { title: '付款条款拦截', version: 'v1', similarity_score: 0.94 },
        { title: '合作流程介绍', version: 'v1', similarity_score: 0.88 },
      ],
      auto_send_allowed: false,
      auto_send_decision_json: { route: 'hold_for_manual_review', hard_block_reasons: ['price_payment_delivery'] },
      manual_review_required: true,
      manual_review_reason: '价格/付款/交付需要人工确认',
      status: 'manual_review',
      recent_outreach_history: [{ channel: 'email', subject: 'Intro', status: 'sent' }],
      vehicle_intent_summary: 'Hybrid SUV / budget unknown',
      created_at: '2026-06-05T09:00:00Z',
      updated_at: '2026-06-05T09:10:00Z',
    },
    {
      id: 'draft-auto',
      customer_name: 'AutoCity Vladivostok',
      customer_id: 'customer-2',
      message_id: 'message-2',
      thread_subject: 'Cooperation',
      inbound_subject: 'Cooperation',
      inbound_body: 'Could you explain cooperation process?',
      detected_language: 'en',
      reply_language: 'en',
      ai_suggested_subject: 'Cooperation process',
      ai_suggested_body: 'Thanks for your message.',
      final_subject: null,
      final_body: null,
      knowledge_hits_json: [{ title: '合作流程介绍', version: 'v1', similarity_score: 0.96 }],
      auto_send_allowed: true,
      auto_send_decision_json: { route: 'auto_send', hard_block_reasons: [] },
      manual_review_required: false,
      manual_review_reason: null,
      status: 'drafted',
      recent_outreach_history: [],
      vehicle_intent_summary: 'Unknown',
      created_at: '2026-06-05T09:30:00Z',
      updated_at: '2026-06-05T09:32:00Z',
    },
    {
      id: 'draft-blocked',
      customer_name: 'Baltic Auto',
      customer_id: 'customer-3',
      message_id: 'message-3',
      thread_subject: 'Stop contacting',
      inbound_subject: 'Stop contacting',
      inbound_body: 'Stop contacting us.',
      detected_language: 'en',
      reply_language: 'en',
      ai_suggested_subject: 'Acknowledgement',
      ai_suggested_body: 'We will stop contacting you.',
      knowledge_hits_json: [],
      auto_send_allowed: false,
      auto_send_decision_json: { route: 'block', hard_block_reasons: ['dnc_request'] },
      manual_review_required: true,
      manual_review_reason: 'DNC request',
      status: 'blocked',
      created_at: '2026-06-05T10:00:00Z',
      updated_at: '2026-06-05T10:02:00Z',
    },
  ],
};

test('email reply review view exposes queues, customer context, ai draft, knowledge hits, and hard blocks', () => {
  const view = buildEmailReplyReviewView({ drafts: draftsPayload, actorRole: 'operator' });

  assert.equal(view.summary.pendingReplyCount, 3);
  assert.equal(view.summary.autoSendCandidateCount, 1);
  assert.equal(view.summary.manualReviewCount, 2);
  assert.equal(view.summary.hardBlockedCount, 1);
  assert.equal(view.queue[0].customerName, 'Sibir Motors');
  assert.equal(view.queue[0].decisionLabel, '人工确认');
  assert.equal(view.queue[0].decisionClass, 'amber');
  assert.equal(view.selectedDraft.customerContext.customerName, 'Sibir Motors');
  assert.equal(view.selectedDraft.inbound.subject, 'Цена и доставка');
  assert.equal(view.selectedDraft.aiSuggestion.promptVersionLabel, 'Unknown');
  assert.equal(view.selectedDraft.finalReply.body, 'Здравствуйте! Требуется проверка цены и условий.');
  assert.equal(view.selectedDraft.knowledgeHits.length, 2);
  assert.equal(view.selectedDraft.risk.hardBlockReasonsText, 'price_payment_delivery');
  assert.equal(view.canConfirmSend, true);
  assert.equal(view.actionEntrypoints.map((item) => item.label).join(','), '编辑最终正文,发送前检查,确认发送,标记已发送,拒绝,阻断,转合规');
});

test('email reply review view disables send actions for read only roles', () => {
  const view = buildEmailReplyReviewView({ drafts: draftsPayload, actorRole: 'viewer' });

  assert.equal(view.canEditFinalBody, false);
  assert.equal(view.canConfirmSend, false);
  assert.equal(view.canTransferCompliance, false);
  assert.equal(view.permissionNotice, '当前角色只能查看邮件回复审核台，编辑、发送、阻断和转合规入口已禁用。');
});

test('email reply drafts query supports review filters', () => {
  assert.equal(buildEmailReplyDraftsQuery(), '?limit=100');
  assert.equal(
    buildEmailReplyDraftsQuery({ status: 'manual_review', manualReviewRequired: true, autoSendAllowed: false, limit: 50 }),
    '?decision=manual_review&limit=50',
  );
});

test('fetch email reply review calls real review queue API', async () => {
  const requestedUrls = [];
  const result = await fetchEmailReplyReview({
    baseUrl: 'https://api.example.test/',
    actorRole: 'operator',
    filters: { status: 'manual_review' },
    fetcher: async (url) => {
      requestedUrls.push(url);
      if (url.includes('/email-replies')) {
        return { ok: true, json: async () => draftsPayload };
      }
      throw new Error(`Unexpected URL: ${url}`);
    },
  });

  assert.deepEqual(requestedUrls, ['https://api.example.test/email-replies?decision=manual_review&limit=100']);
  assert.equal(result.actorRole, 'operator');
  assert.equal(result.drafts.items.length, 3);
});

test('email reply review view supports backend /email-replies summary shape', () => {
  const view = buildEmailReplyReviewView({
    drafts: {
      items: [
        {
          id: 'reply-summary',
          customer_name: 'Summary Motors',
          subject: 'Vehicle inquiry',
          language: 'ru',
          auto_send_decision: 'blocked',
          hard_block_reasons: ['DNC'],
          knowledge_hits: [{ title: '合作流程', similarity_score: 0.91 }],
          preview: '客户询问合作流程。',
          reply_draft: { subject: 'Re: Vehicle inquiry', body: 'Спасибо', prompt_version: 'email-reply-v1' },
        },
      ],
    },
    actorRole: 'operator',
  });

  assert.equal(view.queue[0].decisionLabel, '硬拦截');
  assert.equal(view.queue[0].reason, 'DNC');
  assert.equal(view.selectedDraft.finalReply.subject, 'Re: Vehicle inquiry');
  assert.equal(view.selectedDraft.knowledgeHits[0].title, '合作流程');
});

test('email reply actions update final text and always request backend send check before send', async () => {
  const calls = [];
  const fetcher = async (url, options = {}) => {
    calls.push({ url, options });
    if (url.endsWith('/email-reply/drafts/draft-manual') && options.method === 'PATCH') {
      return { ok: true, json: async () => ({ id: 'draft-manual', final_body: 'updated' }) };
    }
    if (url.endsWith('/internal/email-reply/auto-send-check') && options.method === 'POST') {
      return { ok: true, json: async () => ({ allowed: false, route: 'hold_for_manual_review' }) };
    }
    if (url.endsWith('/email-reply/drafts/draft-manual/manual-send') && options.method === 'POST') {
      return { ok: true, json: async () => ({ id: 'draft-manual', status: 'sent' }) };
    }
    if (url.endsWith('/email-reply/drafts/draft-manual/transfer-compliance') && options.method === 'POST') {
      return { ok: true, json: async () => ({ id: 'draft-manual', status: 'compliance_review' }) };
    }
    throw new Error(`Unexpected URL: ${url}`);
  };

  await updateEmailReplyFinalBody({
    baseUrl: 'https://api.example.test/',
    draftId: 'draft-manual',
    finalSubject: 'Updated subject',
    finalBody: 'updated',
    actor: 'Ada',
    fetcher,
  });
  await requestEmailSendCheck({
    baseUrl: 'https://api.example.test/',
    draftId: 'draft-manual',
    actor: 'Ada',
    actorRole: 'operator',
    fetcher,
  });
  await triggerEmailReplyReviewAction({
    baseUrl: 'https://api.example.test/',
    draftId: 'draft-manual',
    action: 'manual-send',
    actor: 'Ada',
    actorRole: 'operator',
    reviewNote: '已人工确认',
    fetcher,
  });
  await triggerEmailReplyReviewAction({
    baseUrl: 'https://api.example.test/',
    draftId: 'draft-manual',
    action: 'transfer-compliance',
    actor: 'Ada',
    actorRole: 'operator',
    reviewNote: '涉及付款条款',
    fetcher,
  });

  assert.equal(calls.length, 4);
  assert.equal(JSON.parse(calls[0].options.body).final_body, 'updated');
  assert.equal(JSON.parse(calls[1].options.body).draft_id, 'draft-manual');
  assert.equal(JSON.parse(calls[2].options.body).send_check_required, true);
  assert.equal(JSON.parse(calls[3].options.body).review_note, '涉及付款条款');
});
