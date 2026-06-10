<template>
  <section id="phase2" class="admin-card phase2-card">
    <div class="card-head">
      <div>
        <h3>第二阶段小范围运行看板</h3>
        <span>Source Discovery -> 来源审核 -> LEAD_EXTRACTION -> staging/core</span>
      </div>
      <span :class="['tag', statusClass]">{{ statusText }}</span>
    </div>

    <p v-if="errorMessage" class="guardrail">{{ errorMessage }}</p>
    <p v-else-if="isLoading" class="guardrail">正在加载第二阶段真实 API 指标...</p>

    <div class="phase2-summary">
      <article><strong>{{ phase2.summary.sourceCandidateCount }}</strong><span>来源新增</span></article>
      <article><strong>{{ phase2.summary.extractableSourceCount }}</strong><span>可抽取来源</span></article>
      <article class="danger-metric"><strong>{{ phase2.summary.highReviewBacklogCount }}</strong><span>High 待审</span></article>
      <article><strong>{{ phase2.summary.llmCostText }}</strong><span>LLM 成本</span></article>
    </div>

    <div class="phase2-flow">
      <article v-for="node in phase2.taskFlow" :key="node.title" class="phase2-flow-node">
        <strong>{{ node.title }}</strong>
        <span>{{ node.metricText }}</span>
        <p>{{ node.description }}</p>
      </article>
    </div>

    <div class="phase2-split">
      <section>
        <div class="card-head compact-head"><h4>Agent Task Runs</h4><span>真实 API 审计事实</span></div>
        <table class="table">
          <thead><tr><th>Run</th><th>任务</th><th>模型</th><th>状态</th><th>输出</th><th>成本</th></tr></thead>
          <tbody>
            <tr v-for="run in phase2.llmTaskRuns" :key="run.runId">
              <td>{{ run.runId || '-' }}</td>
              <td>{{ run.taskType }}</td>
              <td>{{ run.provider }}</td>
              <td><span :class="['tag', run.statusClass]">{{ run.statusLabel }}</span></td>
              <td>{{ run.outputText }}</td>
              <td>{{ run.costText }}</td>
            </tr>
            <tr v-if="phase2.llmTaskRuns.length === 0"><td colspan="6">暂无真实 LLM 任务成本数据</td></tr>
          </tbody>
        </table>
      </section>
      <section>
        <div class="card-head compact-head"><h4>自动暂停阈值</h4><span>触发后停止自动任务</span></div>
        <div class="pause-list">
          <article v-for="threshold in pauseThresholds" :key="threshold.label">
            <div><strong>{{ threshold.label }}</strong><span>{{ threshold.text || `${threshold.current} / ${threshold.limit}` }}</span></div>
            <div class="progress"><span :class="threshold.className" :style="{ width: `${threshold.percent}%` }"></span></div>
          </article>
        </div>
      </section>
    </div>

    <div class="phase2-risk-list">
      <div class="card-head compact-head"><h4>High/Forbidden 风险事件</h4><span>{{ phase2.summary.highForbiddenRiskEventCount }} 个高风险事件</span></div>
      <article v-for="event in phase2.highForbiddenRiskEvents" :key="event.id" class="risk-row">
        <div><strong>{{ event.channel }}</strong><span>{{ event.eventType }} · {{ event.createdAt }}</span></div>
        <p><span :class="['tag', event.highlightClass]">{{ event.riskLabel }}</span> {{ event.blockReason }}</p>
      </article>
      <p v-if="phase2.highForbiddenRiskEvents.length === 0" class="empty-note">暂无 High/Forbidden 风险事件。</p>
    </div>
    <p class="guardrail">{{ phase2.guardrail }}</p>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';

import { buildPhase2DashboardView, fetchPhase2Dashboard } from '../services/phase2Dashboard.js';
import { apiBaseUrl, formatLoadError } from './pageRuntime.js';

const payload = ref(null);
const isLoading = ref(true);
const errorMessage = ref('');
const phase2 = computed(() => buildPhase2DashboardView(payload.value || {}));
const pauseThresholds = computed(() => Object.values(phase2.value.pauseThresholds));
const statusText = computed(() => {
  if (isLoading.value) return '加载中';
  if (errorMessage.value) return 'API 异常';
  return phase2.value.summary.highForbiddenRiskEventCount > 0 ? '需复核' : '运行中';
});
const statusClass = computed(() => {
  if (isLoading.value) return 'amber';
  if (errorMessage.value || phase2.value.summary.highForbiddenRiskEventCount > 0) return 'red';
  return 'green';
});

onMounted(async () => {
  try {
    payload.value = await fetchPhase2Dashboard({ baseUrl: apiBaseUrl });
  } catch (error) {
    errorMessage.value = formatLoadError('无法加载第二阶段真实 API 指标', error);
  } finally {
    isLoading.value = false;
  }
});
</script>
