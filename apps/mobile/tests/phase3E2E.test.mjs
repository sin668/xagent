import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

import {
  PHASE3_MOBILE_E2E_PAGES,
  createPhase3MobileE2EVerifier,
  summarizePhase3MobileE2E,
} from '../src/services/phase3E2E.js';

test('第三阶段移动端联调页面覆盖线索完善、清洗建议、客户工作台、客户详情和跟进记录', () => {
  const srcPages = JSON.parse(readFileSync(new URL('../src/pages.json', import.meta.url), 'utf8'));
  const rootPages = JSON.parse(readFileSync(new URL('../pages.json', import.meta.url), 'utf8'));

  for (const page of PHASE3_MOBILE_E2E_PAGES) {
    assert.ok(srcPages.pages.some((item) => item.path === page.srcPath), `${page.srcPath} 未注册到 src/pages.json`);
    assert.ok(rootPages.pages.some((item) => item.path === page.rootPath), `${page.rootPath} 未注册到 pages.json`);
  }
});

test('第三阶段移动端联调验收按真实 API 串起完善、晋级、客户、跟进和清洗建议', async () => {
  const calls = [];
  const client = {
    get(endpoint) {
      calls.push(['GET', endpoint]);
      if (endpoint === '/staging-leads/lead-1/enrichment-results') {
        return Promise.resolve({
          items: [
            {
              id: 'run-1',
              enrichment_type: 'manual_enrichment',
              status: 'succeeded',
              confidence_score: 0.9,
              field_candidates: [],
            },
          ],
        });
      }
      if (endpoint === '/customers?limit=20') {
        return Promise.resolve({
          items: [
            {
              id: 'customer-1',
              name: 'AutoCity Moscow',
              country: 'Russia',
              city: 'Moscow',
              grade: 'B',
              status: 'active',
              contact_summary: { primary: 'email:sales@example.ru' },
              vehicle_intent_summary: { total: 1, items: [{ label: 'Toyota Camry' }] },
              next_action: '今日待跟进',
              next_action_priority: 1,
            },
          ],
        });
      }
      if (endpoint === '/customers/customer-1') {
        return Promise.resolve({
          id: 'customer-1',
          profile: {
            id: 'customer-1',
            name: 'AutoCity Moscow',
            country: 'Russia',
            city: 'Moscow',
            grade: 'B',
            status: 'active',
          },
          contacts: [{ id: 'contact-1', type: 'email', value: 'sales@example.ru', is_primary: true }],
          sources: [{ id: 'source-1', platform: 'website', source_url: 'https://example.ru', risk_level: 'Low' }],
          vehicle_intents: [{ id: 'intent-1', brand: 'Toyota', model: 'Camry', status: 'active' }],
          outreach_history: [],
          followups: [],
        });
      }
      if (endpoint === '/customers/customer-1/followups') {
        return Promise.resolve([
          {
            id: 'followup-1',
            customer_id: 'customer-1',
            team: 'customer_service',
            followup_type: 'internal_note',
            content: '人工记录客户反馈。',
            created_by: 'ops-a',
            created_at: '2026-06-04T10:00:00+08:00',
          },
        ]);
      }
      if (endpoint === '/lead-cleanup/suggestions?review_status=pending&limit=20') {
        return Promise.resolve({
          total: 1,
          items: [
            {
              id: 'cleanup-1',
              suggestion_type: 'possible_duplicate',
              review_status: 'pending',
              reason: '疑似重复客户名称',
              evidence_json: { evidence_note: '名称和城市相同' },
            },
          ],
        });
      }
      throw new Error(`未预期 GET ${endpoint}`);
    },
    post(endpoint, payload) {
      calls.push(['POST', endpoint, payload]);
      if (endpoint === '/staging-leads/lead-1/manual-enrichment') {
        return Promise.resolve({ id: 'manual-run-1' });
      }
      if (endpoint === '/staging-leads/lead-1/promote-to-customer') {
        return Promise.resolve({ customer_id: 'customer-1' });
      }
      if (endpoint === '/customers/customer-1/followups') {
        return Promise.resolve({
          id: 'followup-2',
          customer_id: 'customer-1',
          team: 'customer_service',
          followup_type: 'internal_note',
          content: payload.content,
          created_by: payload.created_by,
          created_at: '2026-06-04T11:00:00+08:00',
        });
      }
      throw new Error(`未预期 POST ${endpoint}`);
    },
    patch(endpoint, payload) {
      calls.push(['PATCH', endpoint, payload]);
      if (endpoint === '/lead-cleanup/suggestions/cleanup-1/approve') {
        return Promise.resolve({
          id: 'cleanup-1',
          suggestion_type: 'possible_duplicate',
          review_status: 'approved',
          reason: '疑似重复客户名称',
          evidence_json: { evidence_note: '名称和城市相同' },
        });
      }
      throw new Error(`未预期 PATCH ${endpoint}`);
    },
  };

  const verifier = createPhase3MobileE2EVerifier({ client });
  const report = await verifier.run({
    leadId: 'lead-1',
    customerId: 'customer-1',
    actor: 'ops-a',
    manualField: {
      fieldName: '邮箱',
      candidateValue: 'sales@example.ru',
      sourceUrl: 'https://example.ru/contact',
      evidenceNote: '官网联系页公开邮箱',
    },
  });

  assert.equal(report.leadEnrichment.status, 'passed');
  assert.equal(report.promotion.status, 'passed');
  assert.equal(report.customerWorkbench.status, 'passed');
  assert.equal(report.customerDetail.status, 'passed');
  assert.equal(report.customerFollowups.status, 'passed');
  assert.equal(report.cleanupSuggestions.status, 'passed');
  assert.equal(report.safety.noAutoOutreach, true);
  assert.equal(report.safety.noSeedOrMock, true);
  const promotionCall = calls.find((item) => item[0] === 'POST' && item[1] === '/staging-leads/lead-1/promote-to-customer');
  assert.deepEqual(promotionCall[2].accepted_fields_json, {
    customer_name: { source: 'mobile_manual_review' },
    contacts_json: { source: 'mobile_manual_review' },
    source_evidence: { source: 'mobile_manual_review' },
  });
  assert.deepEqual(
    calls.map((item) => item.slice(0, 2)),
    [
      ['POST', '/staging-leads/lead-1/manual-enrichment'],
      ['GET', '/staging-leads/lead-1/enrichment-results'],
      ['POST', '/staging-leads/lead-1/promote-to-customer'],
      ['GET', '/customers?limit=20'],
      ['GET', '/customers/customer-1'],
      ['GET', '/customers/customer-1/followups'],
      ['POST', '/customers/customer-1/followups'],
      ['GET', '/lead-cleanup/suggestions?review_status=pending&limit=20'],
      ['PATCH', '/lead-cleanup/suggestions/cleanup-1/approve'],
    ],
  );
});

test('第三阶段移动端联调摘要能输出中文验收结论和阻断项', () => {
  const summary = summarizePhase3MobileE2E({
    leadEnrichment: { status: 'passed' },
    promotion: { status: 'passed' },
    customerWorkbench: { status: 'passed' },
    customerDetail: { status: 'passed' },
    customerFollowups: { status: 'passed' },
    cleanupSuggestions: { status: 'failed', reason: '无待复核清洗建议' },
    safety: { noAutoOutreach: true, noSeedOrMock: true },
  });

  assert.equal(summary.ready, false);
  assert.match(summary.text, /清洗建议/);
  assert.match(summary.text, /无待复核清洗建议/);
});

test('第三阶段移动端联调验收拒绝缺少真实字段的人工补录输入', async () => {
  const calls = [];
  const verifier = createPhase3MobileE2EVerifier({
    client: {
      get(endpoint) {
        calls.push(['GET', endpoint]);
        return Promise.resolve({});
      },
      post(endpoint, payload) {
        calls.push(['POST', endpoint, payload]);
        return Promise.resolve({});
      },
      patch(endpoint, payload) {
        calls.push(['PATCH', endpoint, payload]);
        return Promise.resolve({});
      },
    },
  });

  const report = await verifier.run({
    leadId: 'lead-1',
    customerId: 'customer-1',
    actor: 'ops-a',
    manualField: {
      fieldName: '',
      candidateValue: '',
      evidenceNote: '',
    },
  });

  assert.equal(report.leadEnrichment.status, 'failed');
  assert.match(report.leadEnrichment.reason, /人工补录字段/);
  assert.deepEqual(calls, []);
});
