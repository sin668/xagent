<template>
  <view class="home-page">
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
        <view class="nav-title">XAgent 获客</view>
        <view class="nav-subtitle">俄罗斯 · 二手/库存车</view>
      </view>
      <view class="nav-action" aria-label="通知">🔔</view>
    </view>

    <scroll-view scroll-y class="content">
      <view class="hero-card">
        <view class="hero-image">
          <image
            mode="aspectFill"
            src="https://images.unsplash.com/photo-1502877338535-766e1452684a?auto=format&fit=crop&w=900&q=80"
          />
        </view>
        <view class="hero-overlay">
          <view class="hero-eyebrow">低风险公开渠道运行中 · {{ dashboardLabel }}</view>
          <view>
            <view class="hero-title">今日优先处理 {{ dashboard.pendingPriorityCount }} 条 B/C 级线索</view>
            <view class="hero-desc">
              AI {{ dashboard.aiStatusText }}，{{ dashboard.reviewRequiredCount }} 条需要人工复核。
            </view>
          </view>
        </view>
      </view>

      <view class="metric-row">
        <view v-for="stat in dashboard.leadStats" :key="stat.key" class="metric-card">
          <text :class="['metric-value', stat.className || '']">{{ stat.count }}</text>
          <text class="metric-label">{{ stat.label }}</text>
        </view>
      </view>

      <view class="customer-metric-row">
        <view v-for="stat in dashboard.customerStats" :key="stat.key" class="metric-card customer-metric-card">
          <text class="metric-value customer-metric-value">{{ stat.count }}</text>
          <text class="metric-label">{{ stat.label }}</text>
        </view>
      </view>

      <view class="section-head">
        <text class="section-title">AI 作业队列</text>
        <text class="section-link">查看全部</text>
      </view>

      <view class="task-list">
        <view v-for="task in dashboard.executableAiTasks" :key="task.id" class="task-card">
          <view class="task-top">
            <view>
              <view class="task-name">{{ task.title }}</view>
              <view class="task-meta">
                {{ task.source }} · {{ task.candidateCount }} 个候选 · {{ task.estimateText }}
              </view>
            </view>
            <text :class="['tag', task.status === 'running' ? 'tag-blue' : 'tag-amber']">
              {{ task.status === 'running' ? '运行中' : '待复核' }}
            </text>
          </view>
          <view class="progress">
            <text class="progress-fill" :style="{ width: `${task.progress}%` }" />
          </view>
        </view>
      </view>

      <view class="section-head">
        <text class="section-title">渠道表现</text>
        <text class="section-note">仅显示可执行风险等级</text>
      </view>

      <view class="channel-list">
        <view v-for="channel in dashboard.channelPerformance" :key="channel.name" class="channel-card">
          <view class="channel-top">
            <text class="channel-name">{{ channel.name }}</text>
            <text :class="['tag', channel.riskLevel === 'Low' ? 'tag-green' : 'tag-amber']">
              {{ channel.riskLevel === 'Low' ? '低风险' : '中风险' }}
            </text>
          </view>
          <view class="channel-stats">
            <text>B 级线索 {{ channel.bGradeLeads }} 条</text>
            <text>有效率 {{ Math.round(channel.effectiveRate * 100) }}%</text>
          </view>
          <view class="progress">
            <text
              class="progress-fill"
              :style="{
                width: `${Math.round(channel.effectiveRate * 100)}%`,
                background: channel.riskLevel === 'Low' ? '#16a34a' : '#d97706',
              }"
            />
          </view>
        </view>
      </view>

      <view class="section-head">
        <text class="section-title">快速入口</text>
      </view>
      <view class="entry-grid">
        <view v-for="entry in entries" :key="entry.label" class="entry-card" @click="goTo(entry.path)">
          <view class="entry-icon">{{ entry.icon }}</view>
          <text class="entry-label">{{ entry.label }}</text>
        </view>
      </view>
    </scroll-view>

    <view class="tabbar">
      <view
        v-for="tab in tabs"
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

import {
  mapAdminOverviewToHomeData,
  mapStagingLeadListToLeadPool,
} from '../../services/apiAdapters.js';
import { apiClient } from '../../services/apiClient.js';
import { buildBottomTabs, navigateBottomTab } from '../../services/bottomTabs.js';
import { mapCustomer } from '../../services/customers.js';
import { buildHomeDashboard } from '../../services/homeMetrics.js';
import { buildLeadPoolStats } from '../../services/leadPool.js';
import { leadCleanupService } from '../../services/leadCleanup.js';
import { sourceCandidatesService } from '../../services/sourceCandidates.js';
import '../../styles/home.css';

const CLEANED_TYPES = ['confirm_invalid', 'mark_abandoned', 'strong_duplicate', 'possible_duplicate'];

const emptyDashboardInput = {
  leads: [],
  aiTasks: [],
  channels: [],
  customers: [],
};
const dashboard = ref(buildHomeDashboard(emptyDashboardInput));
const apiStatus = ref('loading');
const dashboardLabel = computed(() => (apiStatus.value === 'api' ? '后端实时数据' : '等待后端数据'));

const entries = [
  { label: '线索池', icon: '☷', path: '/pages/leads/index' },
  { label: '触达任务', icon: '↗', path: '/pages/outreach/index' },
  { label: '线索详情', icon: 'ⓘ', path: '/pages/leads/detail' },
];

const tabs = buildBottomTabs('home');

onMounted(async () => {
  try {
    const [overview, customerPayload, stagingPayload, sourceCandidatesPayload, cleanedLeadsTotal] = await Promise.all([
      apiClient.get('/dashboard/admin-overview'),
      apiClient.get('/customers?limit=500').catch(() => ({ items: [] })),
      apiClient.get('/staging-leads?limit=500').catch(() => ({ items: [] })),
      sourceCandidatesService.listSourceCandidates({ limit: 1, offset: 0 }).catch(() => ({ total: 0 })),
      loadCleanedLeadsTotal().catch(() => 0),
    ]);
    const homeData = mapAdminOverviewToHomeData(overview);
    const leadPoolLeads = mapStagingLeadListToLeadPool(stagingPayload);
    const abcLeadsTotal = buildLeadPoolStats(leadPoolLeads).find((stat) => stat.key === 'grade-abc')?.count ?? 0;
    dashboard.value = buildHomeDashboard({
      ...homeData,
      leadStatsSummary: {
        ...homeData.leadStatsSummary,
        abcLeadsTotal,
        sourceCandidatesTotal: sourceCandidatesPayload.total,
        cleanedLeadsTotal,
      },
      customers: (customerPayload.items || []).map(mapCustomer),
    });
    apiStatus.value = 'api';
  } catch (_error) {
    dashboard.value = buildHomeDashboard(emptyDashboardInput);
    apiStatus.value = 'error';
  }
});

async function loadCleanedLeadsTotal() {
  const results = await Promise.all(
    CLEANED_TYPES.map((suggestionType) => leadCleanupService.listCleanupSuggestions({
      suggestionType,
      reviewStatus: 'executed',
      limit: 100,
    })),
  );
  return results.reduce((sum, result) => sum + Number(result.total || 0), 0);
}

function goTo(path) {
  if (!path || !globalThis.uni?.navigateTo) {
    return;
  }

  globalThis.uni.navigateTo({ url: path });
}

function openTab(tab) {
  navigateBottomTab(tab);
}
</script>
