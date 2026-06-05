<template>
  <view class="email-reply-detail-page">
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
        <view class="nav-title">回复审核</view>
        <view class="nav-subtitle">AI 建议与最终发送分开审计</view>
      </view>
      <view class="nav-action" aria-label="刷新" @click="loadDetail">RU</view>
    </view>

    <scroll-view scroll-y class="email-reply-detail-content">
      <view v-if="errorMessage" class="email-alert">{{ errorMessage }}</view>
      <view v-else-if="isLoading" class="email-empty">正在从真实 API 加载邮件回复详情...</view>

      <template v-else>
        <section class="email-panel">
          <view class="email-card-top">
            <view class="email-card-main">
              <view class="email-subject">{{ detail.customerName }}</view>
              <view class="email-meta">{{ detail.customerGrade }} 级 · {{ detail.language }} · thread {{ detail.threadId || 'Unknown' }}</view>
            </view>
            <text :class="['pool-tag', decisionClass(detail.autoSendCheck.decision)]">
              {{ detail.decisionLabel }}
            </text>
          </view>
        </section>

        <view class="section-head">
          <text class="section-title">客户来信</text>
          <text class="section-note">{{ detail.language }}</text>
        </view>
        <section class="email-card">
          <text class="email-subject">{{ detail.subject }}</text>
          <view class="email-preview">{{ detail.inboundBody || '暂无来信正文。' }}</view>
        </section>

        <view class="section-head">
          <text class="section-title">自动发送判断</text>
          <text class="section-note">{{ detail.autoSendCheck.allowAutoSend ? '准入' : '硬拦截/人工' }}</text>
        </view>
        <section :class="['email-decision-band', detail.autoSendCheck.allowAutoSend ? '' : 'email-decision-band-blocked']">
          <view class="email-rule-grid">
            <view class="email-rule">
              <text class="email-rule-icon">￥</text>
              <text class="email-rule-title">价格/付款</text>
              <text class="email-rule-note">涉及准确价格、付款或合同必须人工确认</text>
            </view>
            <view class="email-rule">
              <text class="email-rule-icon">⛟</text>
              <text class="email-rule-title">交付周期</text>
              <text class="email-rule-note">不得自动承诺物流、清关或交付时间</text>
            </view>
            <view class="email-rule">
              <text class="email-rule-icon">⊘</text>
              <text class="email-rule-title">DNC/D/E</text>
              <text class="email-rule-note">勿扰或 D/E 级客户必须硬阻断</text>
            </view>
            <view class="email-rule">
              <text class="email-rule-icon">K</text>
              <text class="email-rule-title">知识命中</text>
              <text class="email-rule-note">{{ detail.knowledgeHits.length }} 条可审计知识证据</text>
            </view>
          </view>
        </section>

        <view class="section-head">
          <text class="section-title">AI 建议回复</text>
          <text class="section-note">{{ detail.promptVersion }}</text>
        </view>
        <section class="reply-editor">
          <text class="reply-subject">Тема: {{ detail.replySubject }}</text>
          <text class="reply-body">{{ detail.replyBody || 'AI 建议回复待生成。' }}</text>
        </section>

        <view class="section-head">
          <text class="section-title">知识证据</text>
          <text class="section-note">{{ detail.knowledgeHits.length }} hits</text>
        </view>
        <section class="email-panel">
          <view v-for="hit in detail.knowledgeHits" :key="hit.id" class="email-knowledge-hit">
            <view class="email-knowledge-icon">K</view>
            <view class="email-card-main">
              <text class="email-row-title">{{ hit.title }}</text>
              <text class="email-row-note">{{ hit.note || '知识摘要待补全' }} · {{ hit.similarityText }}</text>
            </view>
            <text :class="['pool-tag', hit.autoReplyAllowed ? 'risk-low' : 'pool-tag-amber']">
              {{ hit.autoReplyAllowed ? 'ready' : '约束' }}
            </text>
          </view>
          <text v-if="!detail.knowledgeHits.length" class="email-row-note">暂无知识命中，不能自动发送。</text>
        </section>

        <view class="section-head">
          <text class="section-title">AI 审计</text>
          <text class="section-note">{{ detail.modelName }}</text>
        </view>
        <section class="email-panel">
          <view class="source-tag-row">
            <text class="pool-tag pool-tag-blue">Prompt {{ detail.promptVersion }}</text>
            <text class="pool-tag pool-tag-blue">模型 {{ detail.modelName }}</text>
            <text
              v-for="reason in detail.autoSendCheck.reasons"
              :key="reason"
              class="pool-tag pool-tag-red"
            >
              {{ reason }}
            </text>
          </view>
        </section>
      </template>
    </scroll-view>

    <view class="email-action-bar">
      <button class="email-button email-button-secondary" @click="rejectReply">驳回建议</button>
      <button
        :class="['email-button', canConfirmSend ? 'email-button-primary' : 'email-button-disabled']"
        :disabled="!canConfirmSend"
        @click="confirmSend"
      >
        {{ confirmLabel }}
      </button>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue';
import { onLoad as onUniLoad } from '@dcloudio/uni-app';

import { emailRepliesService, mapEmailReplyDetail } from '../../services/emailReplies.js';
import '../../styles/home.css';
import '../../styles/leadPool.css';
import '../../styles/sourceCandidates.css';
import '../../styles/emailReplies.css';

const detail = ref(mapEmailReplyDetail({}));
const replyId = ref('');
const isLoading = ref(false);
const errorMessage = ref('');
const actionMessage = ref('');

const canConfirmSend = computed(
  () => detail.value.autoSendCheck.allowAutoSend || detail.value.autoSendCheck.decision === 'manual_review',
);
const confirmLabel = computed(() => (actionMessage.value ? actionMessage.value : '人工确认发送'));

onUniLoad((options = {}) => {
  initializeFromOptions(options);
});

if (globalThis.location?.search) {
  const params = new URLSearchParams(globalThis.location.search);
  initializeFromOptions({ id: params.get('id') || '' });
}

function initializeFromOptions(options = {}) {
  const id = options.id || '';
  if (!id || id === replyId.value) {
    return;
  }
  replyId.value = id;
  loadDetail();
}

async function loadDetail() {
  if (!replyId.value) {
    errorMessage.value = '缺少邮件回复 ID。';
    return;
  }
  isLoading.value = true;
  errorMessage.value = '';
  actionMessage.value = '';
  try {
    detail.value = await emailRepliesService.getEmailReply(replyId.value);
  } catch (error) {
    detail.value = mapEmailReplyDetail({});
    errorMessage.value = `邮件回复详情加载失败：${error.message || 'Unknown'}`;
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

async function confirmSend() {
  if (!replyId.value || !canConfirmSend.value) {
    return;
  }
  try {
    detail.value = await emailRepliesService.confirmManualSend(replyId.value, {
      actor: 'mobile-operator',
      note: '移动端人工确认发送',
    });
    actionMessage.value = '已确认';
  } catch (error) {
    actionMessage.value = '';
    errorMessage.value = `人工确认发送失败：${error.message || 'Unknown'}`;
  }
}

async function rejectReply() {
  if (!replyId.value) {
    return;
  }
  try {
    detail.value = await emailRepliesService.rejectReply(replyId.value, {
      actor: 'mobile-operator',
      note: '移动端驳回 AI 建议',
    });
    actionMessage.value = '已驳回';
  } catch (error) {
    actionMessage.value = '';
    errorMessage.value = `驳回失败：${error.message || 'Unknown'}`;
  }
}

function goBack() {
  if (globalThis.uni?.navigateBack) {
    globalThis.uni.navigateBack();
  }
}
</script>
