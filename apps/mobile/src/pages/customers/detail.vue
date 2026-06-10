<template>
  <view class="customer-detail-page">
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
        <view class="nav-title">客户详情</view>
        <view class="nav-subtitle">完善线索 -> 客户档案</view>
      </view>
      <view class="nav-action" aria-label="刷新" @click="loadCustomer">↻</view>
    </view>

    <scroll-view scroll-y class="customer-detail-content">
      <view v-if="errorMessage" class="customer-detail-alert">{{ errorMessage }}</view>
      <view v-else-if="isLoading" class="customer-detail-empty">正在从真实 API 加载客户详情...</view>
      <template v-else>
        <section class="customer-detail-profile">
          <view class="customer-detail-avatar">{{ initials }}</view>
          <view class="customer-detail-main">
            <view class="customer-detail-name">{{ viewModel.name }}</view>
            <view class="customer-detail-meta">{{ viewModel.locationText }} · {{ viewModel.customerTypeText }}</view>
            <view class="customer-detail-tags">
              <text class="customer-detail-tag customer-detail-tag-blue">{{ viewModel.gradeLabel }}</text>
              <text class="customer-detail-tag customer-detail-tag-dark">{{ viewModel.ownerText }}</text>
              <text :class="['customer-detail-tag', viewModel.canCreateOutreachDraft ? 'customer-detail-tag-green' : 'customer-detail-tag-red']">
                {{ viewModel.doNotContactLabel }}
              </text>
            </view>
          </view>
        </section>

        <view class="customer-detail-section-head">
          <text class="customer-detail-section-title">客户画像</text>
          <text class="customer-detail-section-note">{{ viewModel.completenessText }}</text>
        </view>
        <section class="customer-detail-card customer-detail-grid">
          <view class="customer-detail-cell">
            <text class="customer-detail-label">客户类型</text>
            <text class="customer-detail-value">{{ viewModel.customerTypeText }}</text>
          </view>
          <view class="customer-detail-cell">
            <text class="customer-detail-label">客户状态</text>
            <text class="customer-detail-value">{{ viewModel.statusText }}</text>
          </view>
          <view class="customer-detail-cell">
            <text class="customer-detail-label">负责人团队</text>
            <text class="customer-detail-value">{{ viewModel.ownerTeamText }}</text>
          </view>
          <view class="customer-detail-cell">
            <text class="customer-detail-label">下一步动作</text>
            <text class="customer-detail-value">{{ viewModel.nextActionText }}</text>
          </view>
        </section>

        <view class="customer-detail-section-head">
          <text class="customer-detail-section-title">待补全字段</text>
          <text class="customer-detail-section-note">{{ viewModel.pendingFieldLabels.length }} 项</text>
        </view>
        <section class="customer-detail-card">
          <view v-if="pendingFieldItems.length" class="customer-detail-pending-list">
            <view v-for="item in pendingFieldItems" :key="item.fieldName" class="customer-detail-pending-item">
              <text class="customer-detail-tag customer-detail-tag-amber">{{ item.label }}</text>
              <button class="customer-detail-inline-button" @click="openManualSupplement(item)">人工补录</button>
            </view>
            <view v-if="manualSupplementField" class="customer-detail-manual-form">
              <view class="customer-detail-manual-head">
                <text class="customer-detail-row-title">补录 {{ manualSupplementFieldLabel }}</text>
                <text class="customer-detail-tag customer-detail-tag-blue">人工记录</text>
              </view>
              <input v-model="manualSupplementValue" class="customer-detail-input" placeholder="补录内容" />
              <input v-model="manualSupplementEvidence" class="customer-detail-input" placeholder="证据说明，如官网公开页、人工电话确认" />
              <button class="customer-detail-submit-button" @click="submitManualSupplement">提交补录</button>
            </view>
          </view>
          <text v-else class="customer-detail-copy">暂无待补全字段。</text>
        </section>

        <view class="customer-detail-section-head">
          <text class="customer-detail-section-title">联系方式</text>
          <text class="customer-detail-section-note">{{ viewModel.contactCountText }}</text>
        </view>
        <section class="customer-detail-card customer-detail-list">
          <view v-for="contact in viewModel.contacts" :key="contact.id" class="customer-detail-evidence-item">
            <view class="customer-detail-evidence-head">
              <text class="customer-detail-row-title">{{ contact.displayText }}</text>
              <text class="customer-detail-tag customer-detail-tag-green">{{ contact.isPrimary ? '主联系' : '联系' }}</text>
            </view>
            <view class="customer-detail-evidence-body">
              <text class="customer-detail-row-note">{{ contact.evidenceText }}</text>
            </view>
          </view>
          <text v-if="!viewModel.contacts.length" class="customer-detail-copy">联系方式待补全。</text>
        </section>

        <view class="customer-detail-section-head">
          <text class="customer-detail-section-title">来源证据</text>
          <text class="customer-detail-section-note">{{ viewModel.sourceCountText }}</text>
        </view>
        <section class="customer-detail-card customer-detail-list">
          <view v-for="source in viewModel.sources" :key="source.id" class="customer-detail-evidence-item">
            <view class="customer-detail-evidence-head">
              <text class="customer-detail-row-title">{{ source.displayText }}</text>
              <text class="customer-detail-tag customer-detail-tag-blue">{{ source.riskLevel }}</text>
            </view>
            <view class="customer-detail-evidence-body">
              <text class="customer-detail-row-note">{{ source.evidenceText }}</text>
              <text class="customer-detail-link">{{ source.sourceUrl }}</text>
            </view>
          </view>
          <text v-if="!viewModel.sources.length" class="customer-detail-copy">来源证据待补全。</text>
        </section>

        <view class="customer-detail-section-head">
          <text class="customer-detail-section-title">意向车型</text>
          <text class="customer-detail-section-note">{{ viewModel.vehicleIntentCountText }}</text>
        </view>
        <section class="customer-detail-card customer-detail-list">
          <view v-for="intent in viewModel.vehicleIntents" :key="intent.id" class="customer-detail-row">
            <view>
              <text class="customer-detail-row-title">{{ intent.displayText }}</text>
              <text class="customer-detail-row-note">{{ intent.evidenceText }}</text>
            </view>
            <text class="customer-detail-tag customer-detail-tag-green">{{ intent.status }}</text>
          </view>
          <text v-if="!viewModel.vehicleIntents.length" class="customer-detail-copy">意向车型待补全。</text>
        </section>

        <view class="customer-detail-section-head">
          <text class="customer-detail-section-title">触达历史</text>
          <text class="customer-detail-section-note">{{ viewModel.outreachCountText }}</text>
        </view>
        <section class="customer-detail-card customer-detail-timeline">
          <view v-for="record in viewModel.outreachHistory" :key="record.id" class="customer-detail-timeline-item">
            <view class="customer-detail-dot"></view>
            <view>
              <text class="customer-detail-row-title">{{ record.title }}</text>
              <text class="customer-detail-row-note">{{ record.detailText }}</text>
            </view>
          </view>
          <text v-if="!viewModel.outreachHistory.length" class="customer-detail-copy">暂无触达历史，后续仅支持人工记录。</text>
        </section>

        <view class="customer-detail-section-head">
          <text class="customer-detail-section-title">跟进记录</text>
          <text class="customer-detail-section-note">{{ viewModel.followupCountText }}</text>
        </view>
        <section class="customer-detail-card customer-detail-timeline">
          <view v-for="record in viewModel.followups" :key="record.id" class="customer-detail-timeline-item">
            <view class="customer-detail-dot customer-detail-dot-green"></view>
            <view>
              <text class="customer-detail-row-title">{{ record.title }}</text>
              <text class="customer-detail-row-note">{{ record.detailText }}</text>
            </view>
          </view>
          <text v-if="!viewModel.followups.length" class="customer-detail-copy">暂无跟进记录。</text>
        </section>

        <view class="customer-detail-section-head">
          <text class="customer-detail-section-title">合规状态</text>
          <text class="customer-detail-section-note">{{ viewModel.complianceLabel }}</text>
        </view>
        <section class="customer-detail-card">
          <text class="customer-detail-copy">勿扰客户状态必须在触达前人工核验。</text>
          <view class="customer-detail-chip-row">
            <text class="customer-detail-tag customer-detail-tag-amber">{{ viewModel.complianceLabel }}</text>
            <text class="customer-detail-tag customer-detail-tag-red">{{ viewModel.doNotContactLabel }}</text>
          </view>
          <text class="customer-detail-copy">
            {{ viewModel.complianceReason || viewModel.doNotContactReason || 'C 级报价、合同、付款、物流、清关、交付周期前必须合规复核。触达仍为人工记录。' }}
          </text>
        </section>
      </template>
    </scroll-view>

    <view class="customer-detail-action-bar customer-detail-action-bar-above-safe-area">
      <button class="customer-detail-button customer-detail-button-secondary" @click="goBack">返回客户池</button>
      <button
        :class="['customer-detail-button', customerId ? 'customer-detail-button-primary' : 'customer-detail-button-disabled']"
        :disabled="!customerId"
        @click="openFollowups"
      >
        人工记录跟进
      </button>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue';
import { onLoad as onUniLoad } from '@dcloudio/uni-app';

import { customersService, getCustomerDetailViewModel, mapCustomerDetail } from '../../services/customers.js';
import { customerFollowupsService } from '../../services/customerFollowups.js';
import '../../styles/home.css';
import '../../styles/customerDetail.css';

const fallbackDetail = mapCustomerDetail({});
const detail = ref(fallbackDetail);
const isLoading = ref(false);
const errorMessage = ref('');
const customerId = ref('');
const manualSupplementField = ref('');
const manualSupplementValue = ref('');
const manualSupplementEvidence = ref('');

const viewModel = computed(() => getCustomerDetailViewModel(detail.value));
const pendingFieldItems = computed(() =>
  (detail.value.pendingFields || []).map((field) => ({
    fieldName: String(field || '').trim(),
    label: `${String(field || '').trim()} 待补全`,
  })).filter((item) => item.fieldName),
);
const manualSupplementFieldLabel = computed(() =>
  pendingFieldItems.value.find((item) => item.fieldName === manualSupplementField.value)?.label || manualSupplementField.value,
);
const initials = computed(() => {
  const name = viewModel.value.name || '客户';
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join('').toUpperCase() || '客户';
});

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
  loadCustomer();
}

async function loadCustomer() {
  if (!customerId.value) {
    errorMessage.value = '缺少客户 ID，无法加载客户详情。';
    return;
  }
  isLoading.value = true;
  errorMessage.value = '';
  try {
    detail.value = await customersService.getCustomerDetail(customerId.value);
  } catch (error) {
    detail.value = fallbackDetail;
    errorMessage.value = `客户详情加载失败：${error.message || 'Unknown'}`;
  } finally {
    isLoading.value = false;
  }
}

function openManualSupplement(item) {
  manualSupplementField.value = item.fieldName;
  manualSupplementValue.value = '';
  manualSupplementEvidence.value = '';
}

function notify(message) {
  if (globalThis.uni?.showToast) {
    globalThis.uni.showToast({ title: message, icon: 'none' });
  }
}

async function submitManualSupplement() {
  const fieldName = manualSupplementField.value.trim();
  const fieldValue = manualSupplementValue.value.trim();
  const evidence = manualSupplementEvidence.value.trim();
  if (!customerId.value || !fieldName || !fieldValue || !evidence) {
    notify('请补齐字段、内容和证据');
    return;
  }

  try {
    const created = await customerFollowupsService.createFollowup(customerId.value, {
      customerId: customerId.value,
      ownerId: 'mobile-user',
      team: 'customer_service',
      followupType: 'manual_supplement',
      content: `人工补录 ${fieldName}：${fieldValue}`,
      customerFeedback: evidence,
      nextAction: `已补录 ${fieldName}`,
      createdBy: 'mobile-user',
    });
    detail.value = {
      ...detail.value,
      followups: [created, ...(detail.value.followups || [])],
    };
    manualSupplementField.value = '';
    manualSupplementValue.value = '';
    manualSupplementEvidence.value = '';
    notify('已保存人工补录');
  } catch (_error) {
    notify('人工补录失败');
  }
}

function goBack() {
  if (globalThis.uni?.navigateBack) {
    globalThis.uni.navigateBack();
    return;
  }
  if (globalThis.uni?.redirectTo) {
    globalThis.uni.redirectTo({ url: '/pages/customers/index' });
  }
}

function openFollowups() {
  if (!customerId.value || !globalThis.uni?.navigateTo) {
    return;
  }
  globalThis.uni.navigateTo({ url: `/pages/customers/followups?id=${encodeURIComponent(customerId.value)}` });
}
</script>
