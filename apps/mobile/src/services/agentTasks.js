import { apiClient } from './apiClient.js';

function compactPayload(payload = {}) {
  return Object.fromEntries(
    Object.entries(payload).filter(([, value]) => value !== undefined && value !== null && value !== ''),
  );
}

function mapOutputSummary(summary = {}) {
  return {
    createdCount: Number(summary.created_count ?? summary.createdCount ?? 0),
    updatedCount: Number(summary.updated_count ?? summary.updatedCount ?? 0),
    blockedCount: Number(summary.blocked_count ?? summary.blockedCount ?? 0),
    duplicateCount: Number(summary.duplicate_count ?? summary.duplicateCount ?? 0),
    error: summary.error || null,
  };
}

export function mapAgentTaskRun(task = {}) {
  const outputSummary = mapOutputSummary(task.output_summary_json || task.outputSummary || task);
  return {
    id: task.id || task.agent_task_run_id || task.agentTaskRunId,
    agentTaskRunId: task.agent_task_run_id || task.agentTaskRunId || task.id,
    taskType: task.task_type || task.taskType || 'SOURCE_DISCOVERY',
    status: task.status || 'pending',
    triggerSource: task.trigger_source || task.triggerSource || '',
    inputJson: task.input_json || task.inputJson || null,
    outputSummary,
    createdCount: Number(task.created_count ?? task.createdCount ?? outputSummary.createdCount),
    blockedCount: Number(task.blocked_count ?? task.blockedCount ?? outputSummary.blockedCount),
    duplicateCount: Number(task.duplicate_count ?? task.duplicateCount ?? outputSummary.duplicateCount),
    llmProvider: task.llm_provider || task.llmProvider || '',
    llmModel: task.llm_model || task.llmModel || '',
    promptVersion: task.prompt_version || task.promptVersion || '',
    errorMessage: task.error_message || task.errorMessage || '',
    createdAt: task.created_at || task.createdAt || '',
    updatedAt: task.updated_at || task.updatedAt || '',
  };
}

export function createAgentTasksService({ client = apiClient } = {}) {
  return {
    async startSourceDiscovery({ country, cities = [], channelStrategy, keywords = [], promptTemplateKey, limit = 20 }) {
      const payload = await client.post('/agent-tasks/source-discovery/run', compactPayload({
        country,
        cities,
        channel_strategy: channelStrategy,
        keywords,
        prompt_template_key: promptTemplateKey,
        limit,
      }));
      return mapAgentTaskRun(payload);
    },

    async startLeadExtraction({ country, cities = [], channelStrategy, promptTemplateKey, limit = 20 }) {
      const payload = await client.post('/agent-tasks/lead-extraction/from-sources/run', compactPayload({
        country,
        city: cities[0],
        limit,
      }));
      return mapAgentTaskRun(payload);
    },

    async getAgentTaskRun(taskRunId) {
      const payload = await client.get(`/agent-task-runs/${encodeURIComponent(taskRunId)}`);
      return mapAgentTaskRun(payload);
    },
  };
}

export const agentTasksService = createAgentTasksService();
