import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

import { createAgentTasksService } from '../src/services/agentTasks.js';

const pagePath = new URL('../src/pages/agent-run/index.vue', import.meta.url);
const srcPagesJsonPath = new URL('../src/pages.json', import.meta.url);
const rootPagesJsonPath = new URL('../pages.json', import.meta.url);

function readText(url) {
  return readFileSync(url, 'utf8');
}

test('Agent 手动调用页面注册到两份 uni-app 页面配置', () => {
  const srcPages = JSON.parse(readText(srcPagesJsonPath));
  const rootPages = JSON.parse(readText(rootPagesJsonPath));

  assert.ok(srcPages.pages.some((page) => page.path === 'pages/agent-run/index'));
  assert.ok(rootPages.pages.some((page) => page.path === 'src/pages/agent-run/index'));
});

test('Agent 手动调用页面支持 SOURCE_DISCOVERY 和 LEAD_EXTRACTION 表单字段', () => {
  const page = readText(pagePath);

  for (const token of [
    'SOURCE_DISCOVERY',
    'LEAD_EXTRACTION',
    'country',
    'citiesText',
    'channelStrategy',
    'promptTemplateKey',
    'limit',
  ]) {
    assert.match(page, new RegExp(token));
  }
});

test('Agent 手动调用页面通过 agentTasksService 启动任务并查询状态', () => {
  const page = readText(pagePath);

  assert.match(page, /agentTasksService/);
  assert.match(page, /\.startSourceDiscovery\(/);
  assert.match(page, /\.startLeadExtraction\(/);
  assert.match(page, /\.getAgentTaskRun\(/);
  assert.match(page, /agentTaskRunId/);
  assert.match(page, /failureReason/);
});

test('Agent 手动调用页面展示安全边界且不包含自动触达动作', () => {
  const page = readText(pagePath);

  for (const text of ['不触达', '自动私信', '登录采集', 'High 抽取', 'Forbidden']) {
    assert.match(page, new RegExp(text));
  }
  assert.doesNotMatch(page, /sendMessage|addFriend|自动加好友|批量触达/i);
});

test('Agent service 支持 LEAD_EXTRACTION 启动契约', async () => {
  const calls = [];
  const service = createAgentTasksService({
    client: {
      async post(endpoint, body) {
        calls.push({ endpoint, body });
        return {
          agent_task_run_id: 'task-lead-1',
          status: 'running',
          created_count: 0,
          blocked_count: 0,
          duplicate_count: 0,
        };
      },
    },
  });

  const result = await service.startLeadExtraction({
    country: 'Russia',
    cities: ['Moscow'],
    channelStrategy: 'approved_sources_only',
    promptTemplateKey: 'lead_extraction_default',
    limit: 30,
  });

  assert.equal(calls[0].endpoint, '/agent-tasks/lead-extraction/from-sources/run');
  assert.deepEqual(calls[0].body, {
    country: 'Russia',
    city: 'Moscow',
    limit: 30,
  });
  assert.equal(result.agentTaskRunId, 'task-lead-1');
  assert.equal(result.status, 'running');
});
