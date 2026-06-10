<template>
  <section id="email-reply-review" class="admin-card email-reply-card">
    <div class="card-head">
      <div><h3>邮件自动回复审核台</h3><span>AI 建议与最终发送内容分开保存；确认发送前必须调用后端发送前检查</span></div>
      <span class="tag amber">{{ emailReplyReview.summary.manualReviewCount }} 待人工确认</span>
    </div>
    <p v-if="errorMessage" class="guardrail">{{ errorMessage }}</p>
    <p v-else-if="isLoading" class="guardrail">正在加载邮件审核真实 API...</p>
    <div class="email-reply-summary">
      <article><strong>{{ emailReplyReview.summary.pendingReplyCount }}</strong><span>待回复邮件</span></article>
      <article><strong>{{ emailReplyReview.summary.autoSendCandidateCount }}</strong><span>自动发送候选</span></article>
      <article><strong>{{ emailReplyReview.summary.manualReviewCount }}</strong><span>人工确认</span></article>
      <article><strong>{{ emailReplyReview.summary.hardBlockedCount }}</strong><span>硬拦截</span></article>
    </div>
    <div class="email-reply-grid">
      <section>
        <div class="card-head compact-head"><h4>待审核队列</h4><span>风险优先，来自真实邮件回复草稿 API</span></div>
        <table class="table">
          <thead><tr><th>客户</th><th>主题</th><th>语言</th><th>判断</th><th>原因</th></tr></thead>
          <tbody>
            <tr v-for="draft in emailReplyReview.queue" :key="draft.id">
              <td>{{ draft.customerName }}</td><td>{{ draft.subject }}</td><td>{{ draft.language }}</td>
              <td><span :class="['tag', draft.decisionClass]">{{ draft.decisionLabel }}</span></td><td>{{ draft.reason }}</td>
            </tr>
            <tr v-if="emailReplyReview.queue.length === 0"><td colspan="5">暂无真实邮件回复草稿数据</td></tr>
          </tbody>
        </table>
      </section>
      <section>
        <div class="card-head compact-head"><h4>当前回复草稿</h4><span>{{ emailReplyReview.selectedDraft.aiSuggestion.promptVersionLabel }}</span></div>
        <div class="reply-editor"><div class="subject-line">{{ emailReplyReview.selectedDraft.finalReply.subject }}</div><div class="body-text">{{ emailReplyReview.selectedDraft.finalReply.body || '暂无最终正文' }}</div></div>
        <div class="mail-rule-grid">
          <article><strong>{{ emailReplyReview.selectedDraft.knowledgeHits.length }} 条知识</strong><span>{{ knowledgeHitsText }}</span></article>
          <article><strong>{{ emailReplyReview.selectedDraft.risk.route }}</strong><span>{{ emailReplyReview.selectedDraft.risk.hardBlockReasonsText }}</span></article>
        </div>
        <p class="guardrail">{{ emailReplyReview.permissionNotice }}</p>
      </section>
    </div>
    <div class="email-review-lower-grid">
      <section class="schema-preview"><div class="card-head compact-head"><h4>客户上下文与来信</h4><span>{{ emailReplyReview.selectedDraft.customerContext.vehicleIntentSummary }}</span></div><pre>{{ contextText }}</pre></section>
      <section><div class="card-head compact-head"><h4>人工动作入口</h4><span>发送前检查由后端控制</span></div><div class="email-action-list"><article v-for="entry in emailReplyReview.actionEntrypoints" :key="entry.label"><strong>{{ entry.label }}</strong><span :class="['tag', entry.enabled ? 'blue' : 'amber']">{{ entry.enabled ? '可操作' : '禁用' }}</span></article></div></section>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';

import { buildEmailReplyReviewView, fetchEmailReplyReview } from '../services/emailReplyReview.js';
import { adminActorRole, apiBaseUrl, formatLoadError } from './pageRuntime.js';

const payload = ref(null);
const isLoading = ref(true);
const errorMessage = ref('');
const emailReplyReview = computed(() => buildEmailReplyReviewView({
  drafts: payload.value?.drafts || {},
  actorRole: payload.value?.actorRole || adminActorRole,
}));
const knowledgeHitsText = computed(() => {
  const hits = emailReplyReview.value.selectedDraft.knowledgeHits;
  return hits.length === 0 ? '无知识命中' : hits.map((hit) => `${hit.title} ${hit.scoreText}`).join(' / ');
});
const contextText = computed(() => JSON.stringify({
  customer: emailReplyReview.value.selectedDraft.customerContext,
  inbound: emailReplyReview.value.selectedDraft.inbound,
  ai_suggestion: emailReplyReview.value.selectedDraft.aiSuggestion,
}, null, 2));

onMounted(async () => {
  try {
    payload.value = await fetchEmailReplyReview({ baseUrl: apiBaseUrl, actorRole: adminActorRole });
  } catch (error) {
    errorMessage.value = formatLoadError('无法加载邮件回复审核真实 API', error);
  } finally {
    isLoading.value = false;
  }
});
</script>
