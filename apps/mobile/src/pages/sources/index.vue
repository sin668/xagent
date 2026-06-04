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

    <view class="nav-bar">
      <view>
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
          <view class="source-tile">
            <text class="source-kicker">待审 High</text>
            <text class="source-number source-number-red">{{ highReviewCount }}</text>
          </view>
          <view class="source-tile">
            <text class="source-kicker">可抽取来源</text>
            <text class="source-number source-number-green">{{ approvedExtractionCount }}</text>
          </view>
          <view class="source-tile">
            <text class="source-kicker">重复候选</text>
            <text class="source-number source-number-amber">{{ duplicateCount }}</text>
          </view>
          <view class="source-tile">
            <text class="source-kicker">阻断来源</text>
            <text class="source-number">{{ forbiddenCount }}</text>
          </view>
        </view>
      </view>

      <view class="section-head">
        <text class="section-title">风险筛选</text>
        <text class="section-note">按准入状态</text>
      </view>

      <scroll-view scroll-x class="source-chip-row">
        <text
          v-for="risk in riskFilters"
          :key="risk.value || 'all-risk'"
          :class="['source-chip', filters.riskLevel === risk.value ? 'source-chip-active' : '']"
          @click="setFilter('riskLevel', risk.value)"
        >
          {{ risk.label }}
        </text>
      </scroll-view>

      <view class="risk-strip">
        <view v-for="risk in riskDistribution" :key="risk.key" class="risk-pill">
          <text :class="['risk-count', risk.className]">{{ risk.count }}</text>
          <text>{{ risk.label }}</text>
        </view>
      </view>

      <view class="filter-grid">
        <picker
          mode="selector"
          :range="reviewStatusOptions"
          range-key="label"
          @change="onPickerChange('reviewStatus', reviewStatusOptions, $event)"
        >
          <view class="filter-select">状态 · {{ selectedReviewStatusLabel }}</view>
        </picker>
        <picker mode="selector" :range="countryOptions" @change="onRawPickerChange('country', countryOptions, $event)">
          <view class="filter-select">国家 · {{ filters.country || '全部' }}</view>
        </picker>
        <picker mode="selector" :range="cityOptions" @change="onRawPickerChange('city', cityOptions, $event)">
          <view class="filter-select">城市 · {{ filters.city || '全部' }}</view>
        </picker>
        <picker mode="selector" :range="platformOptions" @change="onRawPickerChange('platform', platformOptions, $event)">
          <view class="filter-select">平台 · {{ filters.platform || '全部' }}</view>
        </picker>
      </view>

      <view class="section-head">
        <text class="section-title">候选来源</text>
        <text class="section-note">{{ statusText }}</text>
      </view>

      <view v-if="errorMessage" class="source-alert">{{ errorMessage }}</view>
      <view v-else-if="isLoading" class="source-empty">正在从真实 API 加载来源候选...</view>
      <view v-else-if="!candidates.length" class="source-empty">当前筛选下没有来源候选</view>

      <view v-else class="source-list">
        <view v-for="candidate in candidates" :key="candidate.id" class="source-card" @click="openCandidate(candidate.id)">
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
import { computed, onMounted, reactive, ref } from 'vue';

import { buildBottomTabs, navigateBottomTab } from '../../services/bottomTabs.js';
import { sourceCandidatesService } from '../../services/sourceCandidates.js';
import '../../styles/home.css';
import '../../styles/sourceCandidates.css';

const candidates = ref([]);
const totalCount = ref(0);
const isLoading = ref(false);
const errorMessage = ref('');

const filters = reactive({
  riskLevel: '',
  reviewStatus: '',
  country: '',
  city: '',
  platform: '',
});

const riskFilters = [
  { label: '全部', value: '' },
  { label: 'Low', value: 'Low' },
  { label: 'Medium', value: 'Medium' },
  { label: 'High 待审', value: 'High' },
  { label: 'Forbidden', value: 'Forbidden' },
];

const reviewStatusOptions = [
  { label: '全部', value: '' },
  { label: '待复核', value: 'pending_review' },
  { label: '自动通过', value: 'auto_approved' },
  { label: '人工通过', value: 'approved' },
  { label: '高风险复核', value: 'high_risk_review' },
  { label: '已拒绝', value: 'rejected' },
  { label: '已暂停', value: 'paused' },
];

const bottomTabs = buildBottomTabs('sources');

const countryOptions = computed(() => buildOptions('country'));
const cityOptions = computed(() => buildOptions('city'));
const platformOptions = computed(() => buildOptions('platform'));

const selectedReviewStatusLabel = computed(
  () => reviewStatusOptions.find((option) => option.value === filters.reviewStatus)?.label || '全部',
);

const riskDistribution = computed(() => [
  { key: 'Low', label: 'Low', count: countRisk('Low'), className: 'source-number-green' },
  { key: 'Medium', label: 'Medium', count: countRisk('Medium'), className: 'source-number-amber' },
  { key: 'High', label: 'High', count: countRisk('High'), className: 'source-number-red' },
  { key: 'Forbidden', label: 'Forbidden', count: countRisk('Forbidden'), className: '' },
]);

const highReviewCount = computed(
  () => candidates.value.filter((item) => item.riskLevel === 'High' && !item.approvedForExtraction).length,
);
const approvedExtractionCount = computed(() => candidates.value.filter((item) => item.approvedForExtraction).length);
const duplicateCount = computed(() => candidates.value.filter((item) => item.isDuplicate).length);
const forbiddenCount = computed(() => countRisk('Forbidden'));
const statusText = computed(() => (isLoading.value ? '加载中' : `${candidates.value.length} 条证据优先`));

onMounted(loadCandidates);

async function loadCandidates() {
  isLoading.value = true;
  errorMessage.value = '';
  try {
    const payload = await sourceCandidatesService.listSourceCandidates({
      riskLevel: filters.riskLevel,
      reviewStatus: filters.reviewStatus,
      country: filters.country,
      city: filters.city,
      platform: filters.platform,
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

function setFilter(key, value) {
  filters[key] = value;
  loadCandidates();
}

function onPickerChange(key, options, event) {
  const selected = options[Number(event.detail.value)];
  setFilter(key, selected?.value || '');
}

function onRawPickerChange(key, options, event) {
  const selected = options[Number(event.detail.value)];
  setFilter(key, selected === '全部' ? '' : selected);
}

function buildOptions(key) {
  const values = candidates.value.map((item) => item[key]).filter(Boolean);
  return ['全部', ...Array.from(new Set(values))];
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

function openTab(tab) {
  navigateBottomTab(tab);
}
</script>
