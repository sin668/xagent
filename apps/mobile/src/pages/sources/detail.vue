<template>
  <view class="source-detail-page">
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
        <view class="nav-title">来源详情</view>
        <view class="nav-subtitle">审核通过只代表允许抽取，不代表允许触达</view>
      </view>
      <view class="nav-action" aria-label="刷新" @click="loadDetail">↻</view>
    </view>

    <scroll-view scroll-y class="source-detail-content">
      <view v-if="errorMessage" class="source-alert">{{ errorMessage }}</view>
      <view v-else-if="isLoading" class="source-empty">正在加载来源详情...</view>

      <template v-else>
        <section class="source-detail-hero">
          <image
            mode="aspectFill"
            src="https://images.unsplash.com/photo-1603386329225-868f9b1ee6c9?auto=format&fit=crop&w=900&q=80"
          />
          <view class="source-detail-hero-overlay">
            <view class="source-detail-eyebrow">{{ detail.riskLevel }} 风险 · 只读公开页</view>
            <view>
              <view class="source-detail-title">{{ detail.normalizedDomain || detail.sourceUrl || 'Unknown domain' }}</view>
              <view class="source-detail-desc">
                {{ detail.city }} · {{ detail.platform }} · confidence {{ confidenceText }}
              </view>
            </view>
          </view>
        </section>

        <section class="source-summary-card source-detail-panel">
          <view class="source-card-top">
            <view>
              <view class="source-summary-title">来源风险与准入</view>
              <view class="source-summary-meta">reviewStatus: {{ detail.reviewStatus }}</view>
            </view>
            <text :class="['source-tag', detail.approvedForExtraction ? 'source-tag-green' : 'source-tag-red']">
              {{ detail.approvedForExtraction ? '已准入' : '未准入' }}
            </text>
          </view>
          <view class="source-url">{{ detail.sourceUrl || 'Unknown URL' }}</view>
          <view class="source-map source-detail-mini-grid">
            <view class="source-tile">
              <text class="source-kicker">riskLevel</text>
              <text :class="['source-number', getRiskNumberClass(detail.riskLevel)]">{{ detail.riskLevel }}</text>
            </view>
            <view class="source-tile">
              <text class="source-kicker">approvedForExtraction</text>
              <text class="source-number">{{ String(detail.approvedForExtraction) }}</text>
            </view>
            <view class="source-tile">
              <text class="source-kicker">platform</text>
              <text class="source-number source-detail-mini-value">{{ detail.platform }}</text>
            </view>
            <view class="source-tile">
              <text class="source-kicker">city</text>
              <text class="source-number source-detail-mini-value">{{ detail.city }}</text>
            </view>
          </view>
        </section>

        <view class="section-head">
          <text class="section-title">发现证据</text>
          <text class="section-note">必须保留</text>
        </view>
        <section class="source-card">
          <view class="source-evidence">{{ detail.evidenceNote || 'Unknown' }}</view>
          <view class="source-detail-link-list">
            <text v-for="link in detail.evidenceLinks" :key="link" class="source-detail-link">{{ link }}</text>
          </view>
          <view class="source-detail-timeline">
            <view class="source-detail-timeline-item">
              <text class="source-detail-dot" />
              <view>
                <text class="source-detail-timeline-title">SOURCE_DISCOVERY</text>
                <text class="source-detail-timeline-note">
                  {{ detail.llmProvider || 'Unknown' }} · {{ detail.llmModel || 'Unknown' }} · task {{ detail.createdByTaskRunId || 'Unknown' }}
                </text>
              </view>
            </view>
            <view class="source-detail-timeline-item">
              <text class="source-detail-dot" />
              <view>
                <text class="source-detail-timeline-title">risk gate</text>
                <text class="source-detail-timeline-note">{{ riskGateText }}</text>
              </view>
            </view>
          </view>
        </section>

        <view class="section-head">
          <text class="section-title">LLM 输出摘要</text>
          <text class="section-note">agent_task_runs</text>
        </view>
        <section class="source-card">
          <view class="source-detail-json">{{ llmSummaryText }}</view>
          <view class="source-tag-row">
            <text class="source-tag source-tag-blue">createdByTaskRunId {{ detail.createdByTaskRunId || 'Unknown' }}</text>
            <text class="source-tag source-tag-blue">auditTaskRunId {{ detail.auditTaskRunId || 'Unknown' }}</text>
          </view>
        </section>

        <section class="source-summary-card source-detail-panel">
          <view class="source-summary-title">审核动作</view>
          <view class="source-summary-meta">
            所有动作写入 reviewer、review_note、reviewed_at；审核通过只代表允许抽取，不代表允许触达。
          </view>
          <textarea
            v-model="reviewNote"
            class="source-review-note"
            placeholder="填写审核备注，说明风险判断和证据依据"
          />
          <view class="source-action-grid">
            <button
              v-if="canApproveForExtraction"
              class="source-action-button source-action-primary"
              @click="submitReviewAction('approve_for_extraction')"
            >
              只读抽取
            </button>
            <button class="source-action-button" @click="submitReviewAction('reject')">驳回</button>
            <button class="source-action-button" @click="submitReviewAction('mark_high_risk')">标记高风险</button>
            <button class="source-action-button" @click="submitReviewAction('pause_channel')">暂停渠道</button>
            <button class="source-action-button" @click="submitReviewAction('add_review_note')">添加备注</button>
          </view>
          <view v-if="detail.riskLevel === 'Forbidden'" class="source-alert source-detail-warning">
            Forbidden 来源不得进入自动抽取；页面不展示通过按钮，后端仍会执行阻断。
          </view>
          <view v-if="actionMessage" class="source-empty source-detail-action-message">{{ actionMessage }}</view>
        </section>
      </template>
    </scroll-view>
  </view>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';

import { sourceCandidatesService } from '../../services/sourceCandidates.js';
import '../../styles/home.css';
import '../../styles/sourceCandidates.css';

const emptyDetail = {
  id: '',
  sourceUrl: '',
  normalizedDomain: '',
  platform: 'Unknown',
  country: 'Unknown',
  city: 'Unknown',
  riskLevel: 'Unknown',
  reviewStatus: 'pending',
  approvedForExtraction: false,
  evidenceNote: '',
  evidenceLinks: [],
  llmProvider: '',
  llmModel: '',
  llmOutputSummary: {},
  confidenceScore: null,
  createdByTaskRunId: null,
  auditTaskRunId: null,
};

const detail = ref(emptyDetail);
const isLoading = ref(false);
const errorMessage = ref('');
const actionMessage = ref('');
const reviewNote = ref('');

const canApproveForExtraction = computed(() => detail.value.riskLevel !== 'Forbidden');
const confidenceText = computed(() => {
  const score = detail.value.confidenceScore;
  return score === null || score === undefined ? 'Unknown' : Number(score).toFixed(2);
});
const llmSummaryText = computed(() => JSON.stringify(detail.value.llmOutputSummary || {}, null, 2));
const riskGateText = computed(() => {
  if (detail.value.riskLevel === 'Forbidden') {
    return 'Forbidden 默认阻断，不进入自动抽取队列';
  }
  if (detail.value.riskLevel === 'High' && !detail.value.approvedForExtraction) {
    return 'High 默认进入人工复核，未通过前不进入自动抽取队列';
  }
  return detail.value.approvedForExtraction ? '已允许只读抽取，不允许自动触达' : '待人工复核';
});

function getCurrentCandidateId() {
  return globalThis.getCurrentPages?.()?.at(-1)?.options?.id || detail.value.id;
}

onMounted(loadDetail);

async function loadDetail() {
  const candidateId = getCurrentCandidateId();
  if (!candidateId) {
    errorMessage.value = '缺少来源候选 ID。';
    return;
  }

  isLoading.value = true;
  errorMessage.value = '';
  actionMessage.value = '';
  try {
    detail.value = await sourceCandidatesService.getSourceCandidate(candidateId);
  } catch (_error) {
    detail.value = emptyDetail;
    errorMessage.value = '真实 API 暂不可用，请检查来源候选详情接口。';
  } finally {
    isLoading.value = false;
  }
}

async function submitReviewAction(action) {
  if (!detail.value.id) {
    actionMessage.value = '缺少来源候选 ID，无法提交审核动作。';
    return;
  }

  if (action === 'approve_for_extraction' && detail.value.riskLevel === 'Forbidden') {
    actionMessage.value = 'Forbidden 来源不得批准进入自动抽取。';
    return;
  }

  try {
    detail.value = await sourceCandidatesService.reviewSourceCandidate(detail.value.id, {
      action,
      reviewerId: 'mobile-reviewer',
      reviewNote: reviewNote.value || '移动端人工审核动作',
    });
    actionMessage.value = '审核动作已提交并写入审计。';
  } catch (_error) {
    actionMessage.value = '审核动作提交失败，请检查后端审核接口和风险闸门。';
  }
}

function getRiskNumberClass(riskLevel) {
  if (riskLevel === 'Low') {
    return 'source-number-green';
  }
  if (riskLevel === 'Medium') {
    return 'source-number-amber';
  }
  if (riskLevel === 'High' || riskLevel === 'Forbidden') {
    return 'source-number-red';
  }
  return '';
}

function goBack() {
  if (globalThis.uni?.navigateBack) {
    globalThis.uni.navigateBack();
  }
}
</script>
