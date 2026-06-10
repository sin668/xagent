<template>
  <div class="admin-shell">
    <aside class="sidebar">
      <h1>XAgent CRM</h1>
      <nav class="side-nav">
        <a
          v-for="item in menuItems"
          :key="item.key"
          :class="{ active: activePageKey === item.key }"
          :href="`#${item.key}`"
          @click="selectPage(item.key)"
        >
          {{ item.label }}
        </a>
      </nav>
    </aside>
    <main class="admin-main">
      <component :is="activePage.component" />
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

import EmailReplyReviewPage from './pages/EmailReplyReviewPage.vue';
import KnowledgeGovernancePage from './pages/KnowledgeGovernancePage.vue';
import LeadChannelsPage from './pages/LeadChannelsPage.vue';
import LlmModelGovernancePage from './pages/LlmModelGovernancePage.vue';
import Phase2Page from './pages/Phase2Page.vue';
import Phase3Page from './pages/Phase3Page.vue';
import Phase5IntegrationPage from './pages/Phase5IntegrationPage.vue';
import RuntimeOverviewPage from './pages/RuntimeOverviewPage.vue';
import SyncAuditPage from './pages/SyncAuditPage.vue';

const menuItems = [
  { key: 'runtime-overview', label: '运行总览', component: RuntimeOverviewPage },
  { key: 'lead-channels', label: '线索渠道', component: LeadChannelsPage },
  { key: 'sync-audit', label: '同步与AI审计', component: SyncAuditPage },
  { key: 'phase2', label: 'Agents运行看板', component: Phase2Page },
  { key: 'phase3', label: '客户指标与风控', component: Phase3Page },
  { key: 'llm-model-governance', label: 'LLM大模型治理', component: LlmModelGovernancePage },
  { key: 'knowledge-governance', label: '知识库', component: KnowledgeGovernancePage },
  { key: 'email-reply-review', label: '邮件审核', component: EmailReplyReviewPage },
  { key: 'phase5-integration', label: '真实 API 联调', component: Phase5IntegrationPage },
];

const pageKeys = new Set(menuItems.map((item) => item.key));
const activePageKey = ref(pageKeyFromHash());
const activePage = computed(
  () => menuItems.find((item) => item.key === activePageKey.value) || menuItems[0],
);

function pageKeyFromHash() {
  const key = String(globalThis.location?.hash || '').replace(/^#/, '');
  return pageKeys.has(key) ? key : 'runtime-overview';
}

function selectPage(key) {
  activePageKey.value = pageKeys.has(key) ? key : 'runtime-overview';
}

function syncPageFromHash() {
  activePageKey.value = pageKeyFromHash();
}

onMounted(() => {
  syncPageFromHash();
  globalThis.addEventListener?.('hashchange', syncPageFromHash);
});

onBeforeUnmount(() => {
  globalThis.removeEventListener?.('hashchange', syncPageFromHash);
});
</script>
