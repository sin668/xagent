<template>
  <view class="customer-followups-page">
    <view class="status-bar">
      <text>9:41</text>
      <view class="status-icons">
        <text>5G</text>
        <text>Wi-Fi</text>
        <text>78%</text>
      </view>
    </view>

    <view class="nav-bar">
      <view class="nav-action" aria-label="返回" @click="goBack">‹</view>
      <view>
        <view class="nav-title">跟进记录</view>
        <view class="nav-subtitle">触达历史 · 客户反馈 · 下一步</view>
      </view>
      <view class="nav-action" aria-label="刷新" @click="loadPage">↻</view>
    </view>

    <scroll-view scroll-y class="customer-followups-content">
      <view v-if="errorMessage" class="followup-alert">{{ errorMessage }}</view>
      <view v-else-if="isLoading" class="followup-empty">正在从真实 API 加载客户跟进记录...</view>
      <template v-else>
        <section class="followup-panel">
          <view class="followup-card-top">
            <view>
              <view class="followup-customer-name">{{ customerView.name }}</view>
              <view class="followup-meta">
                {{ customerView.gradeLabel }} · {{ customerView.ownerText }} · {{ customerView.nextActionText }}
              </view>
            </view>
            <text :class="['followup-tag', customerView.canCreateOutreachDraft ? 'followup-tag-green' : 'followup-tag-red']">
              {{ customerView.doNotContactLabel }}
            </text>
          </view>
        </section>

        <view class="followup-section-head">
          <text class="followup-section-title">跟进状态</text>
          <text class="followup-section-note">不可自动发送</text>
        </view>
        <section class="followup-panel followup-stepper">
          <view class="followup-step-row">
            <view class="followup-step-dot followup-dot-green">✓</view>
            <view>
              <text class="followup-row-title">勿扰客户状态</text>
              <text class="followup-row-note">{{ customerView.doNotContactLabel }} · 触达前必须人工核验</text>
            </view>
          </view>
          <view class="followup-step-row">
            <view class="followup-step-dot followup-dot-amber">!</view>
            <view>
              <text class="followup-row-title">硬阻断影响</text>
              <text class="followup-row-note">{{ hardBlockTip }}</text>
            </view>
          </view>
        </section>

        <view class="followup-section-head">
          <text class="followup-section-title">触达与跟进时间线</text>
          <text class="followup-section-note">{{ timeline.length }} 条</text>
        </view>
        <section class="followup-panel followup-feed">
          <view v-for="item in timeline" :key="`${item.kind}-${item.id}`" class="followup-feed-item">
            <view :class="['followup-feed-icon', item.kind === 'outreach' ? 'followup-feed-icon-blue' : 'followup-feed-icon-green']">
              {{ item.kind === 'outreach' ? '触' : '跟' }}
            </view>
            <view class="followup-feed-main">
              <text class="followup-row-title">{{ item.title }}</text>
              <text class="followup-row-note">{{ item.note }}</text>
            </view>
          </view>
          <text v-if="!timeline.length" class="followup-row-note">暂无触达历史或跟进记录。</text>
        </section>

        <view class="followup-section-head">
          <text class="followup-section-title">新增跟进</text>
          <text class="followup-section-note">CRM 记录</text>
        </view>
        <section class="followup-panel followup-form">
          <view class="followup-field">
            <text class="followup-label">跟进方式</text>
            <input v-model="form.followupType" class="followup-input" placeholder="email / manual_call / internal_note" />
          </view>
          <view class="followup-field">
            <text class="followup-label">客户反馈</text>
            <textarea v-model="form.customerFeedback" class="followup-textarea" placeholder="记录客户反馈，不发送消息。" />
          </view>
          <view class="followup-field">
            <text class="followup-label">下一步动作</text>
            <input v-model="form.nextAction" class="followup-input" placeholder="例如：明天确认预算" />
          </view>
          <view class="followup-field">
            <text class="followup-label">下一次跟进时间</text>
            <input v-model="form.nextFollowupAt" class="followup-input" placeholder="2026-06-05T10:00:00+08:00" />
          </view>
          <view class="followup-switch-row">
            <label class="followup-check">
              <checkbox :checked="form.triggeredDnc" @click="form.triggeredDnc = !form.triggeredDnc" />
              <text>标记勿扰</text>
            </label>
            <label class="followup-check">
              <checkbox :checked="form.triggeredComplianceReview" @click="form.triggeredComplianceReview = !form.triggeredComplianceReview" />
              <text>触发合规复核</text>
            </label>
          </view>
          <text class="followup-row-note">
            勿扰客户不得再次进入触达队列；本页只保存人工跟进记录。
          </text>
        </section>
      </template>
    </scroll-view>

    <view class="followup-action-bar followup-action-bar-above-safe-area">
      <button class="followup-button followup-button-secondary" @click="goBack">返回</button>
      <button class="followup-button followup-button-primary" @click="submitFollowup">保存跟进记录</button>
    </view>
  </view>
</template>

<script setup>
import { onLoad as onUniLoad } from '@dcloudio/uni-app';
import { computed, reactive, ref } from 'vue';

import { getCustomerDetailViewModel, mapCustomerDetail, customersService } from '../../services/customers.js';
import {
  buildFollowupTimeline,
  customerFollowupsService,
  getFollowupHardBlockTip,
} from '../../services/customerFollowups.js';
import '../../styles/home.css';
import '../../styles/customerFollowups.css';

const customerId = ref('');
const customerDetail = ref(mapCustomerDetail({}));
const followups = ref([]);
const isLoading = ref(false);
const errorMessage = ref('');

const form = reactive({
  ownerId: 'mobile-user',
  team: 'customer_service',
  followupType: 'internal_note',
  content: '人工跟进记录',
  customerFeedback: '',
  nextAction: '',
  nextFollowupAt: '',
  triggeredDnc: false,
  triggeredComplianceReview: false,
  createdBy: 'mobile-user',
});

const customerView = computed(() => getCustomerDetailViewModel(customerDetail.value));
const timeline = computed(() => buildFollowupTimeline({
  followups: followups.value,
  outreachHistory: customerDetail.value.outreachHistory,
}));
const hardBlockTip = computed(() => getFollowupHardBlockTip({
  triggeredDnc: form.triggeredDnc || customerDetail.value.doNotContact?.enabled,
  triggeredComplianceReview: form.triggeredComplianceReview,
}));

onUniLoad((options = {}) => {
  initializeFromOptions(options);
});

if (globalThis.location?.search) {
  const params = new URLSearchParams(globalThis.location.search);
  initializeFromOptions({
    id: params.get('id') || '',
    customerId: params.get('customerId') || '',
  });
}

function initializeFromOptions(options = {}) {
  const routeCustomerId = options.id || options.customerId || '';
  if (!routeCustomerId || routeCustomerId === customerId.value) {
    return;
  }
  customerId.value = routeCustomerId;
  loadPage();
}

async function loadPage() {
  if (!customerId.value) {
    errorMessage.value = '缺少客户 ID，无法加载客户跟进记录。';
    return;
  }
  isLoading.value = true;
  errorMessage.value = '';
  try {
    const [detailPayload, followupPayload] = await Promise.all([
      customersService.getCustomerDetail(customerId.value),
      customerFollowupsService.listFollowups(customerId.value),
    ]);
    customerDetail.value = detailPayload;
    followups.value = followupPayload;
  } catch (error) {
    errorMessage.value = `客户跟进记录加载失败：${error.message || 'Unknown'}`;
  } finally {
    isLoading.value = false;
  }
}

async function submitFollowup() {
  if (!customerId.value) {
    errorMessage.value = '缺少客户 ID，无法保存跟进记录。';
    return;
  }
  try {
    const created = await customerFollowupsService.createFollowup(customerId.value, {
      customerId: customerId.value,
      ...form,
    });
    followups.value = [created, ...followups.value];
  } catch (error) {
    errorMessage.value = `保存跟进记录失败：${error.message || 'Unknown'}`;
  }
}

function goBack() {
  if (globalThis.uni?.navigateBack) {
    globalThis.uni.navigateBack();
    return;
  }
  if (globalThis.uni?.redirectTo) {
    globalThis.uni.redirectTo({ url: `/pages/customers/detail?id=${encodeURIComponent(customerId.value)}` });
  }
}
</script>
