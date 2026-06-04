import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  createSourceCandidatesService,
  mapSourceCandidate,
} from '../src/services/sourceCandidates.js';

function createMockClient() {
  const calls = [];
  return {
    calls,
    client: {
      async get(endpoint) {
        calls.push({ method: 'GET', endpoint });
        return {
          items: [
            {
              id: 'source-1',
              source_url: 'https://dealer.example.ru',
              normalized_domain: 'dealer.example.ru',
              platform: 'official_website',
              channel_name: 'dealer_directory',
              country: 'Russia',
              city: 'Moscow',
              risk_level: 'High',
              review_status: 'high_risk_review',
              approved_for_extraction: false,
              evidence_note: '公开页面包含进口车业务信号。',
              evidence_links: ['https://dealer.example.ru'],
              extraction_status: 'pending',
              created_by_task_run_id: 'task-1',
              created_at: '2026-06-02T00:00:00Z',
              updated_at: '2026-06-02T00:00:00Z',
            },
          ],
          total: 1,
          limit: 20,
          offset: 0,
        };
      },
      async post(endpoint, body) {
        calls.push({ method: 'POST', endpoint, body });
        return {
          id: 'source-1',
          review_status: 'approved',
          approved_for_extraction: true,
          audit_task_run_id: 'audit-1',
          reviewed_at: '2026-06-02T01:00:00Z',
        };
      },
    },
  };
}

test('source candidate service lists backend candidates with real query filters', async () => {
  const mock = createMockClient();
  const service = createSourceCandidatesService({ client: mock.client });

  const result = await service.listSourceCandidates({
    riskLevel: 'High',
    reviewStatus: 'high_risk_review',
    country: 'Russia',
    city: 'Moscow',
    platform: 'official_website',
    channelName: 'dealer_directory',
    extractionStatus: 'pending',
    limit: 20,
    offset: 0,
  });

  assert.equal(
    mock.calls[0].endpoint,
    '/lead-source-candidates?risk_level=High&review_status=high_risk_review&country=Russia&city=Moscow&platform=official_website&channel_name=dealer_directory&extraction_status=pending&limit=20&offset=0',
  );
  assert.equal(result.total, 1);
  assert.equal(result.items[0].sourceUrl, 'https://dealer.example.ru');
  assert.equal(result.items[0].riskLevel, 'High');
  assert.equal(result.items[0].approvedForExtraction, false);
});

test('source candidate service loads detail by id without using seed data', async () => {
  const calls = [];
  const service = createSourceCandidatesService({
    client: {
      async get(endpoint) {
        calls.push(endpoint);
        return {
          id: 'source-1',
          source_url: 'https://dealer.example.ru',
          normalized_domain: 'dealer.example.ru',
          risk_level: 'Low',
          review_status: 'auto_approved',
          approved_for_extraction: true,
          evidence_links: ['https://dealer.example.ru'],
          llm_output_summary: { task_type: 'SOURCE_DISCOVERY', candidate_count: 1 },
          created_by_task_run_id: 'task-1',
        };
      },
    },
  });

  const detail = await service.getSourceCandidate('source-1');

  assert.equal(calls[0], '/lead-source-candidates/source-1');
  assert.equal(detail.id, 'source-1');
  assert.equal(detail.llmOutputSummary.taskType, 'SOURCE_DISCOVERY');
  assert.equal(detail.createdByTaskRunId, 'task-1');
});

test('source candidate service sends review actions with backend schema fields', async () => {
  const mock = createMockClient();
  const service = createSourceCandidatesService({ client: mock.client });

  const result = await service.reviewSourceCandidate('source-1', {
    action: 'approve_for_extraction',
    reviewerId: 'ops-reviewer-1',
    reviewNote: 'High 来源人工审核通过，仅允许只读抽取。',
  });

  assert.equal(mock.calls[0].method, 'POST');
  assert.equal(mock.calls[0].endpoint, '/lead-source-candidates/source-1/review-actions');
  assert.deepEqual(mock.calls[0].body, {
    action: 'approve_for_extraction',
    reviewer_id: 'ops-reviewer-1',
    review_note: 'High 来源人工审核通过，仅允许只读抽取。',
  });
  assert.equal(result.auditTaskRunId, 'audit-1');
  assert.equal(result.reviewStatus, 'approved');
});

test('source candidate mapper preserves risk gates and evidence fields for mobile UI', () => {
  const mapped = mapSourceCandidate({
    id: 'source-1',
    source_url: 'https://vk.example/dealer',
    normalized_domain: 'vk.example',
    risk_level: 'High',
    review_status: 'high_risk_review',
    approved_for_extraction: false,
    evidence_note: '公开主页含车商经营信号；不登录、不互动、不触达。',
    evidence_links: ['https://vk.example/dealer'],
    llm_output_summary: { task_type: 'SOURCE_DISCOVERY', blocked_count: 0 },
  });

  assert.equal(mapped.sourceUrl, 'https://vk.example/dealer');
  assert.equal(mapped.riskLevel, 'High');
  assert.equal(mapped.reviewStatus, 'high_risk_review');
  assert.equal(mapped.approvedForExtraction, false);
  assert.equal(mapped.evidenceLinks[0], 'https://vk.example/dealer');
  assert.equal(mapped.llmOutputSummary.taskType, 'SOURCE_DISCOVERY');
});

