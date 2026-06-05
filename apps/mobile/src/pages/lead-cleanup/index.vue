<template>
  <view class="lead-cleanup-page">
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
        <view class="nav-title">清洗建议</view>
        <view class="nav-subtitle">Watch / Invalid / 重复线索治理</view>
      </view>
      <view class="nav-action" aria-label="刷新" @click="loadSuggestions">↻</view>
    </view>

    <scroll-view scroll-y class="cleanup-content">
      <section class="cleanup-summary-card">
        <view class="cleanup-summary-top">
          <view>
            <view class="cleanup-summary-title">第三阶段清洗队列</view>
            <view class="cleanup-summary-meta">Agent 只生成建议 · 人工审批和执行 · 不提供移除入口</view>
          </view>
          <text class="cleanup-tag cleanup-tag-blue">{{ totalCount }} 条</text>
        </view>
        <view class="cleanup-metric-grid">
          <view class="cleanup-metric-tile">
            <text class="cleanup-kicker">待复核</text>
            <text class="cleanup-number cleanup-number-amber">{{ pendingCount }}</text>
          </view>
          <view class="cleanup-metric-tile">
            <text class="cleanup-kicker">高风险动作</text>
            <text class="cleanup-number cleanup-number-red">{{ elevatedCount }}</text>
          </view>
          <view class="cleanup-metric-tile">
            <text class="cleanup-kicker">可执行</text>
            <text class="cleanup-number cleanup-number-green">{{ approvedCount }}</text>
          </view>
          <view class="cleanup-metric-tile">
            <text class="cleanup-kicker">已执行</text>
            <text class="cleanup-number">{{ executedCount }}</text>
          </view>
        </view>
      </section>

      <view class="section-head">
        <text class="section-title">建议类型</text>
        <text class="section-note">按治理动作筛选</text>
      </view>
      <scroll-view scroll-x class="cleanup-chip-row">
        <text
          v-for="option in suggestionTypeOptions"
          :key="option.value || 'all-type'"
          :class="['cleanup-chip', filters.suggestionType === option.value ? 'cleanup-chip-active' : '']"
          @click="setFilter('suggestionType', option.value)"
        >
          {{ option.label }}
        </text>
      </scroll-view>

      <view class="cleanup-filter-grid">
        <picker
          mode="selector"
          :range="reviewStatusOptions"
          range-key="label"
          @change="onPickerChange('reviewStatus', reviewStatusOptions, $event)"
        >
          <view class="cleanup-filter-select">状态 · {{ selectedReviewStatusLabel }}</view>
        </picker>
        <picker mode="selector" :range="confidenceOptions" range-key="label" @change="onConfidenceChange">
          <view class="cleanup-filter-select">置信度 · {{ selectedConfidenceLabel }}</view>
        </picker>
      </view>

      <view class="section-head">
        <text class="section-title">建议列表</text>
        <text class="section-note">{{ statusText }}</text>
      </view>

      <view v-if="errorMessage" class="cleanup-alert">{{ errorMessage }}</view>
      <view v-else-if="isLoading" class="cleanup-empty">正在从真实 API 加载清洗建议...</view>
      <view v-else-if="!suggestions.length" class="cleanup-empty">当前筛选下没有清洗建议</view>

      <view v-else class="cleanup-list">
        <view v-for="suggestion in suggestions" :key="suggestion.id" class="cleanup-card">
          <view class="cleanup-card-top">
            <view class="cleanup-card-main">
              <view class="cleanup-name">{{ suggestion.suggestionTypeLabel }}</view>
              <view class="cleanup-meta">
                来源线索 {{ suggestion.stagingLeadId }} · 目标线索 {{ suggestion.targetLeadName || suggestion.targetLeadId || 'Unknown' }}
              </view>
            </view>
            <text
              :class="[
                'cleanup-tag',
                suggestion.reviewStatus === 'approved'
                  ? 'cleanup-tag-green'
                  : suggestion.reviewStatus === 'rejected'
                    ? 'cleanup-tag-red'
                    : suggestion.reviewStatus === 'executed'
                      ? 'cleanup-tag-blue'
                      : 'cleanup-tag-amber',
              ]"
            >
              {{ suggestion.reviewStatusLabel }}
            </text>
          </view>

          <view class="cleanup-tag-row">
            <text class="cleanup-tag cleanup-tag-blue">置信度 {{ suggestion.confidenceText }}</text>
            <text v-if="suggestion.requiresElevatedPermission" class="cleanup-tag cleanup-tag-red">高风险权限</text>
            <text v-else class="cleanup-tag cleanup-tag-green">普通复核</text>
          </view>

          <text class="cleanup-copy-strong">原因：{{ suggestion.reason }}</text>
          <text class="cleanup-copy">证据：{{ suggestion.evidenceNote }}</text>
          <text v-if="suggestion.evidenceLinks.length" class="cleanup-link">{{ suggestion.evidenceLinks[0] }}</text>
          <view class="cleanup-permission-tip">
            <text>{{ suggestion.permissionHint }}</text>
          </view>
          <text class="cleanup-copy">建议动作：{{ suggestion.recommendedAction }}</text>

          <view class="cleanup-action-row">
            <button
              class="cleanup-button cleanup-button-secondary"
              :disabled="suggestion.reviewStatus !== 'pending'"
              @click="handleReject(suggestion)"
            >
              拒绝
            </button>
            <button
              class="cleanup-button cleanup-button-primary"
              :disabled="suggestion.reviewStatus !== 'pending'"
              @click="handleApprove(suggestion)"
            >
              通过
            </button>
            <button
              class="cleanup-button cleanup-button-strong"
              :disabled="suggestion.reviewStatus !== 'approved'"
              @click="handleExecute(suggestion)"
            >
              执行
            </button>
          </view>
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
import { leadCleanupService } from '../../services/leadCleanup.js';
import '../../styles/home.css';
import '../../styles/leadCleanup.css';

const suggestions = ref([]);
const totalCount = ref(0);
const isLoading = ref(false);
const errorMessage = ref('');
const currentActorRole = ref('ops');

const filters = reactive({
  suggestionType: '',
  reviewStatus: 'pending',
  minConfidence: '',
});

const suggestionTypeOptions = [
  { label: '全部', value: '' },
  { label: '强重复', value: 'strong_duplicate' },
  { label: '疑似重复', value: 'possible_duplicate' },
  { label: '恢复 Watch', value: 'restore_from_watch' },
  { label: '确认无效', value: 'confirm_invalid' },
  { label: '放弃线索', value: 'mark_abandoned' },
  { label: '人工复核', value: 'needs_manual_review' },
];

const reviewStatusOptions = [
  { label: '全部', value: '' },
  { label: '待复核', value: 'pending' },
  { label: '已通过', value: 'approved' },
  { label: '已拒绝', value: 'rejected' },
  { label: '已执行', value: 'executed' },
];

const confidenceOptions = [
  { label: '全部', value: '' },
  { label: '80%+', value: 0.8 },
  { label: '60%+', value: 0.6 },
];

const bottomTabs = buildBottomTabs('leads');

const selectedReviewStatusLabel = computed(
  () => reviewStatusOptions.find((option) => option.value === filters.reviewStatus)?.label || '全部',
);
const selectedConfidenceLabel = computed(
  () => confidenceOptions.find((option) => option.value === filters.minConfidence)?.label || '全部',
);
const pendingCount = computed(() => suggestions.value.filter((item) => item.reviewStatus === 'pending').length);
const approvedCount = computed(() => suggestions.value.filter((item) => item.reviewStatus === 'approved').length);
const executedCount = computed(() => suggestions.value.filter((item) => item.reviewStatus === 'executed').length);
const elevatedCount = computed(() => suggestions.value.filter((item) => item.requiresElevatedPermission).length);
const statusText = computed(() => (isLoading.value ? '加载中' : `${suggestions.value.length} 条清洗建议`));

onMounted(loadSuggestions);

async function loadSuggestions() {
  isLoading.value = true;
  errorMessage.value = '';
  try {
    const payload = await leadCleanupService.listCleanupSuggestions({
      suggestionType: filters.suggestionType,
      reviewStatus: filters.reviewStatus,
      minConfidence: filters.minConfidence,
      limit: 100,
    });
    suggestions.value = payload.items;
    totalCount.value = payload.total;
  } catch (error) {
    suggestions.value = [];
    totalCount.value = 0;
    errorMessage.value = `清洗建议加载失败：${error.message || 'Unknown'}`;
  } finally {
    isLoading.value = false;
  }
}

function setFilter(key, value) {
  filters[key] = value;
  loadSuggestions();
}

function onPickerChange(key, options, event) {
  const index = Number(event.detail.value);
  filters[key] = options[index]?.value || '';
  loadSuggestions();
}

function onConfidenceChange(event) {
  const index = Number(event.detail.value);
  filters.minConfidence = confidenceOptions[index]?.value || '';
  loadSuggestions();
}

function notify(message) {
  if (globalThis.uni?.showToast) {
    globalThis.uni.showToast({ title: message, icon: 'none' });
  }
}

async function handleApprove(suggestion) {
  try {
    await leadCleanupService.approveSuggestion(suggestion.id, {
      actor: '当前用户',
      actorRole: currentActorRole.value,
      reviewNote: '移动端人工确认清洗建议。',
    });
    await loadSuggestions();
    notify('已通过建议');
  } catch (error) {
    notify(error.message || '通过失败');
  }
}

async function handleReject(suggestion) {
  try {
    await leadCleanupService.rejectSuggestion(suggestion.id, {
      actor: '当前用户',
      actorRole: 'ops',
      reviewNote: '移动端人工拒绝清洗建议。',
    });
    await loadSuggestions();
    notify('已拒绝建议');
  } catch (error) {
    notify(error.message || '拒绝失败');
  }
}

async function handleExecute(suggestion) {
  try {
    await leadCleanupService.executeSuggestion(suggestion.id, {
      actor: '当前用户',
      actorRole: currentActorRole.value,
      executionNote: '移动端人工确认执行清洗建议。',
    });
    await loadSuggestions();
    notify('已执行建议');
  } catch (error) {
    notify(error.message || '执行失败');
  }
}

function openTab(tab) {
  navigateBottomTab(tab);
}
</script>
