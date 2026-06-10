<template>
  <section id="prompt-governance" class="admin-card prompt-governance-card">
    <div class="card-head">
      <div><h3>Prompt 全量入库与版本治理</h3><span>运行时读取数据库 active default；草稿校验、发布和回滚全审计</span></div>
      <span :class="['tag', promptGovernance.summary.coverageStatusClass]">覆盖率 {{ promptGovernance.summary.coverageRateText }}</span>
    </div>
    <p v-if="errorMessage" class="guardrail">{{ errorMessage }}</p>
    <p v-else-if="isLoading" class="guardrail">正在加载 Prompt 治理真实 API...</p>
    <div class="prompt-summary">
      <article><strong>{{ promptGovernance.summary.importedPromptCount }}</strong><span>已入库 Prompt</span></article>
      <article><strong>{{ promptGovernance.summary.activeDefaultCount }}</strong><span>active default</span></article>
      <article><strong>{{ promptGovernance.summary.draftValidationPendingCount }}</strong><span>草稿待校验</span></article>
      <article><strong>{{ promptGovernance.summary.schemaErrorCount }}</strong><span>schema error</span></article>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';

import { buildPromptGovernanceView, fetchPromptGovernance } from '../services/llmGovernance.js';
import { adminActorRole, apiBaseUrl, formatLoadError } from './pageRuntime.js';

const payload = ref(null);
const isLoading = ref(true);
const errorMessage = ref('');
const promptGovernance = computed(() => buildPromptGovernanceView({
  templates: payload.value?.templates || {},
  actorRole: payload.value?.actorRole || adminActorRole,
}));

onMounted(async () => {
  try {
    payload.value = await fetchPromptGovernance({ baseUrl: apiBaseUrl, actorRole: adminActorRole });
  } catch (error) {
    errorMessage.value = formatLoadError('无法加载 Prompt 入库治理真实 API', error);
  } finally {
    isLoading.value = false;
  }
});
</script>
