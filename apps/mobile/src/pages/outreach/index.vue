<template>
  <view class="lead-detail-page">
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
      <view class="nav-title">触达助手</view>
      <view class="nav-action" aria-label="语言">RU</view>
    </view>

    <scroll-view scroll-y class="detail-content">
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
        <label class="confirm-row">
          <checkbox :checked="humanConfirmed" @click="humanConfirmed = !humanConfirmed" />
          <text>已人工审核，确认后仅记录人工发送结果</text>
        </label>
      </section>

      <view class="detail-section-head">
        <text class="detail-section-title">触达记录</text>
        <text class="detail-section-note">人工登记</text>
      </view>
      <section class="detail-panel record-form">
        <view class="record-field">
          <text class="record-label">回复状态</text>
          <picker :range="statusLabels" :value="statusIndex" @change="handleStatusChange">
            <text class="record-input">{{ statusOptions[statusIndex].label }}</text>
          </picker>
        </view>
        <view class="record-field">
          <text class="record-label">负责人</text>
          <input v-model="owner" class="record-input" />
        </view>
        <view class="record-field">
          <text class="record-label">下一步动作</text>
          <input v-model="nextAction" class="record-input" />
        </view>
        <view class="record-field">
          <text class="record-label">结果摘要</text>
          <textarea v-model="summary" class="record-input" auto-height />
        </view>
        <view v-if="recordDecision.reason" class="blocked-note">{{ recordDecision.reason }}</view>
      </section>
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

    <view class="action-bar action-bar-above-tabbar">
      <button class="detail-button detail-button-secondary">编辑</button>
      <button
        :class="['detail-button', canRecord ? 'detail-button-primary' : 'detail-button-disabled']"
        :disabled="!canRecord"
        @click="recordSent"
      >
        {{ sentRecord ? '已记录' : recordButtonLabel }}
      </button>
    </view>
  </view>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';

import { mapOutreachDraft } from '../../services/apiAdapters.js';
import { apiClient } from '../../services/apiClient.js';
import { buildBottomTabs, navigateBottomTab } from '../../services/bottomTabs.js';
import {
  buildOutreachDraftViewModel,
  canRecordManualSend,
  createManualSendRecord,
} from '../../services/outreachDraft.js';
import {
  buildOutreachRecordPayload,
  canCreateOutreachRecord,
  getOutreachStatusOptions,
  isBackendCustomerId,
} from '../../services/outreachRecord.js';
import '../../styles/home.css';
import '../../styles/leadPool.css';
import '../../styles/leadDetail.css';
import '../../styles/outreachDraft.css';
import '../../styles/outreachRecord.css';

const humanConfirmed = ref(false);
const sentRecord = ref(null);
const statusOptions = getOutreachStatusOptions();
const statusLabels = statusOptions.map((option) => option.label);
const statusIndex = ref(0);
const owner = ref('当前用户');
const nextAction = ref('等待回复');
const summary = ref('已人工发送俄语触达草稿。');
const bottomTabs = buildBottomTabs('ai');
const emptyLead = {
  id: '',
  customerName: 'Unknown',
  grade: 'Unknown',
  channel: 'Unknown',
  riskLevel: 'Unknown',
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
const draft = computed(() =>
  buildOutreachDraftViewModel({
    lead: lead.value,
    draft: draftState.value,
  }),
);
const passedCount = computed(() => draft.value.complianceChecks.filter((check) => check.passed).length);
const recordDecision = computed(() =>
  canCreateOutreachRecord({
    lead: lead.value,
    status: statusOptions[statusIndex.value].value,
    manualConfirmed: humanConfirmed.value,
  }),
);
const canRecord = computed(
  () => canRecordManualSend(draft.value, { humanConfirmed: humanConfirmed.value }) && recordDecision.value.allowed,
);
const recordButtonLabel = computed(() => `记录${statusOptions[statusIndex.value].label}`);

function getCurrentLeadId() {
  return globalThis.getCurrentPages?.()?.at(-1)?.options?.leadId || lead.value.id;
}

onMounted(async () => {
  const leadId = getCurrentLeadId();
  lead.value = {
    ...emptyLead,
    id: leadId,
  };
  try {
    const payload = await apiClient.get(`/outreach-drafts/${encodeURIComponent(leadId)}`);
    draftState.value = mapOutreachDraft(payload);
    lead.value = {
      ...lead.value,
      id: leadId,
      customerName: payload.customer_name || lead.value.customerName,
    };
  } catch (_error) {
    draftState.value = emptyDraft;
  }
});

async function recordSent() {
  if (!canRecord.value) {
    return;
  }

  const backendCustomerId = draft.value.leadId;
  const draftRecord = createManualSendRecord(draft.value, {
    humanConfirmed: humanConfirmed.value,
    sender: owner.value,
    channel: draft.value.channel,
  });
  sentRecord.value = {
    ...draftRecord,
    payload: buildOutreachRecordPayload({
      channel: draft.value.channel,
      status: statusOptions[statusIndex.value].value,
      sender: owner.value,
      owner: owner.value,
      summary: summary.value,
      nextAction: nextAction.value,
      manualConfirmed: humanConfirmed.value,
      doNotContactReason: statusOptions[statusIndex.value].value === 'rejected' ? '客户明确拒绝继续联系' : null,
      scriptVersion: draft.value.versionLabel,
    }),
  };

  if (!isBackendCustomerId(backendCustomerId)) {
    sentRecord.value = {
      ...sentRecord.value,
      syncStatus: 'local_only',
    };
    return;
  }

  try {
    await apiClient.post(`/outreach-drafts/${encodeURIComponent(backendCustomerId)}/record-manual-send`, {
      human_confirmed: humanConfirmed.value,
      sender: owner.value,
      channel: sentRecord.value.payload.channel,
    });
  } catch (_error) {
    try {
      await apiClient.post(`/customers/${encodeURIComponent(backendCustomerId)}/outreach-records`, sentRecord.value.payload);
    } catch (_fallbackError) {
      sentRecord.value = {
        ...sentRecord.value,
        syncStatus: 'pending',
      };
    }
  }
}

function handleStatusChange(event) {
  statusIndex.value = Number(event.detail.value);
  if (statusOptions[statusIndex.value].value === 'rejected') {
    nextAction.value = '标记勿扰';
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
