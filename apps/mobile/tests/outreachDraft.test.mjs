import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  buildOutreachEmailPayload,
  buildOutreachDraftViewModel,
  canRecordManualSend,
  createManualSendRecord,
  createOutreachEmailService,
  firstEmailContact,
  hasForbiddenCommitments,
} from '../src/services/outreachDraft.js';

const safeLead = {
  id: 'ru-auto-city',
  customerName: 'AutoCity Moscow',
  grade: 'B',
  riskLevel: 'Low',
  doNotContact: false,
  channel: 'Email',
};

const safeDraft = {
  id: 'draft-1',
  templateId: 'TMP-RU-B-001',
  templateStatus: '可外发',
  version: 'v1',
  generatedAt: '2026-05-28T12:00:00Z',
  subject: 'Поставка подержанных автомобилей из Китая',
  body:
    'Здравствуйте! Мы изучаем возможности сотрудничества с автодилерами по поставкам автомобилей с пробегом, почти новых и складских автомобилей. Если вам интересно, пожалуйста, сообщите, какие модели и форматы сотрудничества для вас актуальны.',
  refusalPath:
    'Если вам не интересно получать такие сообщения, пожалуйста, сообщите нам, и мы больше не будем вас беспокоить.',
  riskTips: ['人工发送', '不得承诺最终价格、物流、清关、付款或交付周期'],
  audit: {
    model: 'Unknown',
    promptVersion: 'outreach-template-v1',
    inputSaved: true,
    outputSaved: true,
  },
};

test('outreach draft view model exposes Russian draft, risk tips, version, generated time, and audit', () => {
  const view = buildOutreachDraftViewModel({ lead: safeLead, draft: safeDraft });

  assert.equal(view.customerName, 'AutoCity Moscow');
  assert.equal(view.subject, safeDraft.subject);
  assert.equal(view.body.includes('Здравствуйте'), true);
  assert.equal(view.refusalPath.includes('больше не будем'), true);
  assert.equal(view.versionLabel, 'TMP-RU-B-001 · v1');
  assert.equal(view.generatedAt, '2026-05-28T12:00:00Z');
  assert.equal(view.audit.inputSaved, true);
  assert.equal(view.audit.outputSaved, true);
  assert.equal(view.complianceChecks.every((check) => check.passed), true);
});

test('do-not-contact lead cannot generate or record outreach draft', () => {
  const view = buildOutreachDraftViewModel({
    lead: { ...safeLead, doNotContact: true },
    draft: safeDraft,
  });

  assert.equal(view.canGenerateDraft, false);
  assert.equal(view.canRecordSent, false);
  assert.equal(view.blockReasons.includes('客户已标记勿扰'), true);
});

test('High and Forbidden channel risks block draft generation and outreach action', () => {
  for (const riskLevel of ['High', 'Forbidden']) {
    const view = buildOutreachDraftViewModel({
      lead: { ...safeLead, riskLevel },
      draft: safeDraft,
    });

    assert.equal(view.canGenerateDraft, false);
    assert.equal(view.canRecordSent, false);
    assert.equal(view.blockReasons.includes('渠道风险不允许触达动作'), true);
  }
});

test('draft with forbidden commitments fails compliance checks', () => {
  const riskyDraft = {
    ...safeDraft,
    body: `${safeDraft.body} Мы гарантируем финальную цену, быструю доставку, таможенное оформление и безопасную оплату.`,
  };
  const view = buildOutreachDraftViewModel({ lead: safeLead, draft: riskyDraft });

  assert.equal(hasForbiddenCommitments(riskyDraft), true);
  assert.equal(view.canRecordSent, false);
  assert.equal(view.complianceChecks.find((check) => check.key === 'no_forbidden_commitments').passed, false);
});

test('manual send can only be recorded after human confirmation', () => {
  const view = buildOutreachDraftViewModel({ lead: safeLead, draft: safeDraft });

  assert.equal(canRecordManualSend(view, { humanConfirmed: false }), false);
  assert.equal(canRecordManualSend(view, { humanConfirmed: true }), true);

  const record = createManualSendRecord(view, {
    humanConfirmed: true,
    sender: 'Anna',
    sentAt: '2026-05-28T12:30:00Z',
    channel: 'Email',
  });

  assert.equal(record.status, 'sent_manual');
  assert.equal(record.autoSend, false);
  assert.equal(record.sender, 'Anna');
});

test('outreach email payload uses customer email, editable subject/body, and real send endpoint', async () => {
  assert.equal(
    firstEmailContact([
      { type: 'telegram', value: '@dealer' },
      { type: 'Email', value: 'buyer@example.ru' },
    ]).value,
    'buyer@example.ru',
  );
  assert.deepEqual(buildOutreachEmailPayload({
    toEmail: ' buyer@example.ru ',
    subject: ' Привет ',
    body: ' Здравствуйте ',
    sender: 'Anna',
  }), {
    to_email: 'buyer@example.ru',
    subject: 'Привет',
    body: 'Здравствуйте',
    sender: 'Anna',
    human_confirmed: true,
  });

  const calls = [];
  const service = createOutreachEmailService({
    client: {
      post(endpoint, body) {
        calls.push({ endpoint, body });
        return Promise.resolve({ status: 'sent', provider: 'fake' });
      },
    },
  });
  const result = await service.sendEmail('customer-1', {
    toEmail: 'buyer@example.ru',
    subject: 'Привет',
    body: 'Здравствуйте',
    sender: 'Anna',
  });

  assert.equal(result.status, 'sent');
  assert.deepEqual(calls, [
    {
      endpoint: '/outreach-drafts/customer-1/send-email',
      body: {
        to_email: 'buyer@example.ru',
        subject: 'Привет',
        body: 'Здравствуйте',
        sender: 'Anna',
        human_confirmed: true,
      },
    },
  ]);
});
