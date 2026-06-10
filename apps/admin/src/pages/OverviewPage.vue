<template>
  <section id="overview" class="admin-page">
    <header class="admin-top">
      <div>
        <h2>后台总览</h2>
        <p>候选线索、团队队列、SLA 风险与阻断任务集中看板</p>
      </div>
      <span class="tag green">真实 API</span>
    </header>

    <p v-if="errorMessage" class="guardrail">{{ errorMessage }}</p>
    <p v-else-if="isLoading" class="guardrail">正在从 apps/api 加载后台总览...</p>

    <section class="admin-grid-cards">
      <article class="admin-card">
        <strong>{{ overview.summary.candidateCount }}</strong>
        <span>候选线索</span>
      </article>
      <article class="admin-card">
        <strong>{{ overview.summary.bcGradeCount }}</strong>
        <span>B/C 级线索</span>
      </article>
      <article class="admin-card">
        <strong>{{ overview.summary.responseRateText }}</strong>
        <span>回复率</span>
      </article>
      <article class="admin-card">
        <strong>{{ overview.summary.slaRiskCount }}</strong>
        <span>SLA 风险</span>
      </article>
    </section>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';

import { buildAdminOverviewView, fetchAdminOverview } from '../services/adminOverview.js';
import { apiBaseUrl, formatLoadError } from './pageRuntime.js';

const payload = ref(null);
const isLoading = ref(true);
const errorMessage = ref('');
const overview = computed(() => buildAdminOverviewView(payload.value || {}));

onMounted(async () => {
  try {
    payload.value = await fetchAdminOverview({ baseUrl: apiBaseUrl });
  } catch (error) {
    errorMessage.value = formatLoadError('无法加载后台总览真实 API', error);
  } finally {
    isLoading.value = false;
  }
});
</script>
