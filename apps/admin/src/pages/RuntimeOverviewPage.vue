<template>
  <section id="runtime-overview" class="admin-page runtime-overview-page">
    <header class="admin-top runtime-hero">
      <div>
        <h2>{{ runtimeOverview.hero.title }}</h2>
        <p>{{ runtimeOverview.hero.subtitle }}</p>
      </div>
      <span :class="['tag', runtimeOverview.hero.statusClass]">{{ runtimeOverview.hero.statusText }}</span>
    </header>

    <p v-if="errorMessage" class="guardrail">{{ errorMessage }}</p>
    <p v-else-if="isLoading" class="guardrail">正在从 apps/api 加载运行总览真实 API...</p>

    <section class="admin-grid-cards runtime-summary-cards">
      <article v-for="card in runtimeOverview.summaryCards" :key="card.key" class="admin-card runtime-summary-card">
        <strong :class="card.accentClass">{{ card.value }}</strong>
        <span>{{ card.label }}</span>
      </article>
    </section>

    <section class="runtime-split">
      <section class="admin-card">
        <div class="card-head">
          <h3>渠道产出</h3>
          <span class="tag blue">真实 API</span>
        </div>
        <table class="table">
          <thead><tr><th>渠道组</th><th>风险</th><th>候选</th><th>core</th><th>状态</th></tr></thead>
          <tbody>
            <tr v-for="channel in runtimeOverview.channels" :key="channel.key">
              <td>{{ channel.displayName }}</td>
              <td><span :class="['tag', channel.riskClass]">{{ channel.riskLevel }}</span></td>
              <td>{{ channel.candidateCount }}</td>
              <td>{{ channel.coreCount }}</td>
              <td>{{ channel.statusText }}</td>
            </tr>
            <tr v-if="runtimeOverview.channels.length === 0"><td colspan="5">暂无真实渠道产出数据</td></tr>
          </tbody>
        </table>
      </section>

      <section class="admin-card">
        <div class="card-head">
          <h3>今日漏斗</h3>
          <span class="tag green">实时聚合</span>
        </div>
        <div class="runtime-funnel">
          <article v-for="item in runtimeOverview.funnel" :key="item.key" class="runtime-funnel-row">
            <div class="runtime-funnel-head">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
            <div class="runtime-progress">
              <span :class="['runtime-progress-fill', item.barClass]" :style="{ width: `${item.width}%` }" />
            </div>
          </article>
        </div>
      </section>
    </section>

    <section class="runtime-insights">
      <article v-for="insight in runtimeOverview.insights" :key="insight.key" class="admin-card runtime-insight-card">
        <h3>{{ insight.title }}</h3>
        <p>{{ insight.body }}</p>
      </article>
    </section>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';

import { buildRuntimeOverviewView, fetchRuntimeOverview } from '../services/runtimeOverview.js';
import { apiBaseUrl, formatLoadError } from './pageRuntime.js';

const payload = ref(null);
const isLoading = ref(true);
const errorMessage = ref('');
const runtimeOverview = computed(() => buildRuntimeOverviewView(payload.value || {}));

onMounted(async () => {
  try {
    payload.value = await fetchRuntimeOverview({ baseUrl: apiBaseUrl });
  } catch (error) {
    errorMessage.value = formatLoadError('无法加载运行总览真实 API', error);
  } finally {
    isLoading.value = false;
  }
});
</script>
