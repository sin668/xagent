<template>
  <section id="queues" class="admin-card queue-card">
    <div class="card-head">
      <h3>今日队列</h3>
      <span>{{ overview.queueSummaryText }}</span>
    </div>
    <p v-if="errorMessage" class="guardrail">{{ errorMessage }}</p>
    <p v-else-if="isLoading" class="guardrail">正在加载团队队列真实数据...</p>
    <div class="queue-grid">
      <article v-for="queue in queues" :key="queue.key" class="queue-column">
        <strong>{{ queue.count }}</strong>
        <span>{{ queue.label }}</span>
        <p v-for="item in queue.items" :key="`${queue.key}-${item.customerId}`">
          {{ item.customerName }} · {{ item.grade }} · {{ item.owner }}
        </p>
      </article>
    </div>
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
const queues = computed(() => [
  { key: 'operations', label: '运营待复核', ...overview.value.teamQueues.operations },
  { key: 'customerService', label: '客服待跟进', ...overview.value.teamQueues.customerService },
  { key: 'sales', label: '销售待承接', ...overview.value.teamQueues.sales },
]);

onMounted(async () => {
  try {
    payload.value = await fetchAdminOverview({ baseUrl: apiBaseUrl });
  } catch (error) {
    errorMessage.value = formatLoadError('无法加载今日队列真实 API', error);
  } finally {
    isLoading.value = false;
  }
});
</script>
