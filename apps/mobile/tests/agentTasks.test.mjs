import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  createAgentTasksService,
  mapAgentTaskRun,
} from '../src/services/agentTasks.js';

function createMockClient() {
  const calls = [];
  return {
    calls,
    client: {
      async get(endpoint) {
        calls.push({ method: 'GET', endpoint });
        return {
          id: 'task-1',
          task_type: 'SOURCE_DISCOVERY',
          status: 'succeeded',
          trigger_source: 'manual_api',
          input_json: { country: 'Russia' },
          output_summary_json: { created_count: 8, blocked_count: 1 },
          llm_provider: 'deepseek',
          llm_model: 'deepseek-chat',
          prompt_version: 'v1.0',
          created_at: '2026-06-02T00:00:00Z',
          updated_at: '2026-06-02T00:05:00Z',
        };
      },
      async post(endpoint, body) {
        calls.push({ method: 'POST', endpoint, body });
        return {
          agent_task_run_id: 'task-1',
          status: 'succeeded',
          created_count: 8,
          blocked_count: 1,
          duplicate_count: 2,
        };
      },
    },
  };
}

test('agent task service starts SOURCE_DISCOVERY with backend schema fields', async () => {
  const mock = createMockClient();
  const service = createAgentTasksService({ client: mock.client });

  const result = await service.startSourceDiscovery({
    country: 'Russia',
    cities: ['Moscow', 'Vladivostok'],
    channelStrategy: 'official_website_public_directory_search_engine',
    keywords: ['автосалон', 'импорт авто'],
    limit: 20,
  });

  assert.equal(mock.calls[0].method, 'POST');
  assert.equal(mock.calls[0].endpoint, '/agent-tasks/source-discovery/run');
  assert.deepEqual(mock.calls[0].body, {
    country: 'Russia',
    cities: ['Moscow', 'Vladivostok'],
    channel_strategy: 'official_website_public_directory_search_engine',
    keywords: ['автосалон', 'импорт авто'],
    limit: 20,
  });
  assert.equal(result.agentTaskRunId, 'task-1');
  assert.equal(result.createdCount, 8);
  assert.equal(result.blockedCount, 1);
  assert.equal(result.duplicateCount, 2);
});

test('agent task service gets task run status by id', async () => {
  const mock = createMockClient();
  const service = createAgentTasksService({ client: mock.client });

  const task = await service.getAgentTaskRun('task-1');

  assert.equal(mock.calls[0].method, 'GET');
  assert.equal(mock.calls[0].endpoint, '/agent-task-runs/task-1');
  assert.equal(task.id, 'task-1');
  assert.equal(task.taskType, 'SOURCE_DISCOVERY');
  assert.equal(task.status, 'succeeded');
  assert.equal(task.outputSummary.createdCount, 8);
  assert.equal(task.promptVersion, 'v1.0');
});

test('agent task mapper supports source discovery run response and task run detail response', () => {
  const run = mapAgentTaskRun({
    agent_task_run_id: 'task-1',
    status: 'running',
    created_count: 0,
    blocked_count: 0,
    duplicate_count: 0,
  });
  const detail = mapAgentTaskRun({
    id: 'task-2',
    task_type: 'SOURCE_DISCOVERY',
    status: 'manual_review_required',
    output_summary_json: { error: { type: 'schema_validation_error' } },
  });

  assert.equal(run.agentTaskRunId, 'task-1');
  assert.equal(run.status, 'running');
  assert.equal(detail.id, 'task-2');
  assert.equal(detail.taskType, 'SOURCE_DISCOVERY');
  assert.equal(detail.outputSummary.error.type, 'schema_validation_error');
});

