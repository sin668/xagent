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

      <view class="detail-section-head">
        <text class="detail-section-title">线索完善区</text>
        <text class="detail-section-note">{{ enrichmentView.fieldCandidates.length }} 个候选</text>
      </view>
      <section class="detail-panel enrichment-panel">
        <view class="enrichment-action-row">
          <view class="enrichment-action-copy">
            <text class="detail-copy-strong">AI 深挖与人工补录</text>
            <text class="detail-copy">
              深挖结果只进入 staging 完善区，字段采纳后仍需人工确认晋级客户。
            </text>
          </view>
          <button
            v-if="enrichmentView.canTriggerDeepEnrichment"
            class="enrichment-button-primary"
            @click="handleCreateEnrichmentRun"
          >
            {{ enrichmentLoading ? '处理中' : enrichmentView.triggerButtonLabel }}
          </button>
          <text v-else class="pool-tag pool-tag-red">{{ enrichmentView.blockReason }}</text>
        </view>

        <view class="detail-tag-row">
          <button class="enrichment-button-secondary" @click="toggleManualEnrichmentForm">人工补录</button>
          <text v-for="result in enrichmentView.results.slice(0, 2)" :key="result.id" class="pool-tag pool-tag-blue">
            {{ result.typeLabel }} · {{ result.statusLabel }} · {{ result.confidenceText }}
          </text>
        </view>

        <view v-if="manualEnrichmentVisible" class="manual-enrichment-form">
          <input
            v-model="manualFieldName"
            class="manual-enrichment-input"
            placeholder="字段名，例如 邮箱 / 意向车型"
          />
          <input
            v-model="manualCandidateValue"
            class="manual-enrichment-input"
            placeholder="字段值"
          />
          <input
            v-model="manualEvidenceNote"
            class="manual-enrichment-input"
            placeholder="证据说明或人工来源"
          />
          <button class="enrichment-button-primary manual-enrichment-submit" @click="handleCreateManualEnrichment">
            提交补录
          </button>
        </view>

        <text v-if="enrichmentView.emptyLabel" class="detail-copy">{{ enrichmentView.emptyLabel }}</text>
        <view v-else class="enrichment-candidate-list">
          <view
            v-for="candidate in enrichmentView.fieldCandidates"
            :key="candidate.id"
            class="enrichment-candidate-card"
          >
            <view class="enrichment-candidate-head">
              <view>
                <text class="detail-timeline-title">{{ candidate.fieldName }}</text>
                <text class="detail-copy-strong">{{ candidate.candidateValue }}</text>
              </view>
              <text
                :class="[
                  'pool-tag',
                  candidate.reviewStatus === 'accepted'
                    ? 'risk-low'
                    : candidate.reviewStatus === 'rejected'
                      ? 'pool-tag-red'
                      : 'pool-tag-amber',
                ]"
              >
                {{ candidate.reviewStatusLabel }}
              </text>
            </view>
            <text class="detail-copy">证据：{{ candidate.evidenceNote }}</text>
            <text v-if="candidate.sourceUrl" class="detail-link">{{ candidate.sourceUrl }}</text>
            <view class="detail-tag-row">
              <text class="pool-tag pool-tag-blue">置信度 {{ candidate.confidenceText }}</text>
              <text class="pool-tag pool-tag-blue">来源 {{ candidate.sourceType }}</text>
              <text v-if="candidate.acceptedBy" class="pool-tag risk-low">采纳人 {{ candidate.acceptedBy }}</text>
              <text v-if="candidate.rejectedReason" class="pool-tag pool-tag-red">{{ candidate.rejectedReason }}</text>
            </view>
            <view v-if="candidate.reviewStatus === 'pending'" class="enrichment-candidate-actions">
              <button class="enrichment-button-secondary" @click="handleRejectFieldCandidate(candidate.id)">拒绝</button>
              <button class="enrichment-button-primary" @click="handleAcceptFieldCandidate(candidate.id)">采纳</button>
            </view>
          </view>
        </view>
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
import { buildLeadEnrichmentViewModel, createLeadEnrichmentService } from '../../services/leadEnrichment.js';
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
const enrichmentResultsPayload = ref({ items: [] });
const enrichmentLoading = ref(false);
const manualEnrichmentVisible = ref(false);
const manualFieldName = ref('');
const manualCandidateValue = ref('');
const manualEvidenceNote = ref('');
const enrichmentService = createLeadEnrichmentService({ apiClient });
const detail = computed(() => buildLeadDetailViewModel(leadState.value));
const enrichmentView = computed(() =>
  buildLeadEnrichmentViewModel({
    lead: {
      ...leadState.value,
      status: leadState.value.status,
      riskLevel: leadState.value.riskLevel,
    },
    resultsPayload: enrichmentResultsPayload.value,
  }),
);
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

  await refreshEnrichmentResults();
});

async function refreshEnrichmentResults() {
  if (!detail.value.id) {
    enrichmentResultsPayload.value = { items: [] };
    return;
  }

  try {
    enrichmentResultsPayload.value = await enrichmentService.listEnrichmentResults(detail.value.id);
  } catch (_error) {
    enrichmentResultsPayload.value = { items: [] };
  }
}

function notify(message) {
  if (globalThis.uni?.showToast) {
    globalThis.uni.showToast({ title: message, icon: 'none' });
  }
}

async function handleCreateEnrichmentRun() {
  if (!enrichmentView.value.canTriggerDeepEnrichment || enrichmentLoading.value) {
    return;
  }

  enrichmentLoading.value = true;
  try {
    await enrichmentService.createEnrichmentRun(detail.value.id, {
      actor: '当前用户',
      manualKeywords: [detail.value.customerName, detail.value.city].filter((item) => item && item !== 'Unknown'),
      note: '移动端人工触发深挖线索。',
    });
    await refreshEnrichmentResults();
    notify('已启动深挖');
  } catch (_error) {
    notify('深挖启动失败');
  } finally {
    enrichmentLoading.value = false;
  }
}

async function handleAcceptFieldCandidate(candidateId) {
  try {
    await enrichmentService.acceptFieldCandidate(candidateId, { actor: '当前用户' });
    await refreshEnrichmentResults();
    notify('已采纳候选');
  } catch (_error) {
    notify('采纳失败');
  }
}

async function handleRejectFieldCandidate(candidateId) {
  try {
    await enrichmentService.rejectFieldCandidate(candidateId, { reason: '移动端人工拒绝该候选字段' });
    await refreshEnrichmentResults();
    notify('已拒绝候选');
  } catch (_error) {
    notify('拒绝失败');
  }
}

function toggleManualEnrichmentForm() {
  manualEnrichmentVisible.value = !manualEnrichmentVisible.value;
}

async function handleCreateManualEnrichment() {
  const fieldName = manualFieldName.value.trim();
  const candidateValue = manualCandidateValue.value.trim();
  const evidenceNote = manualEvidenceNote.value.trim();
  if (!fieldName || !candidateValue || !evidenceNote) {
    notify('请补齐字段名、字段值和证据');
    return;
  }

  try {
    await enrichmentService.createManualEnrichment(detail.value.id, {
      operator: '当前用户',
      note: '移动端人工补录。',
      fields: [
        {
          fieldName,
          candidateValue,
          sourceType: 'manual_public_info',
          evidenceNote,
        },
      ],
    });
    manualFieldName.value = '';
    manualCandidateValue.value = '';
    manualEvidenceNote.value = '';
    manualEnrichmentVisible.value = false;
    await refreshEnrichmentResults();
    notify('已创建人工补录');
  } catch (_error) {
    notify('人工补录失败');
  }
}

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
    const result = await apiClient.post(`/staging-leads/${encodeURIComponent(detail.value.id)}/promote-to-customer`, buildPromoteStagingPayload({
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
