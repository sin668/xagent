<template>
  <section id="email-quality" class="admin-card email-quality-card">
    <div class="card-head">
      <div><h3>第五阶段 Go/No-Go 质量看板</h3><span>同时观察 Prompt、embedding、Agent、风险和业务结果；任一硬风险触发即暂停自动发送</span></div>
      <span :class="['tag', emailQualityDashboard.goNoGo.statusClass]">{{ emailQualityDashboard.goNoGo.statusLabel }}</span>
    </div>
    <p v-if="errorMessage" class="guardrail">{{ errorMessage }}</p>
    <p v-else-if="isLoading" class="guardrail">正在加载质量指标真实 API...</p>
    <div class="email-quality-summary">
      <article><strong>{{ emailQualityDashboard.summary.promptCoverageText }}</strong><span>Prompt 入库覆盖</span></article>
      <article><strong>{{ emailQualityDashboard.summary.embeddingReadyText }}</strong><span>embedding ready</span></article>
      <article><strong>{{ emailQualityDashboard.summary.aiGenerationSuccessText }}</strong><span>AI 生成成功</span></article>
      <article><strong>{{ emailQualityDashboard.summary.manualAdoptionText }}</strong><span>人工采纳率</span></article>
    </div>
    <div class="email-quality-grid">
      <section>
        <div class="card-head compact-head"><h4>邮件业务指标</h4><span>发送成功与退信来自真实邮件发送尝试</span></div>
        <div class="quality-tile-grid">
          <article><strong>{{ emailQualityDashboard.summary.autoSendSuccessText }}</strong><span>自动发送成功率</span></article>
          <article><strong>{{ emailQualityDashboard.summary.bounceRateText }}</strong><span>退信率</span></article>
          <article><strong>{{ emailQualityDashboard.riskGate.dncBlockedCount }}</strong><span>DNC 阻断</span></article>
          <article><strong>{{ emailQualityDashboard.riskGate.deGradeBlockedCount }}</strong><span>D/E 阻断</span></article>
        </div>
      </section>
      <section>
        <div class="card-head compact-head"><h4>硬风险门禁</h4><span :class="['tag', emailQualityDashboard.riskGate.statusClass]">{{ emailQualityDashboard.riskGate.statusLabel }}</span></div>
        <div class="quality-risk-list">
          <article><strong>风险事件</strong><span>{{ emailQualityDashboard.riskGate.riskEventCount }}</span></article>
          <article><strong>退信数量</strong><span>{{ emailQualityDashboard.riskGate.bounceCount }}</span></article>
          <article><strong>Go/No-Go 原因</strong><span>{{ reasonsText }}</span></article>
        </div>
      </section>
    </div>
    <section class="quality-flow-card">
      <div class="card-head compact-head"><h4>Go / 重跑 / 暂停判断</h4><span :class="['tag', emailQualityDashboard.goNoGo.statusClass]">{{ emailQualityDashboard.goNoGo.statusLabel }}</span></div>
      <div class="quality-flow-board"><article v-for="node in emailQualityDashboard.flowNodes" :key="node.title"><strong>{{ node.title }}</strong><span :class="['tag', node.className]">{{ node.metricText }}</span></article></div>
    </section>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';

import { buildEmailQualityDashboardView, fetchEmailQualityDashboard } from '../services/emailQualityDashboard.js';
import { apiBaseUrl, formatLoadError } from './pageRuntime.js';

const payload = ref(null);
const isLoading = ref(true);
const errorMessage = ref('');
const emailQualityDashboard = computed(() => buildEmailQualityDashboardView(payload.value || {}));
const reasonsText = computed(() => {
  const reasons = emailQualityDashboard.value.goNoGo.reasons;
  return reasons.length > 0 ? reasons.join(' / ') : '暂无暂停或重跑原因';
});

onMounted(async () => {
  try {
    payload.value = await fetchEmailQualityDashboard({ baseUrl: apiBaseUrl });
  } catch (error) {
    errorMessage.value = formatLoadError('无法加载第五阶段质量指标真实 API', error);
  } finally {
    isLoading.value = false;
  }
});
</script>
