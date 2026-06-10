import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  buildPromoteStagingPayload,
  buildLeadDetailViewModel,
  canEnterOutreachQueue,
  markLeadDoNotContact,
  unmarkLeadDoNotContact,
} from '../src/services/leadDetail.js';

const baseLead = {
  id: 'ru-auto-city',
  customerName: 'AutoCity Moscow',
  country: 'Russia',
  city: 'Moscow',
  customerType: '当地车商/二级经销商',
  grade: 'B',
  riskLevel: 'Low',
  operatingSummary: '官网展示进口二手车库存，近期更新，门店地址清晰。',
  aiRecommendation: {
    confidence: 0.84,
    suggestion: '建议交付客服，先确认是否长期采购中国二手/准新车。',
    reason: '公开官网展示进口二手车库存，公开邮箱可联系，城市和经营类型清晰。',
    missingInfo: ['主营车型', '月采购量'],
    nextAction: '人工触达',
  },
  sources: [
    {
      type: '官网来源',
      url: 'https://autocity.example.ru',
      evidence: '展示进口二手车库存与门店地址。',
    },
  ],
  contacts: [
    { type: 'Email', value: 'sales@autocity.example.ru', usage: '人工邮件触达' },
  ],
  followUps: [
    { title: '待客服首次触达', detail: '分配给 Anna，剩余 18 小时。' },
  ],
  inventoryMatch: {
    label: '查看 6 台匹配车源',
    path: '/pages/inventory/index?leadId=ru-auto-city',
  },
  doNotContact: false,
};

test('lead detail view model exposes customer basics, evidence, AI advice, contacts, and follow-ups', () => {
  const detail = buildLeadDetailViewModel(baseLead);

  assert.equal(detail.customerName, 'AutoCity Moscow');
  assert.equal(detail.basicInfo, 'Moscow · 当地车商/二级经销商');
  assert.equal(detail.sources.length, 1);
  assert.equal(detail.sources[0].url, 'https://autocity.example.ru');
  assert.equal(detail.hasViewableEvidence, true);
  assert.equal(detail.aiAdvice.confidenceText, '84%');
  assert.deepEqual(detail.aiAdvice.missingInfo, ['主营车型', '月采购量']);
  assert.equal(detail.contacts[0].value, 'sales@autocity.example.ru');
  assert.equal(detail.followUps[0].title, '待客服首次触达');
  assert.equal(detail.inventoryEntry.label, '查看 6 台匹配车源');
  assert.equal(detail.outreachActionLabel, '晋级客户');
  assert.equal(detail.autoSendEnabled, false);
});

test('C grade lead detail displays sales handoff and compliance review status', () => {
  const detail = buildLeadDetailViewModel({
    ...baseLead,
    grade: 'C',
    handoffTeam: 'export_sales',
    complianceReviewStatus: 'required',
  });

  assert.equal(detail.gradeLabel, 'C 级');
  assert.equal(detail.handoffLabel, '交付销售');
  assert.equal(detail.complianceLabel, '待合规复核');
});

test('lead cannot enter outreach queue after being marked do-not-contact', () => {
  const marked = markLeadDoNotContact(baseLead, {
    actor: 'Anna',
    reason: '客户明确拒绝继续联系',
    markedAt: '2026-05-28T12:00:00Z',
  });

  assert.equal(marked.doNotContact, true);
  assert.equal(marked.doNotContactReason, '客户明确拒绝继续联系');
  assert.equal(marked.doNotContactMarkedBy, 'Anna');
  assert.equal(canEnterOutreachQueue(marked), false);
  assert.equal(buildLeadDetailViewModel(marked).outreachActionLabel, '已排除触达');
});

test('do-not-contact lead can be manually restored to normal queue state', () => {
  const marked = markLeadDoNotContact(baseLead, {
    actor: 'Anna',
    reason: '客户明确拒绝继续联系',
    markedAt: '2026-05-28T12:00:00Z',
  });
  const restored = unmarkLeadDoNotContact(marked, {
    actor: '主管B',
    reason: '客户重新同意沟通',
  });

  assert.equal(restored.doNotContact, false);
  assert.equal(restored.status, 'pending');
  assert.equal(restored.doNotContactReason, '取消勿扰：客户重新同意沟通');
  assert.equal(canEnterOutreachQueue(restored), true);
});

test('AI outreach draft is available only when lead has an email contact', () => {
  const emailDetail = buildLeadDetailViewModel(baseLead);
  const noEmailDetail = buildLeadDetailViewModel({
    ...baseLead,
    contacts: [{ type: 'telegram', value: '@autocity' }],
  });

  assert.equal(emailDetail.canCreateOutreachDraft, true);
  assert.equal(noEmailDetail.canCreateOutreachDraft, false);
});

test('source evidence is not considered viewable without url or evidence text', () => {
  const detail = buildLeadDetailViewModel({
    ...baseLead,
    sources: [{ type: 'Unknown', url: '', evidence: '' }],
  });

  assert.equal(detail.hasViewableEvidence, false);
});

test('lead detail disables promotion when core gate blocks missing evidence or source', () => {
  const detail = buildLeadDetailViewModel({
    ...baseLead,
    sources: [],
    coreGate: {
      status: 'blocked',
      canPromoteToCore: false,
      reasons: ['缺少来源证据'],
    },
  });

  assert.equal(detail.hasViewableEvidence, false);
  assert.equal(detail.coreGate.status, 'blocked');
  assert.equal(detail.coreGateLabel, '不可进入 core');
  assert.equal(detail.canEnterOutreachQueue, false);
  assert.equal(detail.outreachActionLabel, '待补证据');
  assert.deepEqual(detail.coreGate.reasons, ['缺少来源证据']);
});

test('promote staging payload records actor, accepted fields, and manual review note', () => {
  const payload = buildPromoteStagingPayload({
    actor: 'ops-anna',
    reviewNote: '来源和证据完整，人工确认晋级。',
  });

  assert.deepEqual(payload, {
    actor: 'ops-anna',
    accepted_fields_json: {
      customer_name: { source: 'mobile_manual_review' },
      contacts_json: { source: 'mobile_manual_review' },
      source_evidence: { source: 'mobile_manual_review' },
    },
    review_note: '来源和证据完整，人工确认晋级。',
  });
});

test('lead detail blocks promotion when duplicate signals require manual review', () => {
  const detail = buildLeadDetailViewModel({
    ...baseLead,
    duplicateSignals: {
      hasStrongDuplicate: true,
      blocksPromotion: true,
      requiresManualReview: true,
      strongDuplicates: [{ reason: '同名同邮箱' }],
    },
  });

  assert.equal(detail.duplicateLabel, '强重复阻断');
  assert.equal(detail.canEnterOutreachQueue, false);
  assert.equal(detail.outreachActionLabel, '重复待处理');
});

test('线索详情页面展示清洗原因并提供底部人工调级入口', async () => {
  const { readFileSync } = await import('node:fs');
  const page = readFileSync(new URL('../src/pages/leads/detail.vue', import.meta.url), 'utf8');

  assert.match(page, /清洗原因/);
  assert.match(page, /cleanupReasons/);
  assert.match(page, /leadCleanupService/);
  assert.match(page, /stagingLeadActionsService/);
  assert.match(page, /调整等级/);
  assert.match(page, /handleUpdateGrade/);
  assert.match(page, /A级/);
  assert.match(page, /B级/);
  assert.match(page, /C级/);
  assert.match(page, /D级/);
  assert.match(page, /E级/);
});

test('线索详情页面底部提供人工晋级客户按钮并调用 promote-to-customer', async () => {
  const { readFileSync } = await import('node:fs');
  const page = readFileSync(new URL('../src/pages/leads/detail.vue', import.meta.url), 'utf8');

  assert.match(page, /晋级客户/);
  assert.match(page, /handleManualPromoteCustomer/);
  assert.match(page, /const stagingLeadId = getStagingLeadId\(\)/);
  assert.match(page, /\/staging-leads\/\$\{encodeURIComponent\(stagingLeadId\)\}\/promote-to-customer/);
  assert.match(page, /buildPromoteStagingPayload/);
  assert.match(page, /已晋级客户/);
});

test('线索详情调级和 staging 专属操作不再把客户ID当 staging lead ID', async () => {
  const { readFileSync } = await import('node:fs');
  const page = readFileSync(new URL('../src/pages/leads/detail.vue', import.meta.url), 'utf8');

  assert.match(page, /function getStagingLeadId\(\)/);
  assert.match(page, /stagingLeadActionsService\.updateGrade\(stagingLeadId/);
  assert.match(page, /enrichmentService\.listEnrichmentResults\(stagingLeadId\)/);
  assert.match(page, /leadId: stagingLeadId/);
  assert.doesNotMatch(page, /stagingLeadActionsService\.updateGrade\(detail\.value\.id/);
  assert.doesNotMatch(page, /enrichmentService\.listEnrichmentResults\(detail\.value\.id\)/);
});

test('线索详情不再把已晋级客户兜底展示为线索详情', async () => {
  const { readFileSync } = await import('node:fs');
  const page = readFileSync(new URL('../src/pages/leads/detail.vue', import.meta.url), 'utf8');

  assert.match(page, /\/customers\/\$\{encodeURIComponent\(leadId\)\}/);
  assert.match(page, /globalThis\.uni\?\.redirectTo/);
  assert.match(page, /\/pages\/customers\/detail\?id=/);
  assert.doesNotMatch(page, /mapCustomerDetailToLeadDetail/);
  assert.doesNotMatch(page, /mapCustomerSummaryToLeadDetail/);
});

test('线索详情底部四个按钮单行显示并支持取消勿扰和邮箱触达门禁', async () => {
  const { readFileSync } = await import('node:fs');
  const page = readFileSync(new URL('../src/pages/leads/detail.vue', import.meta.url), 'utf8');
  const css = readFileSync(new URL('../src/styles/leadDetail.css', import.meta.url), 'utf8');

  assert.match(page, /取消勿扰/);
  assert.match(page, /handleToggleDoNotContact/);
  assert.match(page, /getDoNotContactCustomerId/);
  assert.match(page, /doNotContactCustomerId/);
  assert.match(page, /\/do-not-contact\/cancel/);
  assert.doesNotMatch(page, /\/customers\/\$\{encodeURIComponent\(detail\.value\.id\)\}\/do-not-contact\/cancel/);
  assert.match(page, /AI触达草稿/);
  assert.match(page, /canCreateOutreachDraft/);
  assert.match(page, /openOutreach/);
  assert.doesNotMatch(page, /handlePromoteStaging/);
  assert.doesNotMatch(page, />\s*\{\{\s*detail\.outreachActionLabel\s*\}\}\s*</);
  assert.doesNotMatch(page, />\s*晋级core\s*</);
  assert.match(css, /\.action-bar\s*{[^}]*grid-template-columns:\s*repeat\(4,\s*minmax\(0,\s*1fr\)\)/s);
});
