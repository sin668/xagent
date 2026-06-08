import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

import {
  buildAcceptFieldCandidatePayload,
  buildLeadEnrichmentViewModel,
  buildManualEnrichmentPayload,
  buildRejectFieldCandidatePayload,
  createLeadEnrichmentService,
} from '../src/services/leadEnrichment.js';

const baseLead = {
  id: '45d1480c-76c9-4297-86e8-f5a1f2e30d96',
  customerName: 'AutoCity Moscow',
  grade: 'B',
  status: 'pending',
  riskLevel: 'Low',
  doNotContact: false,
};

const enrichmentPayload = {
  staging_lead_id: baseLead.id,
  items: [
    {
      id: 'run-1',
      enrichment_type: 'ai_deep_research',
      triggered_by: 'ops-anna',
      status: 'succeeded',
      evidence_links: ['https://autocity.example.ru/about'],
      confidence_score: 0.82,
      missing_fields: ['月采购量'],
      recommended_action: '建议人工确认后晋级客户',
      created_at: '2026-06-04T10:00:00Z',
      field_candidates: [
        {
          id: 'candidate-1',
          field_name: '经营状况',
          candidate_value: '官网展示进口二手车库存和门店地址',
          source_type: 'ai_public_source',
          source_url: 'https://autocity.example.ru/about',
          evidence_note: '页面公开展示 imported used cars 与 showroom 地址',
          confidence_score: 0.88,
          review_status: 'pending',
        },
        {
          id: 'candidate-2',
          field_name: '联系方式',
          candidate_value: 'sales@autocity.example.ru',
          source_type: 'manual_public_info',
          source_url: 'https://autocity.example.ru/contact',
          evidence_note: '联系页公开邮箱',
          confidence_score: 0.95,
          review_status: 'accepted',
          accepted_by: 'ops-anna',
        },
      ],
    },
  ],
};

test('线索完善视图展示字段候选、证据、置信度和采纳状态', () => {
  const view = buildLeadEnrichmentViewModel({
    lead: baseLead,
    resultsPayload: enrichmentPayload,
  });

  assert.equal(view.canTriggerDeepEnrichment, true);
  assert.equal(view.triggerButtonLabel, '深挖线索');
  assert.equal(view.results.length, 1);
  assert.equal(view.results[0].statusLabel, '已完成');
  assert.equal(view.results[0].confidenceText, '82%');
  assert.equal(view.fieldCandidates.length, 2);
  assert.equal(view.fieldCandidates[0].fieldName, '经营状况');
  assert.equal(view.fieldCandidates[0].evidenceNote, '页面公开展示 imported used cars 与 showroom 地址');
  assert.equal(view.fieldCandidates[0].confidenceText, '88%');
  assert.equal(view.fieldCandidates[0].reviewStatusLabel, '待采纳');
  assert.equal(view.fieldCandidates[1].reviewStatusLabel, '已采纳');
});

test('Watch、Invalid、勿扰和 Forbidden 线索不允许触发深挖', () => {
  const blockedCases = [
    { ...baseLead, status: 'watch' },
    { ...baseLead, grade: 'Watch' },
    { ...baseLead, status: 'invalid' },
    { ...baseLead, grade: 'Invalid' },
    { ...baseLead, doNotContact: true },
    { ...baseLead, riskLevel: 'Forbidden' },
  ];

  for (const lead of blockedCases) {
    const view = buildLeadEnrichmentViewModel({ lead, resultsPayload: { items: [] } });
    assert.equal(view.canTriggerDeepEnrichment, false);
    assert.match(view.blockReason, /不允许深挖|勿扰|Forbidden/);
  }
});

test('字段候选采纳、拒绝和人工补录 payload 保留人工审计信息', () => {
  assert.deepEqual(buildAcceptFieldCandidatePayload({ actor: 'ops-anna' }), {
    accepted_by: 'ops-anna',
  });
  assert.deepEqual(buildRejectFieldCandidatePayload({ reason: '证据不足' }), {
    rejected_reason: '证据不足',
  });
  assert.deepEqual(
    buildManualEnrichmentPayload({
      operator: 'ops-anna',
      note: '人工从官网联系页补录',
      fields: [
        {
          fieldName: '邮箱',
          candidateValue: 'sales@autocity.example.ru',
          sourceUrl: 'https://autocity.example.ru/contact',
          evidenceNote: '联系页公开邮箱',
          confidenceScore: 0.95,
        },
      ],
    }),
    {
      operator: 'ops-anna',
      note: '人工从官网联系页补录',
      fields: [
        {
          field_name: '邮箱',
          candidate_value: 'sales@autocity.example.ru',
          source_type: 'manual_public_info',
          source_url: 'https://autocity.example.ru/contact',
          evidence_note: '联系页公开邮箱',
          confidence_score: 0.95,
        },
      ],
    },
  );
});

test('线索完善服务调用后端深挖、查询、采纳、拒绝和人工补录接口', async () => {
  const calls = [];
  const apiClient = {
    get(endpoint) {
      calls.push(['GET', endpoint]);
      return Promise.resolve(enrichmentPayload);
    },
    post(endpoint, body) {
      calls.push(['POST', endpoint, body]);
      return Promise.resolve({ id: 'run-1' });
    },
    patch(endpoint, body) {
      calls.push(['PATCH', endpoint, body]);
      return Promise.resolve({ id: 'candidate-1' });
    },
  };
  const service = createLeadEnrichmentService({ apiClient });

  await service.createEnrichmentRun(baseLead.id, { actor: 'ops-anna', manualKeywords: ['AutoCity import'] });
  await service.listEnrichmentResults(baseLead.id);
  await service.acceptFieldCandidate('candidate-1', { actor: 'ops-anna' });
  await service.rejectFieldCandidate('candidate-2', { reason: '证据不足' });
  await service.createManualEnrichment(baseLead.id, {
    operator: 'ops-anna',
    fields: [{ fieldName: '邮箱', candidateValue: 'sales@autocity.example.ru', evidenceNote: '联系页公开邮箱' }],
  });

  assert.deepEqual(calls, [
    [
      'POST',
      `/staging-leads/${baseLead.id}/enrichment-runs`,
      {
        triggered_by: 'ops-anna',
        manual_keywords: ['AutoCity import'],
        allowed_channel_scope: [],
        note: null,
      },
    ],
    ['GET', `/staging-leads/${baseLead.id}/enrichment-results`],
    ['PATCH', '/lead-enrichment-field-candidates/candidate-1/accept', { accepted_by: 'ops-anna' }],
    ['PATCH', '/lead-enrichment-field-candidates/candidate-2/reject', { rejected_reason: '证据不足' }],
    [
      'POST',
      `/staging-leads/${baseLead.id}/manual-enrichment`,
      {
        operator: 'ops-anna',
        note: null,
        fields: [
          {
            field_name: '邮箱',
            candidate_value: 'sales@autocity.example.ru',
            source_type: 'manual_public_info',
            source_url: null,
            evidence_note: '联系页公开邮箱',
            confidence_score: null,
          },
        ],
      },
    ],
  ]);
});

test('线索详情人工补录入口要求用户输入真实字段，不提交占位数据', () => {
  const pageSource = readFileSync(new URL('../src/pages/leads/detail.vue', import.meta.url), 'utf8');

  assert.match(pageSource, /manualFieldName/);
  assert.match(pageSource, /manualCandidateValue/);
  assert.match(pageSource, /manualEvidenceNote/);
  assert.doesNotMatch(pageSource, /candidateValue:\s*'待补充'/);
  assert.doesNotMatch(pageSource, /人工补录备注/);
});
