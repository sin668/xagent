<template>
  <section id="sync-audit" class="admin-card sync-audit-card">
    <div class="card-head">
      <h3>飞书同步与 AI 审计</h3>
      <span>最近同步 {{ syncAudit.summary.latestSyncAt || '暂无' }}</span>
    </div>
    <p v-if="errorMessage" class="guardrail">{{ errorMessage }}</p>
    <p v-else-if="isLoading" class="guardrail">正在加载同步与 AI 审计真实数据...</p>
    <div class="sync-audit-grid">
      <div><strong>{{ syncAudit.summary.syncSuccessCount }}</strong><span>同步成功</span></div>
      <div><strong>{{ syncAudit.summary.syncFailureCount }}</strong><span>同步失败</span></div>
      <div><strong>{{ syncAudit.summary.aiTaskCount }}</strong><span>AI 审计日志</span></div>
      <div><strong>{{ syncAudit.summary.aiBlockedCount }}</strong><span>被阻断任务</span></div>
    </div>
    <div class="audit-columns">
      <section>
        <h4>同步日志</h4>
        <article v-for="item in syncAudit.syncLogs" :key="item.id" class="audit-row">
          <div><strong>{{ item.objectName }}</strong><span>{{ item.successCount }} 成功 / {{ item.failureCount }} 失败</span></div>
          <p>{{ item.errorSummary || item.statusLabel }}</p>
        </article>
      </section>
      <section>
        <h4>AI 执行审计</h4>
        <article v-for="item in syncAudit.aiAuditLogs" :key="item.id" class="audit-row">
          <div><strong>{{ item.taskType }}</strong><span>{{ item.modelName }} · {{ item.promptVersion }}</span></div>
          <p>{{ item.riskBlockReason || item.statusLabel }}</p>
        </article>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';

import { buildSyncAiAuditView, fetchSyncAiAuditDashboard } from '../services/syncAiAudit.js';
import { apiBaseUrl, formatLoadError } from './pageRuntime.js';

const payload = ref(null);
const isLoading = ref(true);
const errorMessage = ref('');
const syncAudit = computed(() => buildSyncAiAuditView(payload.value || {}));

onMounted(async () => {
  try {
    payload.value = await fetchSyncAiAuditDashboard({ baseUrl: apiBaseUrl });
  } catch (error) {
    errorMessage.value = formatLoadError('无法加载同步与 AI 审计真实 API', error);
  } finally {
    isLoading.value = false;
  }
});
</script>
