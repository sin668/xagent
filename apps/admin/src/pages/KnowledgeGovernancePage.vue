<template>
  <section id="knowledge-governance" class="admin-card knowledge-governance-card">
    <div class="card-head">
      <div><h3>Q&A 与邮件回复知识库</h3><span>Q&A、邮件模板、合规话术、车型说明和流程 SOP 统一进入 PostgreSQL + pgvector 治理</span></div>
      <span :class="['tag', knowledgeGovernance.summary.embeddingStatusClass]">embedding ready {{ knowledgeGovernance.summary.embeddingReadyRateText }}</span>
    </div>
    <p v-if="errorMessage" class="guardrail">{{ errorMessage }}</p>
    <p v-else-if="isLoading" class="guardrail">正在加载知识库治理真实 API...</p>
    <div class="knowledge-tabs">
      <span v-for="tab in knowledgeGovernance.tabs" :key="tab.label" class="knowledge-tab">{{ tab.label }}</span>
    </div>
    <div class="knowledge-summary">
      <article><strong>{{ knowledgeGovernance.summary.publishedItemCount }}</strong><span>published items</span></article>
      <article><strong>{{ knowledgeGovernance.summary.embeddingReadyCount }}</strong><span>embedding ready</span></article>
      <article><strong>{{ knowledgeGovernance.summary.autoReplyAllowedCount }}</strong><span>auto reply allowed</span></article>
      <article><strong>{{ knowledgeGovernance.summary.reviewDraftCount }}</strong><span>待审核草稿</span></article>
    </div>
    <div class="knowledge-governance-grid">
      <section>
        <div class="card-head compact-head"><h4>知识条目</h4><span>草稿 -> 审核 -> 发布 -> embedding -> active_for_retrieval</span></div>
        <table class="table">
          <thead><tr><th>标题</th><th>类型</th><th>语言</th><th>场景</th><th>工作流</th><th>向量</th><th>自动回复</th></tr></thead>
          <tbody>
            <tr v-for="item in knowledgeGovernance.items" :key="item.id">
              <td>{{ item.title }}</td><td>{{ item.contentTypeLabel }}</td><td>{{ item.language }}</td><td>{{ item.businessScene }}</td>
              <td><span :class="['tag', item.statusClass]">{{ item.workflowLabel }}</span></td>
              <td><span :class="['tag', item.embeddingStatusClass]">{{ item.embeddingStatusLabel }}</span></td>
              <td>{{ item.autoReplyLabel }}</td>
            </tr>
            <tr v-if="knowledgeGovernance.items.length === 0"><td colspan="7">暂无真实知识库数据</td></tr>
          </tbody>
        </table>
      </section>
      <section>
        <div class="card-head compact-head"><h4>治理操作入口</h4><span>{{ knowledgeGovernance.canPublish ? '知识管理员受控操作' : '权限不足已禁用' }}</span></div>
        <div class="knowledge-action-list">
          <article v-for="entry in knowledgeGovernance.actionEntrypoints" :key="entry.label">
            <strong>{{ entry.label }}</strong><span :class="['tag', entry.enabled ? 'blue' : 'amber']">{{ entry.enabled ? '可操作' : '禁用' }}</span>
          </article>
        </div>
        <p class="guardrail">{{ knowledgeGovernance.permissionNotice }}</p>
      </section>
    </div>
    <div class="knowledge-lower-grid">
      <section class="schema-preview"><div class="card-head compact-head"><h4>召回测试面板</h4><span>dry run，不触发邮件发送</span></div><pre>{{ ragTestText }}</pre></section>
      <section class="schema-preview"><div class="card-head compact-head"><h4>Embedding 失败与重试</h4><span>{{ knowledgeGovernance.summary.failedEmbeddingCount }} failed / {{ knowledgeGovernance.summary.totalRetryCount }} retries</span></div><pre>{{ embeddingFailuresText }}</pre></section>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';

import { buildKnowledgeGovernanceView, fetchKnowledgeGovernance } from '../services/knowledgeGovernance.js';
import { adminActorRole, apiBaseUrl, formatLoadError } from './pageRuntime.js';

const payload = ref(null);
const isLoading = ref(true);
const errorMessage = ref('');
const knowledgeGovernance = computed(() => buildKnowledgeGovernanceView({
  items: payload.value?.items || {},
  embeddingMetrics: payload.value?.embeddingMetrics || {},
  actorRole: payload.value?.actorRole || adminActorRole,
}));
const ragTestText = computed(() => JSON.stringify({
  query: knowledgeGovernance.value.ragTestPanel.defaultQuery,
  filters: knowledgeGovernance.value.ragTestPanel.defaultFilters,
  result_policy: 'dry_run_only_triggered_send_false',
}, null, 2));
const embeddingFailuresText = computed(() => {
  if (knowledgeGovernance.value.embeddingFailures.length === 0) return '暂无 embedding 失败案例。';
  return knowledgeGovernance.value.embeddingFailures.map((item) => `${item.knowledgeTitle} / ${item.embeddingModel} / retry=${item.retryCount} / ${item.errorMessage}`).join('\n');
});

onMounted(async () => {
  try {
    payload.value = await fetchKnowledgeGovernance({ baseUrl: apiBaseUrl, actorRole: adminActorRole });
  } catch (error) {
    errorMessage.value = formatLoadError('无法加载知识库治理真实 API', error);
  } finally {
    isLoading.value = false;
  }
});
</script>
