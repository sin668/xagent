<template>
  <view class="lead-pool-page">
    <view class="status-bar">
      <text>9:41</text>
      <view class="status-icons">
        <text>5G</text>
        <text>Wi-Fi</text>
        <text>78%</text>
      </view>
    </view>

    <view class="nav-bar">
      <view>
        <view class="nav-title">线索池</view>
        <view class="nav-subtitle">移动端优先处理队列</view>
      </view>
      <view class="nav-action" aria-label="筛选">⌕</view>
    </view>

    <scroll-view scroll-y class="lead-pool-content">
      <view class="lead-summary-card source-summary-card">
        <view class="source-summary-top">
          <view>
            <view class="source-summary-title">线索联系方式概览</view>
            <view class="source-summary-meta">有邮箱联系线索 · 有社交媒体联系线索 · A/B/C级线索 · D/E级线索</view>
          </view>
          <text class="source-tag source-tag-blue">{{ leads.length }} 条</text>
        </view>

        <view class="source-map">
          <view v-for="stat in leadStats" :key="stat.key" class="source-tile">
            <text class="source-kicker">{{ stat.label }}</text>
            <text :class="['source-number', stat.className]">{{ stat.count }}</text>
          </view>
        </view>
      </view>

      <view class="lead-search">
        <text>⌕</text>
        <text>搜索车商、城市、Telegram、邮箱</text>
      </view>

      <scroll-view scroll-x class="chip-row">
        <text
          v-for="tab in tabs"
          :key="tab.key"
          :class="['filter-chip', activeFilter === tab.key ? 'filter-chip-active' : '']"
          @click="activeFilter = tab.key"
        >
          {{ tab.label }} {{ tab.count }}
        </text>
      </scroll-view>

      <view v-if="cards.length" class="lead-list">
        <view
          v-for="card in cards"
          :key="card.id"
          :class="['pool-card', card.isDoNotContact ? 'pool-card-dnc' : '']"
          @click="openLead(card.id)"
        >
          <view class="pool-card-top">
            <view>
              <view class="pool-lead-name">{{ card.customerName }}</view>
              <view class="pool-lead-meta">
                {{ card.city }} · {{ card.customerType }} · {{ card.channel }}
              </view>
            </view>
            <text :class="['pool-tag', card.gradeClass]">{{ card.gradeLabel }}</text>
          </view>

          <view class="pool-tag-row">
            <text :class="['pool-tag', card.riskClass]">{{ card.riskLabel }}</text>
            <text class="pool-tag pool-tag-blue">{{ card.handoffLabel }}</text>
            <text v-if="card.complianceLabel" class="pool-tag pool-tag-red">{{ card.complianceLabel }}</text>
            <text v-if="card.isOverdue" class="pool-tag pool-tag-amber">SLA 超时</text>
            <text v-if="card.isDoNotContact" class="pool-tag pool-tag-red">勿扰</text>
            <text v-for="marker in card.riskMarkers" :key="`${card.id}-${marker}`" class="pool-tag pool-tag-red">
              {{ marker }}
            </text>
          </view>

          <view class="pool-evidence">{{ card.evidenceNote }}</view>
        </view>
      </view>
      <view v-else class="empty-state">当前筛选下没有可处理线索</view>
    </scroll-view>

    <view class="tabbar">
      <view
        v-for="tab in bottomTabs"
        :key="tab.label"
        :class="['tab', tab.active ? 'tab-active' : '', tab.disabled ? 'tab-disabled' : '']"
        @click="openTab(tab)"
      >
        <text class="tab-icon">{{ tab.icon }}</text>
        <text>{{ tab.label }}</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';

import { mapCustomerListToLeadPool, mapStagingLeadListToLeadPool, mergeCustomerAndStagingLeadPools } from '../../services/apiAdapters.js';
import { apiClient } from '../../services/apiClient.js';
import { buildBottomTabs, navigateBottomTab } from '../../services/bottomTabs.js';
import { buildLeadFilterTabs, buildLeadPoolStats, filterLeadPool, getLeadCardViewModel } from '../../services/leadPool.js';
import '../../styles/home.css';
import '../../styles/leadPool.css';
import '../../styles/sourceCandidates.css';

const activeFilter = ref('all');
const leads = ref([]);
const leadStats = computed(() => buildLeadPoolStats(leads.value));
const tabs = computed(() => buildLeadFilterTabs(leads.value));
const cards = computed(() => filterLeadPool(leads.value, activeFilter.value).map(getLeadCardViewModel));

const bottomTabs = buildBottomTabs('leads');

onMounted(async () => {
  try {
    const [customerPayload, stagingPayload] = await Promise.all([
      apiClient.get('/customers?limit=100'),
      apiClient.get('/staging-leads?limit=100'),
    ]);
    leads.value = mergeCustomerAndStagingLeadPools(
      mapCustomerListToLeadPool(customerPayload),
      mapStagingLeadListToLeadPool(stagingPayload),
    );
  } catch (_error) {
    leads.value = [];
  }
});

function openLead(id) {
  if (!id || !globalThis.uni?.navigateTo) {
    return;
  }

  globalThis.uni.navigateTo({ url: `/pages/leads/detail?id=${encodeURIComponent(id)}` });
}

function openTab(tab) {
  navigateBottomTab(tab);
}
</script>
