<template>
  <section id="phase5-integration" class="admin-card phase5-integration-card">
    <div class="card-head">
      <div><h3>第五阶段真实 API 联调</h3><span>Prompt、知识库和邮件审核三条后台链路必须接真实 API，不允许以 seed 静态数据作为验收依据</span></div>
      <span :class="['tag', phase5Integration.statusClass]">{{ phase5Integration.statusLabel }}</span>
    </div>
    <p v-if="errorMessage" class="guardrail">{{ errorMessage }}</p>
    <p v-else-if="isLoading" class="guardrail">正在检查第五阶段真实 API 联调状态...</p>
    <div class="integration-grid">
      <article v-for="record in phase5Integration.integrationRecords" :key="record.key">
        <div><strong>{{ record.name }}</strong><span>{{ record.url }}</span></div>
        <span :class="['tag', record.statusClass]">{{ record.statusLabel }}</span>
        <em>{{ record.itemCount }} 条真实记录 / HTTP {{ record.status }}</em>
      </article>
    </div>
    <p v-if="phase5Integration.firstError" class="guardrail">{{ phase5Integration.firstError.title }}：{{ phase5Integration.firstError.message }}</p>
    <p class="guardrail">{{ phase5Integration.permission.notice }}</p>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';

import { buildPhase5AdminIntegrationView, fetchPhase5AdminIntegration } from '../services/adminRealApiIntegration.js';
import { adminActorRole, apiBaseUrl, formatLoadError } from './pageRuntime.js';

const payload = ref(null);
const isLoading = ref(true);
const errorMessage = ref('');
const phase5Integration = computed(() => buildPhase5AdminIntegrationView({
  ...(payload.value || {}),
  actorRole: payload.value?.actorRole || adminActorRole,
  seedFallbackAllowed: false,
}));

onMounted(async () => {
  try {
    payload.value = await fetchPhase5AdminIntegration({ baseUrl: apiBaseUrl, actorRole: adminActorRole });
  } catch (error) {
    errorMessage.value = formatLoadError('无法加载第五阶段真实 API 联调记录', error);
  } finally {
    isLoading.value = false;
  }
});
</script>
