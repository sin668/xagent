<template>
  <view class="outreach-send-page">
    <view class="status-bar">
      <text>9:41</text>
      <view class="status-icons">
        <text>5G</text>
        <text>Wi-Fi</text>
        <text>78%</text>
      </view>
    </view>

    <view class="nav-bar">
      <view class="nav-action" aria-label="返回" @click="cancelSend">‹</view>
      <view>
        <view class="nav-title">邮件发送</view>
        <view class="nav-subtitle">人工确认 · 使用后端邮件发送服务</view>
      </view>
      <view class="nav-action" aria-label="邮件">✉</view>
    </view>

    <scroll-view scroll-y class="outreach-send-content">
      <section class="outreach-send-panel outreach-send-recipient">
        <view>
          <text class="outreach-send-kicker">TO</text>
          <text class="outreach-send-customer">{{ form.customerName || 'Unknown customer' }}</text>
        </view>
        <text class="outreach-send-status">{{ sendStatusText }}</text>
      </section>

      <section class="outreach-send-panel outreach-send-form">
        <view class="outreach-send-field">
          <text class="outreach-send-label">收件人</text>
          <input v-model="form.toEmail" class="outreach-send-input" placeholder="customer@example.ru" />
        </view>
        <view class="outreach-send-field">
          <text class="outreach-send-label">主题</text>
          <input v-model="form.subject" class="outreach-send-input" placeholder="邮件主题" />
        </view>
        <view class="outreach-send-field">
          <text class="outreach-send-label">正文</text>
          <textarea v-model="form.body" class="outreach-send-textarea" placeholder="邮件正文" />
        </view>
      </section>

      <section v-if="errorMessage" class="outreach-send-alert">
        <text>{{ errorMessage }}</text>
      </section>
      <section v-if="sendResult" class="outreach-send-success">
        <text>发送完成：{{ sendResult.provider }} · {{ sendResult.provider_message_id || sendResult.providerMessageId || '无消息ID' }}</text>
      </section>
    </scroll-view>

    <view class="followup-action-bar followup-action-bar-above-safe-area">
      <button class="followup-button followup-button-secondary" @click="cancelSend">取消</button>
      <button
        :class="['followup-button', canSend ? 'followup-button-primary' : 'followup-button-disabled']"
        :disabled="!canSend"
        @click="sendEmail"
      >
        {{ sending ? '发送中' : '发送' }}
      </button>
    </view>
  </view>
</template>

<script setup>
import { onLoad as onUniLoad } from '@dcloudio/uni-app';
import { computed, reactive, ref } from 'vue';

import { mapOutreachDraft } from '../../services/apiAdapters.js';
import { apiClient } from '../../services/apiClient.js';
import { customersService } from '../../services/customers.js';
import {
  createOutreachEmailService,
  firstEmailContact,
} from '../../services/outreachDraft.js';
import '../../styles/home.css';
import '../../styles/customerFollowups.css';
import '../../styles/outreachDraft.css';

const emailService = createOutreachEmailService({ client: apiClient });
const customerId = ref('');
const sending = ref(false);
const errorMessage = ref('');
const sendResult = ref(null);
const form = reactive({
  customerName: '',
  toEmail: '',
  subject: '',
  body: '',
});

const canSend = computed(() =>
  Boolean(customerId.value && form.toEmail.trim() && form.subject.trim() && form.body.trim() && !sending.value),
);
const sendStatusText = computed(() => (sendResult.value ? '已发送' : '待发送'));

onUniLoad((options = {}) => {
  initializeFromOptions(options);
});

if (globalThis.location?.search) {
  const params = new URLSearchParams(globalThis.location.search);
  initializeFromOptions({
    customerId: params.get('customerId') || '',
  });
}

async function initializeFromOptions(options = {}) {
  const routeCustomerId = options.customerId || '';
  if (!routeCustomerId || routeCustomerId === customerId.value) {
    applyDraft(globalThis.__xagentOutreachEmailDraft || {});
    return;
  }
  customerId.value = routeCustomerId;
  applyDraft(globalThis.__xagentOutreachEmailDraft || {});
  if (!form.toEmail || !form.subject || !form.body) {
    await loadDraftFallback(routeCustomerId);
  }
}

function applyDraft(draft = {}) {
  if (draft.customerId) {
    customerId.value = draft.customerId;
  }
  form.customerName = draft.customerName || form.customerName;
  form.toEmail = draft.toEmail || form.toEmail;
  form.subject = draft.subject || form.subject;
  form.body = draft.body || form.body;
}

async function loadDraftFallback(id) {
  try {
    const [draftPayload, customerDetail, stagingDetail] = await Promise.all([
      apiClient.get(`/outreach-drafts/${encodeURIComponent(id)}`),
      customersService.getCustomerDetail(id).catch(() => null),
      apiClient.get(`/staging-leads/${encodeURIComponent(id)}`).catch(() => null),
    ]);
    const mappedDraft = mapOutreachDraft(draftPayload);
    const stagingLead = stagingDetail?.staging_lead || stagingDetail || {};
    const emailContact = firstEmailContact([
      ...(customerDetail?.contacts || []),
      ...(stagingLead.contacts_json || stagingLead.contacts || []),
    ]);
    form.customerName = draftPayload.customer_name || customerDetail?.profile?.name || stagingLead.customer_name || form.customerName;
    form.toEmail = emailContact?.value || form.toEmail;
    form.subject = mappedDraft.subject || form.subject;
    form.body = mappedDraft.body || form.body;
  } catch (error) {
    errorMessage.value = `邮件草稿加载失败：${error.message || 'Unknown'}`;
  }
}

async function sendEmail() {
  if (!canSend.value) {
    errorMessage.value = '请补齐收件人、主题和正文。';
    return;
  }
  sending.value = true;
  errorMessage.value = '';
  try {
    sendResult.value = await emailService.sendEmail(customerId.value, {
      toEmail: form.toEmail,
      subject: form.subject,
      body: form.body,
      sender: '当前用户',
    });
    if (globalThis.uni?.showToast) {
      globalThis.uni.showToast({ title: '邮件已发送', icon: 'none' });
    }
  } catch (error) {
    errorMessage.value = `邮件发送失败：${error.message || 'Unknown'}`;
  } finally {
    sending.value = false;
  }
}

function cancelSend() {
  if (globalThis.uni?.navigateBack) {
    globalThis.uni.navigateBack();
  }
}
</script>
