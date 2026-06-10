<template>
  <view class="cleaned-leads-page">
    <view class="status-bar">
      <text>9:41</text>
      <view class="status-icons">
        <text>5G</text>
        <text>Wi-Fi</text>
        <text>78%</text>
      </view>
    </view>

    <view class="nav-bar cleaned-nav-centered">
      <view class="nav-action" aria-label="返回" @click="goBack">‹</view>
      <view class="cleaned-nav-title-block">
        <view class="nav-title">被清洗线索</view>
        <view class="nav-subtitle">已确认无效、重复或放弃的线索</view>
      </view>
      <view class="nav-action" aria-label="刷新" @click="loadCleanedLeads">↻</view>
    </view>

    <scroll-view scroll-y class="cleaned-content">
      <view class="cleaned-summary-card">
        <view class="cleaned-summary-top">
          <view>
            <view class="cleaned-title">清洗结果总览</view>
            <view class="cleaned-meta">人工审计视图 · 展示清洗原因和联系方式</view>
          </view>
          <text class="cleaned-tag cleaned-tag-blue">{{ totalCount }} 条</text>
        </view>

        <view class="cleaned-metric-grid">
          <view
            v-for="stat in cleanedStats"
            :key="stat.key"
            :class="['cleaned-metric', activeCleanedFilter === stat.key ? 'cleaned-metric-active' : '']"
            @click="selectCleanedStat(stat)"
          >
            <text class="cleaned-kicker">{{ stat.label }}</text>
            <text :class="['cleaned-number', stat.className]">{{ stat.count }}</text>
          </view>
        </view>
      </view>

      <view class="section-head">
        <text class="section-title">清洗明细</text>
        <text class="section-note">{{ statusText }}</text>
      </view>

      <view v-if="errorMessage" class="cleaned-empty cleaned-alert">{{ errorMessage }}</view>
      <view v-else-if="isLoading" class="cleaned-empty">正在加载被清洗线索...</view>
      <view v-else-if="!filteredCleanedLeads.length" class="cleaned-empty">暂无已执行清洗结果</view>

      <view v-else class="cleaned-list">
        <view v-for="item in filteredCleanedLeads" :key="item.id" class="cleanup-result-card" @click="openLeadDetail(item)">
          <view class="cleaned-card-top">
            <view class="cleaned-card-main">
              <view class="cleaned-name">{{ item.leadDisplayName || 'Unknown' }}</view>
              <view class="cleaned-card-meta">线索 {{ item.stagingLeadId || 'Unknown' }}</view>
            </view>
            <text :class="['cleaned-tag', tagClassFor(item.suggestionType)]">{{ item.confidenceText }}</text>
          </view>

          <view class="cleaned-tag-row">
            <text :class="['cleaned-tag', tagClassFor(item.suggestionType)]">{{ item.suggestionTypeLabel }}</text>
            <text class="cleaned-tag cleaned-tag-red">{{ item.reviewStatusLabel }}</text>
            <text v-if="item.executedBy" class="cleaned-tag cleaned-tag-blue">执行 {{ item.executedBy }}</text>
            <text v-if="item.targetLeadId" class="cleaned-tag cleaned-tag-amber">目标 {{ item.targetLeadId }}</text>
          </view>

          <view v-if="item.contacts.length" class="cleaned-contact-block">
            <text class="cleaned-block-title">联系方式</text>
            <view v-for="contact in item.contacts.slice(0, 2)" :key="`${item.id}-${contact.type}-${contact.value}`" class="cleaned-contact-row">
              <text class="cleaned-contact-type">{{ contact.type }}</text>
              <text class="cleaned-contact-value">{{ contact.value }}</text>
            </view>
          </view>

          <view class="cleaned-reason-block">
            <text class="cleaned-block-title">清洗原因</text>
            <text class="cleaned-copy-strong">{{ item.reason }}</text>
          </view>

          <text class="cleaned-copy">建议动作：{{ item.recommendedAction }}</text>
          <text v-if="item.executedAt" class="cleaned-time">执行时间：{{ item.executedAt }}</text>
          <view class="cleaned-grade-actions" @click.stop>
            <text class="cleaned-action-label">调整等级</text>
            <button
              v-for="grade in GRADE_OPTIONS"
              :key="`${item.id}-${grade.value}`"
              class="cleaned-grade-button"
              @click="handleUpdateGrade(item, grade)"
            >
              {{ grade.label }}
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
import { computed, onMounted, ref } from 'vue';

import { buildBottomTabs, navigateBottomTab } from '../../services/bottomTabs.js';
import { leadCleanupService } from '../../services/leadCleanup.js';
import { stagingLeadActionsService } from '../../services/stagingLeadActions.js';
import '../../styles/home.css';
import '../../styles/cleanedLeads.css';

const CLEANED_TYPES = ['confirm_invalid', 'mark_abandoned', 'strong_duplicate', 'possible_duplicate'];
const GRADE_OPTIONS = [
  { label: 'A级', value: 'A' },
  { label: 'B级', value: 'B' },
  { label: 'C级', value: 'C' },
  { label: 'D级', value: 'D' },
  { label: 'E级', value: 'E' },
];

const cleanedLeads = ref([]);
const totalCount = ref(0);
const isLoading = ref(false);
const errorMessage = ref('');
const activeCleanedFilter = ref('');
const bottomTabs = buildBottomTabs('leads');

const cleanedStats = computed(() => [
  { key: 'invalid', label: '确认无效', count: countType('confirm_invalid'), className: 'cleaned-number-red' },
  { key: 'abandoned', label: '放弃线索', count: countType('mark_abandoned'), className: 'cleaned-number-amber' },
  { key: 'duplicate', label: '重复线索', count: countType('strong_duplicate') + countType('possible_duplicate'), className: 'cleaned-number-blue' },
  { key: 'contacts', label: '有联系方式', count: cleanedLeads.value.filter((item) => item.contacts.length).length, className: 'cleaned-number-green' },
]);

const filteredCleanedLeads = computed(() => {
  switch (activeCleanedFilter.value) {
    case 'invalid':
      return cleanedLeads.value.filter((item) => item.suggestionType === 'confirm_invalid');
    case 'abandoned':
      return cleanedLeads.value.filter((item) => item.suggestionType === 'mark_abandoned');
    case 'duplicate':
      return cleanedLeads.value.filter((item) => ['strong_duplicate', 'possible_duplicate'].includes(item.suggestionType));
    case 'contacts':
      return cleanedLeads.value.filter((item) => item.contacts.length);
    default:
      return cleanedLeads.value;
  }
});

const statusText = computed(() => (isLoading.value ? '加载中' : `${filteredCleanedLeads.value.length} 条已清洗`));

onMounted(loadCleanedLeads);

async function loadCleanedLeads() {
  isLoading.value = true;
  errorMessage.value = '';
  try {
    const results = await Promise.all(
      CLEANED_TYPES.map((suggestionType) => leadCleanupService.listCleanupSuggestions({
        suggestionType,
        reviewStatus: 'executed',
        limit: 100,
      })),
    );
    const merged = results.flatMap((result) => result.items || []);
    cleanedLeads.value = merged.sort((a, b) => String(b.executedAt || b.updatedAt).localeCompare(String(a.executedAt || a.updatedAt)));
    totalCount.value = results.reduce((sum, result) => sum + Number(result.total || 0), 0);
  } catch (error) {
    cleanedLeads.value = [];
    totalCount.value = 0;
    errorMessage.value = `被清洗线索加载失败：${error.message || 'Unknown'}`;
  } finally {
    isLoading.value = false;
  }
}

function countType(type) {
  return cleanedLeads.value.filter((item) => item.suggestionType === type).length;
}

function selectCleanedStat(stat) {
  activeCleanedFilter.value = activeCleanedFilter.value === stat.key ? '' : stat.key;
}

function tagClassFor(type) {
  if (type === 'confirm_invalid') {
    return 'cleaned-tag-red';
  }
  if (type === 'mark_abandoned') {
    return 'cleaned-tag-amber';
  }
  return 'cleaned-tag-blue';
}

function openLeadDetail(item) {
  if (!item?.stagingLeadId || !globalThis.uni?.navigateTo) {
    return;
  }

  globalThis.uni.navigateTo({ url: `/pages/leads/detail?id=${encodeURIComponent(item.stagingLeadId)}` });
}

function notify(message) {
  if (globalThis.uni?.showToast) {
    globalThis.uni.showToast({ title: message, icon: 'none' });
  }
}

async function handleUpdateGrade(item, grade) {
  if (!item?.stagingLeadId) {
    notify('缺少线索ID');
    return;
  }

  try {
    await stagingLeadActionsService.updateGrade(item.stagingLeadId, {
      grade: grade.value,
      actor: '当前用户',
      reason: `移动端从被清洗线索页人工调整为${grade.label}。清洗原因：${item.reason || 'Unknown'}`,
    });
    notify(`已调整为${grade.label}`);
    await loadCleanedLeads();
  } catch (_error) {
    notify('调整等级失败');
  }
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
