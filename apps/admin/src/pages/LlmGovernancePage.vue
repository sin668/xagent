<template>
  <section id="llm-governance" class="admin-card llm-card">
    <div class="card-head">
      <div><h3>LLM Provider 与 Prompt Schema</h3><span>Provider 健康、prompt/schema 版本、fallback 边界和只读治理</span></div>
      <span :class="['tag', statusClass]">{{ statusText }}</span>
    </div>
    <p v-if="errorMessage" class="guardrail">{{ errorMessage }}</p>
    <p v-else-if="isLoading" class="guardrail">正在加载 LLM 治理真实 API...</p>
    <div class="provider-grid">
      <article class="provider-card"><strong>{{ llmGovernance.providerHealth.providerName }}</strong><small>{{ llmGovernance.providerHealth.modelSummary || '暂无模型配置' }}</small><span :class="['tag', llmGovernance.providerHealth.statusClass]">{{ llmGovernance.providerHealth.statusLabel }}</span></article>
      <article class="provider-card"><strong>Base URL</strong><small>仅展示配置状态，不展示具体密钥或敏感配置</small><span :class="['tag', llmGovernance.providerHealth.baseUrlConfigured ? 'green' : 'amber']">{{ llmGovernance.providerHealth.baseUrlConfigured ? 'configured' : 'missing' }}</span></article>
      <article class="provider-card"><strong>API Key</strong><small>页面只显示是否已配置，禁止展示 API key 原文</small><span :class="['tag', llmGovernance.providerHealth.apiKeyConfigured ? 'green' : 'amber']">{{ llmGovernance.providerHealth.apiKeyConfigured ? 'configured' : 'missing' }}</span></article>
      <article class="provider-card"><strong>Read Only</strong><small>{{ llmGovernance.readOnlyNotice }}</small><span class="tag blue">governance</span></article>
    </div>
    <div class="llm-split">
      <section>
        <div class="card-head compact-head"><h4>Prompt Template 版本</h4><span>仅管理员维护</span></div>
        <table class="table">
          <thead><tr><th>名称</th><th>任务</th><th>Provider</th><th>版本</th><th>状态</th><th>Schema</th><th>默认</th></tr></thead>
          <tbody>
            <tr
              v-for="template in llmGovernance.promptTemplates"
              :key="template.id"
              :class="['clickable-row', selectedTemplateId === template.id ? 'row-active' : '']"
              @click="selectTemplate(template.id)"
            >
              <td>{{ template.name }}</td><td>{{ template.taskType }}</td><td>{{ template.provider }} / {{ template.model }}</td><td>{{ template.version }}</td>
              <td><span :class="['tag', template.statusClass]">{{ template.statusLabel }}</span></td><td>{{ template.schemaSummary }}</td><td>{{ template.defaultLabel }}</td>
            </tr>
            <tr v-if="llmGovernance.promptTemplates.length === 0"><td colspan="7">暂无真实 prompt template 数据</td></tr>
          </tbody>
        </table>
      </section>
      <section>
        <div class="card-head compact-head"><h4>Fallback 边界</h4><span>合规失败不得 fallback</span></div>
        <div class="fallback-list"><article v-for="item in llmGovernance.fallbackBoundaries" :key="item.condition"><strong>{{ item.condition }}</strong><span :class="['tag', item.className]">{{ item.decisionLabel }}</span></article></div>
      </section>
    </div>
    <section class="llm-workbench">
      <section class="schema-preview">
        <div class="card-head compact-head"><h4>{{ llmGovernance.promptWorkbench.title }} 输入 Prompt</h4><span>{{ llmGovernance.promptWorkbench.version || '无版本' }}</span></div>
        <pre>{{ llmGovernance.promptWorkbench.promptInputText }}</pre>
      </section>
      <section class="schema-preview">
        <div class="card-head compact-head"><h4>{{ llmGovernance.promptWorkbench.title }} 输出 Schema</h4><span>{{ llmGovernance.promptWorkbench.version || '无版本' }}</span></div>
        <pre>{{ llmGovernance.promptWorkbench.schemaOutputText }}</pre>
      </section>
    </section>
    <p class="guardrail">{{ llmGovernance.readOnlyNotice }} 页面不展示 API key、secret 或完整敏感连接配置。</p>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';

import { buildLlmGovernanceView, fetchLlmGovernance } from '../services/llmGovernance.js';
import { apiBaseUrl, formatLoadError } from './pageRuntime.js';

const payload = ref(null);
const isLoading = ref(true);
const errorMessage = ref('');
const selectedTemplateId = ref('');
const llmGovernance = computed(() => buildLlmGovernanceView({
  ...(payload.value || {}),
  selectedTemplateId: selectedTemplateId.value,
}));
const statusText = computed(() => {
  if (isLoading.value) return '加载中';
  if (errorMessage.value) return 'API 异常';
  return llmGovernance.value.providerHealth.statusLabel;
});
const statusClass = computed(() => {
  if (isLoading.value) return 'amber';
  if (errorMessage.value) return 'red';
  return llmGovernance.value.providerHealth.statusClass;
});

onMounted(async () => {
  try {
    payload.value = await fetchLlmGovernance({ baseUrl: apiBaseUrl });
    selectedTemplateId.value = llmGovernance.value.promptWorkbench.selectedTemplateId;
  } catch (error) {
    errorMessage.value = formatLoadError('无法加载 LLM/Prompt 治理真实 API', error);
  } finally {
    isLoading.value = false;
  }
});

function selectTemplate(templateId) {
  selectedTemplateId.value = templateId;
}
</script>
