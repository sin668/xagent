import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  buildLlmGovernanceView,
  buildPromptGovernanceView,
  buildPromptTemplateQuery,
  fetchPromptGovernance,
  fetchLlmGovernance,
} from '../src/services/llmGovernance.js';

const healthPayload = {
  provider: 'deepseek',
  models: {
    default: 'deepseek-chat',
    source_discovery: 'deepseek-chat',
    extraction: 'deepseek-chat',
    grading: 'deepseek-chat',
  },
  base_url_configured: true,
  api_key_configured: true,
  configuration_complete: true,
};

const templatesPayload = {
  total: 2,
  items: [
    {
      id: 'template-source',
      name: 'source_discovery_default',
      task_type: 'SOURCE_DISCOVERY',
      provider: 'deepseek',
      model: 'deepseek-chat',
      system_prompt: '只允许公开来源发现，不得自动私信。',
      user_prompt_template: '国家：{country}',
      output_schema_json: {
        type: 'object',
        required: ['task_type', 'candidates', 'blocked_candidates'],
        properties: {
          task_type: { type: 'string' },
          candidates: { type: 'array' },
          blocked_candidates: { type: 'array' },
        },
      },
      version: 'v1.0',
      status: 'active',
      is_default: true,
      created_by: 'system',
      created_at: '2026-06-02T10:00:00Z',
      updated_at: '2026-06-02T11:00:00Z',
    },
    {
      id: 'template-draft',
      name: 'social_high_review_probe',
      task_type: 'SOURCE_DISCOVERY',
      provider: 'deepseek',
      model: 'deepseek-chat',
      system_prompt: 'High 风险仅人工小样本。',
      user_prompt_template: '渠道：{channel}',
      output_schema_json: {
        type: 'object',
        required: ['blocked_candidates'],
        properties: {
          blocked_candidates: { type: 'array' },
        },
      },
      version: 'v0.4',
      status: 'draft',
      is_default: false,
      created_by: 'admin',
      created_at: '2026-06-01T10:00:00Z',
      updated_at: '2026-06-01T11:00:00Z',
    },
  ],
};

test('llm governance view exposes provider health, prompt versions, schema summary, and read-only boundaries', () => {
  const view = buildLlmGovernanceView({ health: healthPayload, templates: templatesPayload });

  assert.equal(view.providerHealth.providerName, 'deepseek');
  assert.equal(view.providerHealth.statusLabel, 'Health OK');
  assert.equal(view.providerHealth.statusClass, 'green');
  assert.equal(view.providerHealth.apiKeyVisible, false);
  assert.equal(view.providerHealth.modelSummary, 'default: deepseek-chat / source_discovery: deepseek-chat / extraction: deepseek-chat / grading: deepseek-chat');

  assert.equal(view.promptTemplates.length, 2);
  assert.equal(view.promptTemplates[0].name, 'source_discovery_default');
  assert.equal(view.promptTemplates[0].defaultLabel, 'yes');
  assert.equal(view.promptTemplates[0].schemaSummary, 'required: task_type, candidates, blocked_candidates');
  assert.equal(view.promptTemplates[0].statusClass, 'green');
  assert.equal(view.promptTemplates[1].statusClass, 'amber');

  assert.equal(view.defaultTemplates.length, 1);
  assert.equal(view.schemaPreview.name, 'source_discovery_default');
  assert.equal(view.schemaPreview.schemaText.includes('"candidates"'), true);

  assert.equal(view.fallbackBoundaries.length, 4);
  assert.equal(view.fallbackBoundaries[0].decisionLabel, '可 fallback');
  assert.equal(view.fallbackBoundaries[1].decisionLabel, '不 fallback');
  assert.equal(view.readOnlyNotice, '第二阶段只读：普通运营不可创建、编辑或删除 prompt template。');
});

test('prompt template query supports read-only filters', () => {
  assert.equal(buildPromptTemplateQuery(), '');
  assert.equal(
    buildPromptTemplateQuery({ taskType: 'SOURCE_DISCOVERY', status: 'active', isDefault: true }),
    '?task_type=SOURCE_DISCOVERY&status=active&is_default=true',
  );
});

test('fetch llm governance calls health and prompt template read-only APIs without exposing api key', async () => {
  const requestedUrls = [];
  const result = await fetchLlmGovernance({
    baseUrl: 'https://api.example.test/',
    fetcher: async (url) => {
      requestedUrls.push(url);
      if (url.endsWith('/llm-health')) {
        return { ok: true, json: async () => healthPayload };
      }
      if (url.endsWith('/llm-prompt-templates')) {
        return { ok: true, json: async () => templatesPayload };
      }
      throw new Error(`Unexpected URL: ${url}`);
    },
  });

  assert.deepEqual(requestedUrls, [
    'https://api.example.test/llm-health',
    'https://api.example.test/llm-prompt-templates',
  ]);
  assert.equal(result.health.api_key, undefined);
  assert.equal(result.health.provider, 'deepseek');
  assert.equal(result.templates.total, 2);
});

test('prompt governance view exposes coverage, source hash, validation, and permission-gated actions', () => {
  const view = buildPromptGovernanceView({
    templates: templatesPayload,
    actorRole: 'operator',
    expectedTaskTypes: ['SOURCE_DISCOVERY', 'LEAD_EXTRACTION', 'LEAD_GRADING', 'EMAIL_REPLY_DRAFT'],
  });

  assert.equal(view.summary.importedPromptCount, 2);
  assert.equal(view.summary.activeDefaultCount, 1);
  assert.equal(view.summary.draftValidationPendingCount, 1);
  assert.equal(view.summary.schemaErrorCount, 0);
  assert.equal(view.summary.coverageRateText, '25%');
  assert.equal(view.summary.coverageStatusClass, 'amber');
  assert.equal(view.templates[0].sourceHashShort, 'Unknown');
  assert.equal(view.templates[0].validationStatusLabel, '未校验');
  assert.equal(view.canEditDraft, false);
  assert.equal(view.canPublish, false);
  assert.equal(view.canRollback, false);
  assert.equal(view.permissionNotice, '当前角色只能查看 Prompt 入库治理，编辑、发布和回滚入口已禁用。');
});

test('prompt governance view enables publish and rollback actions for tech admin', () => {
  const view = buildPromptGovernanceView({
    templates: {
      items: [
        {
          ...templatesPayload.items[0],
          source_file_hash: 'abcdef1234567890',
          validation_status: 'validation_passed',
        },
        {
          ...templatesPayload.items[1],
          source_file_hash: 'fedcba9876543210',
          validation_status: 'validation_failed',
          validation_errors_json: { missing_variables: ['customer_context'] },
        },
      ],
    },
    actorRole: 'tech_admin',
    expectedTaskTypes: ['SOURCE_DISCOVERY', 'LEAD_EXTRACTION'],
  });

  assert.equal(view.canEditDraft, true);
  assert.equal(view.canPublish, true);
  assert.equal(view.canRollback, true);
  assert.equal(view.summary.coverageRateText, '50%');
  assert.equal(view.templates[0].sourceHashShort, 'abcdef12');
  assert.equal(view.templates[0].validationStatusLabel, '通过');
  assert.equal(view.templates[1].validationStatusLabel, '失败');
  assert.equal(view.templates[1].validationErrorsText, 'missing_variables: customer_context');
  assert.equal(view.actionEntrypoints.map((item) => item.label).join(','), '校验草稿,发布版本,回滚版本');
});

test('fetch prompt governance calls real prompt template API with role context', async () => {
  const requestedUrls = [];
  const result = await fetchPromptGovernance({
    baseUrl: 'https://api.example.test/',
    actorRole: 'tech_admin',
    fetcher: async (url) => {
      requestedUrls.push(url);
      if (url.endsWith('/llm-prompt-templates')) {
        return { ok: true, json: async () => templatesPayload };
      }
      throw new Error(`Unexpected URL: ${url}`);
    },
  });

  assert.deepEqual(requestedUrls, ['https://api.example.test/llm-prompt-templates']);
  assert.equal(result.actorRole, 'tech_admin');
  assert.equal(result.templates.total, 2);
});
