<template>
  <view class="source-candidates-page">
    <view class="status-bar">
      <text>9:41</text>
      <view class="status-icons">
        <text>5G</text>
        <text>Wi-Fi</text>
        <text>78%</text>
      </view>
    </view>

    <view class="nav-bar source-nav-centered">
      <view class="nav-action" aria-label="返回" @click="goBack">‹</view>
      <view class="source-nav-title-block">
        <view class="nav-title">来源审核</view>
        <view class="nav-subtitle">lead_source_candidates · 自动发现候选池</view>
      </view>
      <view class="nav-action" aria-label="刷新" @click="loadCandidates">↻</view>
    </view>

    <scroll-view scroll-y class="source-content">
      <view class="source-summary-card">
        <view class="source-summary-top">
          <view>
            <view class="source-summary-title">第二阶段今日来源池</view>
            <view class="source-summary-meta">Low/Medium 自动准入 · High 人工复核 · Forbidden 阻断</view>
          </view>
          <text class="source-tag source-tag-blue">{{ totalCount }} 新增</text>
        </view>

        <view class="source-map">
          <view
            v-for="stat in sourceStats"
            :key="stat.key"
            :class="['source-tile', 'source-summary-tile', isSourceStatActive(stat) ? 'source-summary-tile-active' : '']"
            @click="selectSourceStat(stat)"
          >
            <text class="source-kicker">{{ stat.label }}</text>
            <text :class="['source-number', stat.className]">{{ stat.count }}</text>
          </view>
        </view>
      </view>

      <view class="section-head">
        <text class="section-title">候选来源</text>
        <text class="section-note">{{ statusText }}</text>
      </view>

      <view v-if="errorMessage" class="source-alert">{{ errorMessage }}</view>
      <view v-else-if="isLoading" class="source-empty">正在从真实 API 加载来源候选...</view>
      <view v-else-if="!candidates.length" class="source-empty">当前筛选下没有来源候选</view>

      <view v-else class="source-list">
        <view v-for="candidate in filteredCandidates" :key="candidate.id" class="source-card" @click="openCandidate(candidate.id)">
          <view class="source-card-top">
            <view class="source-card-main">
              <view class="source-name">{{ candidate.normalizedDomain || candidate.sourceUrl || 'Unknown domain' }}</view>
              <view class="source-meta">
                {{ candidate.platform }} · {{ candidate.city }} · {{ candidate.discoveryMethod }}
              </view>
            </view>
            <text :class="['source-tag', getRiskClass(candidate.riskLevel)]">{{ candidate.riskLevel }}</text>
          </view>

          <view class="source-tag-row">
            <text class="source-tag source-tag-blue">{{ candidate.reviewStatus }}</text>
            <text :class="['source-tag', candidate.approvedForExtraction ? 'source-tag-green' : 'source-tag-red']">
              {{ candidate.approvedForExtraction ? '可抽取' : '不可抽取' }}
            </text>
            <text v-if="candidate.isDuplicate" class="source-tag source-tag-amber">疑似重复</text>
          </view>

          <view class="source-url">{{ candidate.sourceUrl || 'Unknown URL' }}</view>
          <view class="source-evidence">{{ candidate.evidenceNote || 'Unknown' }}</view>
        </view>
      </view>
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

import { buildBottomTabs, navigateBottomTab } from '../../services/bottomTabs.js';
import { sourceCandidatesService } from '../../services/sourceCandidates.js';
import '../../styles/home.css';
import '../../styles/sourceCandidates.css';

const candidates = ref([]);
const totalCount = ref(0);
const isLoading = ref(false);
const errorMessage = ref('');
const activeSourceStat = ref('');

const bottomTabs = buildBottomTabs('insights');

const sourceStats = computed(() => [
  { key: 'high-review', label: '待审 High', count: highReviewCount.value, className: 'source-number-red' },
  { key: 'approved', label: '可抽取来源', count: approvedExtractionCount.value, className: 'source-number-green' },
  { key: 'duplicate', label: '重复候选', count: duplicateCount.value, className: 'source-number-amber' },
  { key: 'forbidden', label: '阻断来源', count: forbiddenCount.value, className: '' },
]);

const highReviewCount = computed(
  () => candidates.value.filter((item) => item.riskLevel === 'High' && !item.approvedForExtraction).length,
);
const approvedExtractionCount = computed(() => candidates.value.filter((item) => item.approvedForExtraction).length);
const duplicateCount = computed(() => candidates.value.filter((item) => item.isDuplicate).length);
const forbiddenCount = computed(() => countRisk('Forbidden'));
const filteredCandidates = computed(() => {
  switch (activeSourceStat.value) {
    case 'high-review':
      return candidates.value.filter((item) => item.riskLevel === 'High' && !item.approvedForExtraction);
    case 'approved':
      return candidates.value.filter((item) => item.approvedForExtraction);
    case 'duplicate':
      return candidates.value.filter((item) => item.isDuplicate);
    case 'forbidden':
      return candidates.value.filter((item) => item.riskLevel === 'Forbidden');
    default:
      return candidates.value;
  }
});
const statusText = computed(() => (isLoading.value ? '加载中' : `${filteredCandidates.value.length} 条证据优先`));

onMounted(loadCandidates);

async function loadCandidates() {
  isLoading.value = true;
  errorMessage.value = '';
  try {
    const payload = await sourceCandidatesService.listSourceCandidates({
      limit: 100,
      offset: 0,
    });
    candidates.value = payload.items;
    totalCount.value = payload.total;
  } catch (_error) {
    candidates.value = [];
    totalCount.value = 0;
    errorMessage.value = '真实 API 暂不可用，请检查 apps/api 服务和网络配置。';
  } finally {
    isLoading.value = false;
  }
}

function selectSourceStat(stat) {
  activeSourceStat.value = activeSourceStat.value === stat.key ? '' : stat.key;
}

function isSourceStatActive(stat) {
  return activeSourceStat.value === stat.key;
}

function countRisk(riskLevel) {
  return candidates.value.filter((item) => item.riskLevel === riskLevel).length;
}

function getRiskClass(riskLevel) {
  if (riskLevel === 'Low') {
    return 'source-tag-green';
  }
  if (riskLevel === 'Medium') {
    return 'source-tag-amber';
  }
  if (riskLevel === 'High' || riskLevel === 'Forbidden') {
    return 'source-tag-red';
  }
  return 'source-tag-blue';
}

function openCandidate(id) {
  if (!id || !globalThis.uni?.navigateTo) {
    return;
  }

  globalThis.uni.navigateTo({ url: `/pages/sources/detail?id=${encodeURIComponent(id)}` });
}

function goBack() {
  if (globalThis.uni?.navigateBack) {
    globalThis.uni.navigateBack();
  }
}

function openTab(tab) {
  navigateBottomTab(tab);
}
</script>
