import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  buildKnowledgeGovernanceView,
  buildKnowledgeItemsQuery,
  createKnowledgeItemDraft,
  fetchKnowledgeGovernance,
  runKnowledgeRagTest,
  triggerKnowledgeAction,
} from '../src/services/knowledgeGovernance.js';

const knowledgeItemsPayload = {
  items: [
    {
      id: 'item-qa',
      collection_id: 'collection-main',
      title: '合作流程介绍',
      body: '介绍海外车辆采购合作流程。',
      language: 'ru',
      country: 'RU',
      applicable_channels: ['public_web'],
      status: 'active',
      review_status: 'approved',
      source_ref: 'docs/faq/cooperation.md',
      version: 'v1.0',
      content_type: 'qa_entry',
      business_scene: 'first_touch',
      risk_level: 'low',
      auto_reply_allowed: true,
      market: 'ru',
      tone: 'professional',
      rag_eligible: true,
      created_at: '2026-06-05T08:00:00Z',
      updated_at: '2026-06-05T09:00:00Z',
    },
    {
      id: 'item-template',
      collection_id: 'collection-main',
      title: '车型资料说明',
      body: '车型资料回复模板。',
      language: 'en',
      country: 'RU',
      applicable_channels: ['email'],
      status: 'draft',
      review_status: 'pending',
      source_ref: 'manual',
      version: 'v0.2',
      content_type: 'vehicle_product_note',
      business_scene: 'low_risk_followup',
      risk_level: 'medium',
      auto_reply_allowed: false,
      market: 'ru',
      tone: 'concise',
      rag_eligible: false,
      created_at: '2026-06-05T08:30:00Z',
      updated_at: '2026-06-05T08:40:00Z',
    },
  ],
};

const embeddingMetricsPayload = {
  published_knowledge_count: 2,
  embedding_task_count: 3,
  ready_count: 1,
  pending_count: 1,
  failed_count: 1,
  ready_rate: 0.5,
  total_retry_count: 2,
  go_no_go_ready: false,
  failure_reason_groups: [{ reason: 'rate_limit', count: 1 }],
  failed_cases: [
    {
      embedding_id: 'embedding-failed',
      knowledge_title: '车型资料说明',
      embedding_model: 'text-embedding-3-small',
      error_message: 'rate_limit',
      retry_count: 2,
    },
  ],
};

test('knowledge governance view exposes type filters, lifecycle actions, embedding status, and rag test panel', () => {
  const view = buildKnowledgeGovernanceView({
    items: knowledgeItemsPayload,
    embeddingMetrics: embeddingMetricsPayload,
    actorRole: 'operator',
  });

  assert.equal(view.summary.publishedItemCount, 1);
  assert.equal(view.summary.embeddingReadyCount, 1);
  assert.equal(view.summary.autoReplyAllowedCount, 1);
  assert.equal(view.summary.reviewDraftCount, 1);
  assert.equal(view.summary.embeddingReadyRateText, '50.0%');
  assert.equal(view.summary.embeddingStatusClass, 'amber');
  assert.deepEqual(view.tabs.map((tab) => tab.label), ['全部', 'Q&A', '邮件模板', '合规话术', '车型说明', '流程 SOP', '待 embedding']);
  assert.equal(view.items[0].contentTypeLabel, 'Q&A');
  assert.equal(view.items[0].embeddingStatusLabel, 'ready');
  assert.equal(view.items[0].autoReplyLabel, 'yes');
  assert.equal(view.items[1].workflowLabel, '草稿待审');
  assert.equal(view.canCreateOrEdit, true);
  assert.equal(view.canPublish, false);
  assert.equal(view.canRetryEmbedding, false);
  assert.equal(view.actionEntrypoints.map((item) => item.label).join(','), '创建草稿,提交审核,发布,下线,重试 embedding');
  assert.equal(view.ragTestPanel.defaultFilters.language, 'ru');
  assert.equal(view.embeddingFailures[0].retryCount, 2);
});

test('knowledge governance view enables publish and embedding retry for knowledge admin', () => {
  const view = buildKnowledgeGovernanceView({
    items: knowledgeItemsPayload,
    embeddingMetrics: embeddingMetricsPayload,
    actorRole: 'knowledge_admin',
  });

  assert.equal(view.canCreateOrEdit, true);
  assert.equal(view.canPublish, true);
  assert.equal(view.canArchive, true);
  assert.equal(view.canRetryEmbedding, true);
  assert.equal(view.permissionNotice, '当前角色可创建/编辑草稿、提交审核、发布/下线知识，并可重试失败 embedding。');
});

test('knowledge items query supports list filters used by admin tabs', () => {
  assert.equal(buildKnowledgeItemsQuery(), '?limit=100');
  assert.equal(
    buildKnowledgeItemsQuery({
      status: 'active',
      reviewStatus: 'approved',
      language: 'ru',
      contentType: 'qa_entry',
      autoReplyAllowed: true,
      limit: 50,
    }),
    '?status=active&review_status=approved&language=ru&content_type=qa_entry&auto_reply_allowed=true&limit=50',
  );
});

test('fetch knowledge governance calls real knowledge list and embedding metrics APIs', async () => {
  const requestedUrls = [];
  const result = await fetchKnowledgeGovernance({
    baseUrl: 'https://api.example.test/',
    actorRole: 'knowledge_admin',
    filters: { contentType: 'qa_entry', autoReplyAllowed: true },
    fetcher: async (url) => {
      requestedUrls.push(url);
      if (url.includes('/knowledge/items')) {
        return { ok: true, json: async () => knowledgeItemsPayload };
      }
      if (url.endsWith('/knowledge/embeddings/metrics')) {
        return { ok: true, json: async () => embeddingMetricsPayload };
      }
      throw new Error(`Unexpected URL: ${url}`);
    },
  });

  assert.deepEqual(requestedUrls, [
    'https://api.example.test/knowledge/items?content_type=qa_entry&auto_reply_allowed=true&limit=100',
    'https://api.example.test/knowledge/embeddings/metrics',
  ]);
  assert.equal(result.actorRole, 'knowledge_admin');
  assert.equal(result.items.items.length, 2);
  assert.equal(result.embeddingMetrics.ready_count, 1);
});

test('knowledge admin service calls create, workflow, retry, and rag test APIs', async () => {
  const calls = [];
  const fetcher = async (url, options = {}) => {
    calls.push({ url, options });
    if (url.endsWith('/knowledge/items') && options.method === 'POST') {
      return { ok: true, json: async () => ({ id: 'created-item' }) };
    }
    if (url.endsWith('/knowledge/items/item-qa/publish') && options.method === 'POST') {
      return { ok: true, json: async () => ({ id: 'item-qa', status: 'draft' }) };
    }
    if (url.endsWith('/knowledge/embeddings/embedding-failed/retry') && options.method === 'POST') {
      return { ok: true, json: async () => ({ id: 'embedding-failed', embedding_status: 'pending' }) };
    }
    if (url.endsWith('/knowledge/rag-test') && options.method === 'POST') {
      return { ok: true, json: async () => ({ dry_run: true, triggered_send: false, items: [], total: 0 }) };
    }
    throw new Error(`Unexpected URL: ${url}`);
  };

  await createKnowledgeItemDraft({
    baseUrl: 'https://api.example.test/',
    payload: { collection_id: 'collection-main', title: '新 FAQ', body: '内容' },
    fetcher,
  });
  await triggerKnowledgeAction({
    baseUrl: 'https://api.example.test/',
    itemId: 'item-qa',
    action: 'publish',
    actor: 'Ada',
    actorRole: 'knowledge_admin',
    reviewNote: '通过',
    fetcher,
  });
  await triggerKnowledgeAction({
    baseUrl: 'https://api.example.test/',
    embeddingId: 'embedding-failed',
    action: 'retry_embedding',
    fetcher,
  });
  await runKnowledgeRagTest({
    baseUrl: 'https://api.example.test/',
    payload: { query: 'cooperation process', language: 'en', content_types: ['qa_entry'] },
    fetcher,
  });

  assert.equal(calls.length, 4);
  assert.equal(JSON.parse(calls[1].options.body).actor_role, 'knowledge_admin');
  assert.equal(JSON.parse(calls[3].options.body).triggered_send, undefined);
});
