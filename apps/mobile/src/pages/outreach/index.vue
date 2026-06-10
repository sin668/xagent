<template>
  <view class="lead-detail-page outreach-assistant-page">
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
        <view class="nav-title">触达助手</view>
        <view class="nav-subtitle">AI 俄语草稿 · 人工邮件发送</view>
      </view>
      <view class="nav-action" aria-label="语言">RU</view>
    </view>

    <scroll-view scroll-y class="detail-content outreach-assistant-content">
      <section class="detail-panel">
        <view class="pool-card-top">
          <view>
            <view class="pool-lead-name">{{ draft.customerName }}</view>
            <view class="pool-lead-meta">{{ draft.gradeLabel }} · {{ draft.channel }} · {{ draft.riskLevel }}</view>
          </view>
          <text class="pool-tag pool-tag-blue">人工发送</text>
        </view>
      </section>

      <view class="detail-section-head">
        <text class="detail-section-title">AI 俄语草稿</text>
        <text class="detail-section-note">{{ draft.versionLabel }}</text>
      </view>
      <section class="draft-panel">
        <text class="draft-subject-label">SUBJECT</text>
        <text class="draft-subject">{{ draft.subject }}</text>
        <text class="draft-body">{{ draft.body }}</text>
        <text class="draft-refusal">{{ draft.refusalPath }}</text>
        <view class="detail-tag-row">
          <text v-for="tip in draft.riskTips" :key="tip" class="pool-tag pool-tag-amber">{{ tip }}</text>
        </view>
      </section>

      <view class="detail-section-head">
        <text class="detail-section-title">合规检查</text>
        <text class="detail-section-note">{{ passedCount }}/{{ draft.complianceChecks.length }} 通过</text>
      </view>
      <section class="check-list">
        <view v-for="check in draft.complianceChecks" :key="check.key" class="check-row">
          <text class="check-label">{{ check.label }}</text>
          <text :class="['pool-tag', check.passed ? 'risk-low' : 'pool-tag-red']">
            {{ check.passed ? '通过' : '阻断' }}
          </text>
        </view>
      </section>

      <section v-if="draft.blockReasons.length" class="blocked-note">
        <text>阻断原因：{{ draft.blockReasons.join('；') }}</text>
      </section>

      <view class="detail-section-head">
        <text class="detail-section-title">AI 审计</text>
        <text class="detail-section-note">{{ draft.generatedAt }}</text>
      </view>
      <section class="detail-panel">
        <view class="audit-grid">
          <view class="audit-item">
            <text class="audit-label">模型</text>
            <text class="audit-value">{{ draft.audit.model || 'Unknown' }}</text>
          </view>
          <view class="audit-item">
            <text class="audit-label">Prompt</text>
            <text class="audit-value">{{ draft.audit.promptVersion || 'Unknown' }}</text>
          </view>
          <view class="audit-item">
            <text class="audit-label">输入保存</text>
            <text class="audit-value">{{ draft.audit.inputSaved ? '是' : '否' }}</text>
          </view>
          <view class="audit-item">
            <text class="audit-label">输出保存</text>
            <text class="audit-value">{{ draft.audit.outputSaved ? '是' : '否' }}</text>
          </view>
        </view>
      </section>
    </scroll-view>

    <view class="followup-action-bar followup-action-bar-above-safe-area">
      <button class="followup-button followup-button-secondary" @click="goBack">返回</button>
      <button
        :class="['followup-button', draft.canRecordSent ? 'followup-button-primary' : 'followup-button-disabled']"
        :disabled="!draft.canRecordSent"
        @click="openEmailSend"
      >
        编辑
      </button>
    </view>
  </view>
</template>

<script setup>
import { onLoad as onUniLoad } from '@dcloudio/uni-app';
import { computed, ref } from 'vue';

import { mapOutreachDraft } from '../../services/apiAdapters.js';
import { apiClient } from '../../services/apiClient.js';
import { customersService } from '../../services/customers.js';
import { buildOutreachDraftViewModel, firstEmailContact } from '../../services/outreachDraft.js';
import '../../styles/home.css';
import '../../styles/leadPool.css';
import '../../styles/leadDetail.css';
import '../../styles/outreachDraft.css';
import '../../styles/customerFollowups.css';

const emptyLead = {
  id: '',
  customerName: 'Unknown',
  grade: 'Unknown',
  channel: 'Email',
  riskLevel: 'Low',
  doNotContact: false,
};
const emptyDraft = {
  id: '',
  templateId: '',
  templateStatus: '待业务审核',
  version: '',
  generatedAt: '',
  subject: '',
  body: '',
  refusalPath: '',
  riskTips: [],
  audit: {
    model: 'Unknown',
    promptVersion: 'Unknown',
    inputSaved: false,
    outputSaved: false,
  },
};

const lead = ref(emptyLead);
const draftState = ref(emptyDraft);
const recipientEmail = ref('');
const customerId = ref('');
const draft = computed(() =>
  buildOutreachDraftViewModel({
    lead: lead.value,
    draft: draftState.value,
  }),
);
const passedCount = computed(() => draft.value.complianceChecks.filter((check) => check.passed).length);

onUniLoad((options = {}) => {
  initializeFromOptions(options);
});

if (globalThis.location?.search) {
  const params = new URLSearchParams(globalThis.location.search);
  initializeFromOptions({
    leadId: params.get('leadId') || '',
    customerId: params.get('customerId') || '',
  });
}

async function initializeFromOptions(options = {}) {
  const routeId = options.customerId || options.leadId || '';
  if (!routeId || routeId === customerId.value) {
    return;
  }
  customerId.value = routeId;
  lead.value = {
    ...emptyLead,
    id: routeId,
  };
  await loadDraft(routeId);
}

async function loadDraft(id) {
  try {
    const [draftPayload, customerDetail, stagingDetail] = await Promise.all([
      apiClient.get(`/outreach-drafts/${encodeURIComponent(id)}`),
      customersService.getCustomerDetail(id).catch(() => null),
      apiClient.get(`/staging-leads/${encodeURIComponent(id)}`).catch(() => null),
    ]);
    const stagingLead = stagingDetail?.staging_lead || stagingDetail || {};
    const emailContact = firstEmailContact([
      ...(customerDetail?.contacts || []),
      ...(stagingLead.contacts_json || stagingLead.contacts || []),
    ]);
    recipientEmail.value = emailContact?.value || '';
    draftState.value = mapOutreachDraft(draftPayload);
    lead.value = {
      ...lead.value,
      id,
      customerName: draftPayload.customer_name || customerDetail?.profile?.name || stagingLead.customer_name || lead.value.customerName,
      grade: customerDetail?.profile?.grade || stagingLead.recommended_grade || lead.value.grade,
      channel: 'Email',
      riskLevel: customerDetail?.sources?.[0]?.riskLevel || stagingLead.source_risk_level || lead.value.riskLevel,
      doNotContact: Boolean(customerDetail?.doNotContact?.enabled || stagingDetail?.has_do_not_contact_match),
    };
  } catch (_error) {
    draftState.value = emptyDraft;
  }
}

function openEmailSend() {
  const payload = {
    customerId: customerId.value || draft.value.leadId,
    toEmail: recipientEmail.value,
    subject: draft.value.subject,
    body: draft.value.body,
    customerName: draft.value.customerName,
  };
  globalThis.__xagentOutreachEmailDraft = payload;
  if (globalThis.uni?.navigateTo) {
    const query = new URLSearchParams({
      customerId: payload.customerId || '',
    }).toString();
    globalThis.uni.navigateTo({ url: `/pages/outreach/send?${query}` });
  }
}

function goBack() {
  if (globalThis.uni?.navigateBack) {
    globalThis.uni.navigateBack();
  }
}
</script>
