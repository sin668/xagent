<template>
  <section id="risk-audit" class="admin-card risk-card">
    <div class="card-head">
      <h3>风险事件与阻断任务</h3>
      <span>管理者必须可见阻断原因</span>
    </div>
    <p v-if="errorMessage" class="guardrail">{{ errorMessage }}</p>
    <p v-else-if="isLoading" class="guardrail">正在加载风险事件真实数据...</p>
    <div class="risk-list">
      <article v-for="event in overview.riskEvents" :key="event.id" class="risk-row">
        <div>
          <strong>{{ event.taskType }}</strong>
          <span>{{ event.sourceUrl || '无来源链接' }}</span>
        </div>
        <p>{{ event.riskBlockReason || '未填写阻断原因' }}</p>
      </article>
      <p v-if="!isLoading && overview.riskEvents.length === 0" class="empty-note">暂无真实风险事件。</p>
    </div>
    <p class="guardrail">High/Forbidden 渠道和勿扰客户不得进入自动化触达；C 级线索报价或合同前必须合规复核。</p>
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
    errorMessage.value = formatLoadError('无法加载风险事件真实 API', error);
  } finally {
    isLoading.value = false;
  }
});
</script>
