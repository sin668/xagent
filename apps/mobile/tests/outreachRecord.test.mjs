import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  buildOutreachHistoryView,
  buildOutreachRecordPayload,
  canCreateOutreachRecord,
  getOutreachStatusOptions,
  isBackendCustomerId,
} from '../src/services/outreachRecord.js';

const lead = {
  id: 'ru-auto-city',
  grade: 'B',
  doNotContact: false,
};

test('outreach status options include sent, replied, rejected, no response, and bad contact', () => {
  assert.deepEqual(
    getOutreachStatusOptions().map((option) => option.value),
    ['sent', 'replied', 'rejected', 'no_response', 'bad_contact'],
  );
});

test('sent outreach record requires manual confirmation and blocks do-not-contact leads', () => {
  assert.equal(canCreateOutreachRecord({ lead, status: 'sent', manualConfirmed: false }).allowed, false);
  assert.equal(canCreateOutreachRecord({ lead, status: 'sent', manualConfirmed: true }).allowed, true);
  assert.equal(
    canCreateOutreachRecord({ lead: { ...lead, doNotContact: true }, status: 'sent', manualConfirmed: true }).allowed,
    false,
  );
});

test('rejected outreach payload links do-not-contact reason and next action', () => {
  const payload = buildOutreachRecordPayload({
    channel: 'email',
    status: 'rejected',
    sender: 'Anna',
    owner: 'Anna',
    summary: '客户拒绝继续联系',
    nextAction: '标记勿扰',
    manualConfirmed: true,
    doNotContactReason: '客户明确拒绝继续联系',
    scriptVersion: 'TMP-RU-B-001/v1',
  });

  assert.equal(payload.status, 'rejected');
  assert.equal(payload.next_action, '标记勿扰');
  assert.equal(payload.do_not_contact_reason, '客户明确拒绝继续联系');
  assert.equal(payload.manual_confirmed, true);
});

test('outreach payload normalizes display channel names to backend enum values', () => {
  assert.equal(
    buildOutreachRecordPayload({
      channel: 'Email',
      status: 'sent',
      sender: 'Anna',
      owner: 'Anna',
      summary: '已人工发送',
      nextAction: '等待回复',
      manualConfirmed: true,
      scriptVersion: 'TMP-RU-B-001/v1',
    }).channel,
    'email',
  );
  assert.equal(
    buildOutreachRecordPayload({
      channel: 'Telegram 公开频道',
      status: 'sent',
      sender: 'Anna',
      owner: 'Anna',
      summary: '已人工发送',
      nextAction: '等待回复',
      manualConfirmed: true,
      scriptVersion: 'TMP-RU-B-001/v1',
    }).channel,
    'telegram',
  );
  assert.equal(
    buildOutreachRecordPayload({
      channel: '官网 + 邮箱',
      status: 'sent',
      sender: 'Anna',
      owner: 'Anna',
      summary: '已人工发送',
      nextAction: '等待回复',
      manualConfirmed: true,
      scriptVersion: 'TMP-RU-B-001/v1',
    }).channel,
    'email',
  );
});

test('backend customer id check only allows UUID route params', () => {
  assert.equal(isBackendCustomerId('ru-auto-city'), false);
  assert.equal(isBackendCustomerId('550e8400-e29b-41d4-a716-446655440000'), true);
});

test('outreach history view exposes records for lead detail timeline', () => {
  const history = buildOutreachHistoryView([
    {
      id: 'out-1',
      status: 'sent',
      channel: 'email',
      sent_by: 'Anna',
      owner: 'Anna',
      response_summary: '已人工发送',
      next_action: '等待回复',
      script_version: 'TMP-RU-B-001/v1',
    },
  ]);

  assert.equal(history[0].statusLabel, '已发送');
  assert.equal(history[0].title, 'Email · 已发送');
  assert.equal(history[0].detail.includes('等待回复'), true);
});
