<template>
  <view class="email-replies-page">
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
        <view class="nav-title">邮件回复</view>
        <view class="nav-subtitle">EMAIL_REPLY · 低风险自动发送</view>
      </view>
      <view class="nav-action" aria-label="刷新" @click="loadReplies">✉</view>
    </view>

    <scroll-view scroll-y class="email-replies-content">
      <view class="metric-row">
        <view class="metric-card">
          <text class="metric-value">{{ summary.total }}</text>
          <text class="metric-label">待回复</text>
        </view>
        <view class="metric-card">
          <text class="metric-value metric-green">{{ summary.autoSend }}</text>
          <text class="metric-label">可自动发</text>
        </view>
        <view class="metric-card">
          <text class="metric-value metric-blue">{{ summary.manual }}</text>
          <text class="metric-label">需确认</text>
        </view>
      </view>

      <scroll-view scroll-x class="chip-row">
        <text
          v-for="filter in filters"
          :key="filter.key"
          :class="['filter-chip', activeFilter === filter.key ? 'filter-chip-active' : '']"
          @click="activeFilter = filter.key"
        >
          {{ filter.label }}
        </text>
      </scroll-view>

      <section class="email-decision-band">
        <view class="channel-top">
          <view>
            <view class="channel-name">自动发送准入</view>
            <view class="channel-stats">
              <text>白名单、固定 FAQ、首次触达、低风险场景；DNC 和 D/E 级 100% 阻断</text>
            </view>
          </view>
          <text class="pool-tag risk-low">规则在线</text>
        </view>
      </section>

      <view class="section-head">
        <text class="section-title">待处理邮件</text>
        <text class="section-note">{{ statusText }}</text>
      </view>

      <view v-if="errorMessage" class="email-alert">{{ errorMessage }}</view>
      <view v-else-if="isLoading" class="email-empty">正在从真实 API 加载待回复邮件...</view>
      <view v-else-if="!cards.length" class="email-empty">当前筛选下没有待处理邮件</view>

      <view v-else class="email-list">
        <view v-for="card in cards" :key="card.id" class="email-card" @click="openReply(card.id)">
          <view class="email-card-top">
            <view class="email-card-main">
              <view class="email-subject">{{ card.subject }}</view>
              <view class="email-meta">{{ card.customerName }} · {{ card.language }} · {{ card.customerGrade }} 级</view>
            </view>
            <text :class="['pool-tag', decisionClass(card.decision)]">{{ card.decisionLabel }}</text>
          </view>

          <view class="email-preview">{{ card.preview || '暂无邮件正文摘要。' }}</view>

          <view class="email-knowledge-hit">
            <view class="email-knowledge-icon">{{ card.decision === 'blocked' ? '!' : 'K' }}</view>
            <view class="email-card-main">
              <text class="email-row-title">{{ card.knowledgeSummary }}</text>
              <text class="email-row-note">
                相似度 {{ card.similarityText }} · {{ card.hardBlocks.length ? card.hardBlocks.join('、') : 'embedding ready' }}
              </text>
            </view>
            <text :class="['pool-tag', decisionClass(card.decision)]">
              {{ card.decision === 'blocked' ? 'blocked' : card.riskLevel }}
            </text>
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
import { emailRepliesService, filterEmailReplies, summarizeEmailReplies } from '../../services/emailReplies.js';
import '../../styles/home.css';
import '../../styles/leadPool.css';
import '../../styles/emailReplies.css';

const replies = ref([]);
const isLoading = ref(false);
const errorMessage = ref('');
const activeFilter = ref('all');
const bottomTabs = buildBottomTabs('email');
const filters = [
  { key: 'all', label: '全部' },
  { key: 'auto', label: '自动发送候选' },
  { key: 'manual', label: '人工确认' },
  { key: 'blocked', label: '硬拦截' },
];

const summary = computed(() => summarizeEmailReplies(replies.value));
const cards = computed(() => filterEmailReplies(replies.value, activeFilter.value));
const statusText = computed(() => (isLoading.value ? '加载中' : `${cards.value.length} 条按风险排序`));

onMounted(loadReplies);

async function loadReplies() {
  isLoading.value = true;
  errorMessage.value = '';
  try {
    const payload = await emailRepliesService.listEmailReplies({ limit: 100 });
    replies.value = payload.items;
  } catch (error) {
    replies.value = [];
    errorMessage.value = `邮件回复队列加载失败：${error.message || 'Unknown'}`;
  } finally {
    isLoading.value = false;
  }
}

function decisionClass(decision) {
  if (decision === 'auto_send_allowed') {
    return 'risk-low';
  }
  if (decision === 'blocked') {
    return 'pool-tag-red';
  }
  return 'pool-tag-amber';
}

function openReply(replyId) {
  if (!replyId || !globalThis.uni?.navigateTo) {
    return;
  }
  globalThis.uni.navigateTo({ url: `/pages/email-replies/detail?id=${encodeURIComponent(replyId)}` });
}

function openTab(tab) {
  navigateBottomTab(tab);
}
</script>
