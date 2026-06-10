<template>
  <section id="channels" class="admin-card channel-card">
    <div class="card-head">
      <h3>渠道产出</h3>
      <span>按 B/C 级线索排序 · apps/api</span>
    </div>
    <p v-if="errorMessage" class="guardrail">{{ errorMessage }}</p>
    <p v-else-if="isLoading" class="guardrail">正在加载渠道真实数据...</p>
    <table class="table">
      <thead>
        <tr>
          <th>渠道</th>
          <th>风险</th>
          <th>状态</th>
          <th>候选</th>
          <th>B/C</th>
          <th>无效率</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="channel in dashboard.channels" :key="channel.channelName">
          <td>{{ channel.displayName }}</td>
          <td><span :class="['tag', riskClass(channel.riskLevel)]">{{ channel.riskLabel }}</span></td>
          <td>{{ channel.statusLabel }}</td>
          <td>{{ channel.candidateCount }}</td>
          <td>{{ channel.bcText }}</td>
          <td>{{ channel.invalidRateText }}</td>
        </tr>
        <tr v-if="!isLoading && dashboard.channels.length === 0">
          <td colspan="6">暂无真实渠道数据</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';

import { buildChannelDashboardView, fetchChannelLeadDashboard } from '../services/channelDashboard.js';
import { apiBaseUrl, formatLoadError } from './pageRuntime.js';

const payload = ref(null);
const isLoading = ref(true);
const errorMessage = ref('');
const dashboard = computed(() => buildChannelDashboardView(payload.value || {}));

function riskClass(riskLevel) {
  if (riskLevel === 'Low') return 'green';
  if (riskLevel === 'Medium') return 'amber';
  return 'red';
}

onMounted(async () => {
  try {
    payload.value = await fetchChannelLeadDashboard({ baseUrl: apiBaseUrl });
  } catch (error) {
    errorMessage.value = formatLoadError('无法加载渠道产出真实 API', error);
  } finally {
    isLoading.value = false;
  }
});
</script>
