<template>
  <section id="risk-config" class="admin-card risk-config-card">
    <div class="card-head">
      <h3>渠道风险配置</h3>
      <span>允许动作、禁止动作、政策来源和变更留痕</span>
    </div>
    <p v-if="errorMessage" class="guardrail">{{ errorMessage }}</p>
    <p v-else-if="isLoading" class="guardrail">正在加载渠道风险配置...</p>
    <table class="table">
      <thead>
        <tr>
          <th>渠道</th>
          <th>风险</th>
          <th>允许动作</th>
          <th>禁止动作</th>
          <th>政策来源</th>
          <th>变更人</th>
          <th>状态</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="rule in riskConfig.rules" :key="rule.channelName">
          <td>{{ rule.channelName }}</td>
          <td><span :class="['tag', riskClass(rule.riskLevel)]">{{ rule.riskLabel }}</span></td>
          <td>{{ rule.allowedActions }}</td>
          <td>{{ rule.forbiddenActions }}</td>
          <td class="source-cell">{{ rule.policySourceUrl }}</td>
          <td>{{ rule.updatedBy }}</td>
          <td>{{ rule.statusLabel }}</td>
        </tr>
        <tr v-if="!isLoading && riskConfig.rules.length === 0">
          <td colspan="7">暂无真实风险配置</td>
        </tr>
      </tbody>
    </table>
    <div class="blocked-reasons">
      <article v-for="rule in riskConfig.blockedRules" :key="`${rule.channelName}-blocked`">
        <strong>{{ rule.channelName }}</strong>
        <span>{{ rule.blockReason }}</span>
      </article>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';

import { buildChannelRiskConfigView, fetchChannelRiskRules } from '../services/channelRiskConfig.js';
import { apiBaseUrl, formatLoadError } from './pageRuntime.js';

const payload = ref(null);
const isLoading = ref(true);
const errorMessage = ref('');
const riskConfig = computed(() => buildChannelRiskConfigView(payload.value || {}));

function riskClass(riskLevel) {
  if (riskLevel === 'Low') return 'green';
  if (riskLevel === 'Medium') return 'amber';
  return 'red';
}

onMounted(async () => {
  try {
    payload.value = await fetchChannelRiskRules({ baseUrl: apiBaseUrl });
  } catch (error) {
    errorMessage.value = formatLoadError('无法加载渠道风险配置真实 API', error);
  } finally {
    isLoading.value = false;
  }
});
</script>
