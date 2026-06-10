import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const appSource = readFileSync(new URL('../src/App.vue', import.meta.url), 'utf8');
const pageRuntimeSource = readFileSync(new URL('../src/pages/pageRuntime.js', import.meta.url), 'utf8');

const pageContracts = [
  ['runtime-overview', 'RuntimeOverviewPage.vue', 'fetchRuntimeOverview'],
  ['lead-channels', 'LeadChannelsPage.vue', ['ChannelsPage', 'RiskConfigPage', 'QueuesPage', 'RiskAuditPage']],
  ['sync-audit', 'SyncAuditPage.vue', 'fetchSyncAiAuditDashboard'],
  ['phase2', 'Phase2Page.vue', 'fetchPhase2Dashboard'],
  ['phase3', 'Phase3Page.vue', 'fetchPhase3Dashboard'],
  ['llm-model-governance', 'LlmModelGovernancePage.vue', ['PromptGovernancePage', 'LlmGovernancePage']],
  ['knowledge-governance', 'KnowledgeGovernancePage.vue', 'fetchKnowledgeGovernance'],
  ['email-reply-review', 'EmailReplyReviewPage.vue', 'fetchEmailReplyReview'],
  ['phase5-integration', 'Phase5IntegrationPage.vue', 'fetchPhase5AdminIntegration'],
];

const removedMenuKeys = ['overview', 'channels', 'risk-config', 'queues', 'risk-audit', 'prompt-governance', 'llm-governance', 'email-quality'];

function readPage(filename) {
  return readFileSync(new URL(`../src/pages/${filename}`, import.meta.url), 'utf8');
}

test('admin App shell only manages menu and renders independent page components', () => {
  assert.match(appSource, /<component :is="activePage\.component"/);
  assert.match(appSource, /menuItems/);
  assert.doesNotMatch(appSource, /adminOverviewSeed|channelRiskConfigSeed|syncAiAuditSeed/);
  assert.doesNotMatch(appSource, /<section id="channels"|<section id="phase2"|<section id="llm-governance"/);
});

test('each admin menu maps to one independent page file', () => {
  for (const [key, filename] of pageContracts) {
    assert.match(appSource, new RegExp(`key: '${key}'`));
    assert.match(appSource, new RegExp(filename.replace(/\.vue$/, '')));
    const pageSource = readPage(filename);
    assert.match(pageSource, new RegExp(`id="${key}"`));
  }
});

test('each admin page calls apps/api through its service fetch function and avoids seed data', () => {
  for (const [, filename, fetchFunction] of pageContracts.filter((contract) => typeof contract[2] === 'string')) {
    const pageSource = readPage(filename);
    assert.match(pageSource, new RegExp(fetchFunction));
    assert.match(pageSource, /apiBaseUrl/);
    assert.doesNotMatch(pageSource, /from ['"].*\/data\/.*Seed\.js['"]/i);
    assert.doesNotMatch(pageSource, /from ['"].*\/data\/.*seed\.js['"]/i);
  }
});

test('admin menu consolidates lead channel and LLM governance entries with requested labels', () => {
  assert.match(appSource, /label: '运行总览'/);
  assert.match(appSource, /label: '线索渠道'/);
  assert.match(appSource, /label: 'LLM大模型治理'/);
  assert.match(appSource, /label: '同步与AI审计'/);
  assert.match(appSource, /label: 'Agents运行看板'/);
  assert.match(appSource, /label: '客户指标与风控'/);
  assert.doesNotMatch(appSource, /label: '质量指标'/);
  assert.doesNotMatch(appSource, /label: '第二阶段'/);
  assert.doesNotMatch(appSource, /label: '第三阶段'/);
  assert.doesNotMatch(appSource, /label: '同步'/);

  for (const key of removedMenuKeys) {
    assert.doesNotMatch(appSource, new RegExp(`key: '${key}'`));
  }
});

test('combined admin pages compose the original real API page components', () => {
  for (const [, filename, componentNames] of pageContracts.filter((contract) => Array.isArray(contract[2]))) {
    const pageSource = readPage(filename);
    for (const componentName of componentNames) {
      assert.match(pageSource, new RegExp(`<${componentName}\\s*/>`));
      assert.match(pageSource, new RegExp(`import ${componentName} from './${componentName}\\.vue'`));
    }
  }
});

test('lead channels page no longer embeds the old overview page after runtime overview is split out', () => {
  const pageSource = readPage('LeadChannelsPage.vue');
  assert.doesNotMatch(pageSource, /<OverviewPage\s*\/>/);
  assert.doesNotMatch(pageSource, /import OverviewPage from '\.\/OverviewPage\.vue'/);
});

test('prompt governance page removes prompt version, validation failure summary, and draft operation sections from combined LLM page', () => {
  const pageSource = readPage('PromptGovernancePage.vue');
  assert.doesNotMatch(pageSource, /Prompt 版本/);
  assert.doesNotMatch(pageSource, /校验失败摘要/);
  assert.doesNotMatch(pageSource, /草稿校验与操作入口/);
});

test('llm governance page supports clickable prompt template switching and split prompt/schema workbench', () => {
  const pageSource = readPage('LlmGovernancePage.vue');
  assert.match(pageSource, /selectedTemplateId/);
  assert.match(pageSource, /@click="selectTemplate\(template\.id\)"/);
  assert.match(pageSource, /llm-workbench/);
  assert.match(pageSource, /输入 Prompt/);
  assert.match(pageSource, /输出 Schema/);
});

test('admin shared runtime defaults API calls to local apps/api instead of Vite HTML fallback', () => {
  assert.match(pageRuntimeSource, /http:\/\/localhost:8000/);
  assert.doesNotMatch(pageRuntimeSource, /VITE_API_BASE_URL\s*\|\|\s*''/);
});
