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
      <view class="nav-title">{{ detail.customerName }}</view>
      <view class="nav-action" aria-label="更多">⋯</view>
    </view>

    <scroll-view scroll-y class="detail-content">
      <section class="detail-panel">
        <view class="pool-card-top">
          <view>
            <view class="detail-hero-title">{{ detail.customerName }}</view>
            <view class="detail-subtitle">{{ detail.basicInfo }}</view>
          </view>
          <text :class="['pool-tag', detail.gradeClass]">{{ detail.gradeLabel }}</text>
        </view>
        <view class="detail-tag-grid">
          <text class="pool-tag pool-tag-blue">来源 {{ detail.sources.length }}</text>
          <text :class="['pool-tag', detail.riskLabel === '低风险' ? 'risk-low' : 'risk-medium']">
            {{ detail.riskLabel }}
          </text>
          <text class="pool-tag pool-tag-amber">{{ detail.handoffLabel }}</text>
        </view>
        <view v-if="detail.complianceLabel" class="detail-tag-row">
          <text class="pool-tag pool-tag-red">{{ detail.complianceLabel }}</text>
        </view>
      </section>

      <view class="detail-section-head">
        <text class="detail-section-title">经营状况判断</text>
      </view>
      <section class="detail-panel">
        <text class="detail-copy-strong">{{ detail.operatingSummary }}</text>
      </section>

      <view class="detail-section-head">
        <text class="detail-section-title">AI 建议</text>
        <text class="detail-section-note">可信度 {{ detail.aiAdvice.confidenceText }}</text>
      </view>
      <section class="detail-panel">
        <text class="detail-copy-strong">{{ detail.aiAdvice.suggestion }}</text>
        <text class="detail-copy">{{ detail.aiAdvice.reason }}</text>
        <view class="detail-tag-row">
          <text class="pool-tag pool-tag-blue">下一步：{{ detail.aiAdvice.nextAction }}</text>
          <text v-for="item in detail.aiAdvice.missingInfo" :key="item" class="pool-tag pool-tag-amber">
            缺失：{{ item }}
          </text>
        </view>
      </section>

      <view class="detail-section-head">
        <text class="detail-section-title">准入闸门</text>
        <text class="detail-section-note">{{ detail.coreGateLabel }}</text>
      </view>
      <section class="detail-panel gate-panel">
        <view class="compliance-status-row">
          <text :class="['pool-tag', detail.coreGate.canPromoteToCore ? 'risk-low' : 'pool-tag-red']">
            {{ detail.coreGateLabel }}
          </text>
          <text class="pool-tag pool-tag-blue">模型 {{ detail.aiAudit.modelName }}</text>
          <text class="pool-tag pool-tag-blue">Prompt {{ detail.aiAudit.promptVersion }}</text>
        </view>
        <view class="detail-tag-row">
          <text v-for="reason in detail.coreGate.reasons" :key="reason" class="pool-tag pool-tag-amber">
            {{ reason }}
          </text>
        </view>
        <text v-if="detail.latestPageSnapshot" class="detail-copy">
          快照：{{ detail.latestPageSnapshot.pageTitle }} · {{ detail.latestPageSnapshot.readStatus }} · {{ detail.latestPageSnapshot.capturedAt }}
        </text>
      </section>

      <view v-if="detail.duplicateLabel" class="detail-section-head">
        <text class="detail-section-title">重复建议</text>
        <text class="detail-section-note">{{ detail.duplicateLabel }}</text>
      </view>
      <section v-if="detail.duplicateLabel" class="detail-panel">
        <text class="detail-copy-strong">{{ detail.duplicateLabel }}</text>
        <view class="detail-tag-row">
          <text
            v-for="item in duplicateItems"
            :key="`${item.target_type}-${item.target_id}-${item.reason}`"
            class="pool-tag pool-tag-amber"
          >
            {{ item.reason }}
          </text>
        </view>
      </section>

      <view class="detail-section-head">
        <text class="detail-section-title">证据与来源</text>
        <text class="detail-section-note">{{ detail.hasViewableEvidence ? '可查看' : '缺证据' }}</text>
      </view>
      <section class="detail-panel">
        <view class="detail-timeline">
          <view v-for="source in detail.sources" :key="`${source.type}-${source.url}`" class="detail-timeline-item">
            <text class="detail-dot" />
            <view class="detail-timeline-copy">
              <text class="detail-timeline-title">{{ source.type }}</text>
              <text>{{ source.evidence || 'Unknown' }}</text>
              <text v-if="source.url" class="detail-link">{{ source.url }}</text>
            </view>
          </view>
        </view>
      </section>

      <view class="detail-section-head">
        <text class="detail-section-title">联系方式</text>
        <text class="detail-section-note">{{ detail.contacts.length }} 个</text>
      </view>
      <section class="detail-panel">
        <view class="contact-grid">
          <view v-for="contact in detail.contacts" :key="`${contact.type}-${contact.value}`" class="contact-row">
            <view>
              <text class="contact-type">{{ contact.type }}</text>
              <text class="detail-copy">{{ contact.usage }}</text>
            </view>
            <text class="contact-value">{{ contact.value }}</text>
          </view>
        </view>
      </section>

      <view class="detail-section-head">
        <text class="detail-section-title">跟进记录</text>
        <text class="detail-section-note">{{ detail.gradeLabel }} SLA</text>
      </view>
      <section class="detail-panel">
        <view class="detail-timeline">
          <view v-for="followUp in detail.followUps" :key="followUp.title" class="detail-timeline-item">
            <text class="detail-dot" />
            <view class="detail-timeline-copy">
              <text class="detail-timeline-title">{{ followUp.title }}</text>
              <text>{{ followUp.detail }}</text>
            </view>
          </view>
        </view>
      </section>

      <view class="detail-section-head">
        <text class="detail-section-title">触达历史</text>
        <text class="detail-section-note">{{ outreachHistory.length }} 条</text>
      </view>
      <section class="detail-panel history-list">
        <view v-for="record in outreachHistory" :key="record.id" class="detail-timeline-item">
          <text class="detail-dot" />
          <view class="detail-timeline-copy">
            <text class="detail-timeline-title">{{ record.title }}</text>
            <text>{{ record.detail }}</text>
          </view>
        </view>
      </section>

      <view class="detail-section-head">
        <text class="detail-section-title">车源匹配</text>
        <text class="detail-section-note">{{ inventoryMatches.length }} 条推荐</text>
      </view>
      <section class="detail-panel" @click="openInventory">
        <text class="detail-copy-strong">{{ detail.inventoryEntry.label }}</text>
        <text class="detail-copy">进入车源匹配页查看可用于后续人工报价前评估的车辆。</text>
        <view class="inventory-match-list">
          <view v-for="match in inventoryMatches" :key="match.matchId" class="inventory-match-row">
            <text class="detail-timeline-title">{{ match.title }}</text>
            <text class="detail-copy">{{ match.reason }}</text>
            <text class="detail-copy">{{ match.priceText }} · {{ match.expiryLabel }} · {{ match.exportLabel }}</text>
            <view class="detail-tag-row">
              <text :class="['pool-tag', match.priorityRecommendable ? 'risk-low' : 'pool-tag-red']">
                {{ match.priorityRecommendable ? '可推进报价前评估' : '暂不匹配' }}
              </text>
              <text v-for="tip in match.riskTips" :key="tip" class="pool-tag pool-tag-amber">{{ tip }}</text>
            </view>
          </view>
        </view>
      </section>

      <view class="detail-section-head">
        <text class="detail-section-title">合规复核</text>
        <text class="detail-section-note">{{ complianceReview.label }}</text>
      </view>
      <section class="detail-panel compliance-panel">
        <view class="compliance-status-row">
          <text :class="['pool-tag', complianceReview.quoteContractBlocked ? 'pool-tag-red' : 'risk-low']">
            {{ complianceReview.label }}
          </text>
          <text :class="['pool-tag', complianceReview.quoteContractBlocked ? 'pool-tag-amber' : 'risk-low']">
            {{ complianceReview.quoteContractBlocked ? '报价前阻断' : '可进入报价前评估' }}
          </text>
        </view>
        <text class="detail-copy-strong">{{ complianceReview.reason }}</text>
        <text class="detail-copy">{{ complianceReview.riskNote }}</text>
        <view class="compliance-meta">
          <text class="detail-timeline-title">复核人</text>
          <text class="detail-copy">{{ complianceReview.reviewerText }}</text>
        </view>
        <view class="compliance-tip">
          <text>{{ complianceReview.aiRiskTip }}</text>
        </view>
      </section>

      <view class="detail-section-head">
        <text class="detail-section-title">AI 触达草稿</text>
        <text class="detail-section-note">{{ draft.versionLabel }}</text>
      </view>
      <section class="draft-panel" @click="openOutreach">
        <text class="draft-subject-label">俄语草稿</text>
        <text class="draft-subject">{{ draft.subject }}</text>
        <text class="draft-refusal">
          {{ draft.canGenerateDraft ? '需人工确认后记录发送' : draft.blockReasons.join('；') }}
        </text>
        <view class="detail-tag-row">
          <text
            v-for="check in draft.complianceChecks.slice(0, 3)"
            :key="check.key"
            :class="['pool-tag', check.passed ? 'risk-low' : 'pool-tag-red']"
          >
            {{ check.label }}
          </text>
        </view>
      </section>
    </scroll-view>

    <view class="action-bar">
      <button class="detail-button detail-button-secondary" @click="handleMarkDoNotContact">
        {{ detail.isDoNotContact ? '已勿扰' : '标记勿扰' }}
      </button>
      <button
        :class="['detail-button', detail.canEnterOutreachQueue ? 'detail-button-primary' : 'detail-button-disabled']"
        :disabled="!detail.canEnterOutreachQueue"
        @click="handlePromoteStaging"
      >
        {{ detail.outreachActionLabel }}
      </button>
    </view>
  </view>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';

import {
  mapComplianceStatus,
  mapCustomerSummaryToLeadDetail,
  mapInventoryMatches,
  mapOutreachDraft,
  mapOutreachRecords,
  mapStagingLeadDetailToLeadDetail,
} from '../../services/apiAdapters.js';
import { apiClient } from '../../services/apiClient.js';
import { buildComplianceReviewView } from '../../services/complianceReview.js';
import { buildLeadDetailViewModel, buildPromoteStagingPayload, markLeadDoNotContact } from '../../services/leadDetail.js';
import { buildInventoryMatchView } from '../../services/inventoryMatch.js';
import { buildOutreachDraftViewModel } from '../../services/outreachDraft.js';
import { buildOutreachHistoryView } from '../../services/outreachRecord.js';
import '../../styles/home.css';
import '../../styles/leadPool.css';
import '../../styles/leadDetail.css';
import '../../styles/inventory.css';
import '../../styles/outreachDraft.css';
import '../../styles/outreachRecord.css';

const emptyLeadDetail = {
  id: '',
  customerName: 'Unknown',
  country: 'Unknown',
  city: 'Unknown',
  customerType: 'Unknown',
  grade: 'Unknown',
  status: 'pending',
  riskLevel: 'Unknown',
  operatingSummary: 'Unknown',
  aiRecommendation: {
    confidence: null,
    suggestion: 'Unknown',
    reason: 'Unknown',
    missingInfo: [],
    nextAction: 'Unknown',
  },
  sources: [],
  contacts: [],
  followUps: [],
  inventoryMatch: {
    label: '查看匹配车源',
    path: '/pages/inventory/index',
  },
  coreGate: {
    status: 'blocked',
    canPromoteToCore: false,
    reasons: ['等待后端数据'],
  },
  duplicateSignals: {},
  doNotContact: false,
};
const emptyOutreachDraft = {
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

const leadState = ref(emptyLeadDetail);
const outreachRecords = ref([]);
const outreachDraft = ref(emptyOutreachDraft);
const complianceState = ref(null);
const inventoryMatchItems = ref([]);
const promotedCustomerId = ref('');
const detail = computed(() => buildLeadDetailViewModel(leadState.value));
const duplicateItems = computed(() => [
  ...(detail.value.duplicateSignals.strongDuplicates || []),
  ...(detail.value.duplicateSignals.suspectedDuplicates || []),
  ...(detail.value.duplicateSignals.sourceDuplicates || []),
]);
const complianceReview = computed(() => {
  const grade = leadState.value.grade;
  if (String(grade).toUpperCase() !== 'C') {
    return buildComplianceReviewView({
      grade,
      status: 'not_required',
      reason: '非C级线索默认不需要报价前合规复核',
      riskNote: '仍需遵守人工报价、合同和付款审核流程',
      quoteContractBlocked: false,
    });
  }

  return buildComplianceReviewView({
    grade,
    ...(complianceState.value || leadState.value.complianceReview || {}),
  });
});
const inventoryMatches = computed(() => inventoryMatchItems.value.map((match) => buildInventoryMatchView(match)));
const outreachHistory = computed(() => buildOutreachHistoryView(outreachRecords.value));
const draft = computed(() =>
  buildOutreachDraftViewModel({
    lead: {
      id: detail.value.id,
      customerName: detail.value.customerName,
      grade: leadState.value.grade,
      channel: leadState.value.channel,
      riskLevel: leadState.value.riskLevel,
      doNotContact: detail.value.isDoNotContact,
    },
    draft: outreachDraft.value,
  }),
);

function getCurrentLeadId() {
  return globalThis.getCurrentPages?.()?.at(-1)?.options?.id || leadState.value.id;
}

function getBackendCustomerId() {
  return promotedCustomerId.value || detail.value.id;
}

onMounted(async () => {
  const leadId = getCurrentLeadId();
  try {
    const stagingLead = await apiClient.get(`/staging-leads/${encodeURIComponent(leadId)}`);
    leadState.value = mapStagingLeadDetailToLeadDetail(stagingLead);
  } catch (_stagingError) {
    try {
      const customer = await apiClient.get(`/customers/${encodeURIComponent(leadId)}`);
      leadState.value = mapCustomerSummaryToLeadDetail(customer);
    } catch (_customerError) {
      leadState.value = {
        ...emptyLeadDetail,
        id: leadId,
      };
    }
  }

  try {
    const records = await apiClient.get(`/customers/${encodeURIComponent(getBackendCustomerId())}/outreach-records`);
    outreachRecords.value = mapOutreachRecords(records);
  } catch (_error) {
    outreachRecords.value = [];
  }

  try {
    const payload = await apiClient.get(`/outreach-drafts/${encodeURIComponent(getBackendCustomerId())}`);
    outreachDraft.value = mapOutreachDraft(payload);
  } catch (_error) {
    outreachDraft.value = emptyOutreachDraft;
  }

  try {
    const payload = await apiClient.get(`/compliance/customers/${encodeURIComponent(getBackendCustomerId())}/status`);
    complianceState.value = mapComplianceStatus(payload);
  } catch (_error) {
    complianceState.value = null;
  }

  try {
    const payload = await apiClient.post(`/inventory/matches/${encodeURIComponent(getBackendCustomerId())}/recommendations`, {
      requires_compliance_review: String(leadState.value.grade || '').toUpperCase() === 'C',
    });
    inventoryMatchItems.value = mapInventoryMatches(payload);
  } catch (_error) {
    inventoryMatchItems.value = [];
  }
});

async function handleMarkDoNotContact() {
  if (detail.value.isDoNotContact) {
    return;
  }

  const nextLead = markLeadDoNotContact(leadState.value, {
    actor: '当前用户',
    reason: '移动端人工标记勿扰',
  });
  leadState.value = nextLead;

  try {
    await apiClient.post(`/customers/${encodeURIComponent(detail.value.id)}/do-not-contact`, {
      actor: '当前用户',
      reason: '移动端人工标记勿扰',
    });
  } catch (_error) {
    leadState.value = nextLead;
  }
}

async function handlePromoteStaging() {
  if (!detail.value.canEnterOutreachQueue || promotedCustomerId.value) {
    return;
  }

  try {
    const result = await apiClient.post(`/staging-leads/${encodeURIComponent(detail.value.id)}/promote`, buildPromoteStagingPayload({
      actor: '当前用户',
      reviewNote: '移动端人工复核通过，准入闸门允许晋级 core。',
    }));
    promotedCustomerId.value = result.customer_id || '';
  } catch (_error) {
    promotedCustomerId.value = '';
  }
}


function openInventory() {
  const path = detail.value.inventoryEntry?.path;
  if (!path || !globalThis.uni?.navigateTo) {
    return;
  }

  globalThis.uni.navigateTo({ url: path });
}

function openOutreach() {
  if (!draft.value.canGenerateDraft || !globalThis.uni?.navigateTo) {
    return;
  }

  globalThis.uni.navigateTo({ url: `/pages/outreach/index?leadId=${encodeURIComponent(detail.value.id)}` });
}

function goBack() {
  if (globalThis.uni?.navigateBack) {
    globalThis.uni.navigateBack();
  }
}
</script>
