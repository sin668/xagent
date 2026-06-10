<template>
  <view class="lead-pool-page">
    <view class="status-bar">
      <text>9:41</text>
      <view class="status-icons">
        <text>5G</text>
        <text>Wi-Fi</text>
        <text>78%</text>
      </view>
    </view>

    <view class="nav-bar">
      <view>
        <view class="nav-title">线索池</view>
        <view class="nav-subtitle">移动端优先处理队列</view>
      </view>
      <view class="nav-action" aria-label="筛选">⌕</view>
    </view>

    <scroll-view scroll-y class="lead-pool-content">
      <view class="lead-summary-card source-summary-card">
        <view class="source-summary-top">
          <view>
            <view class="source-summary-title">线索联系方式概览</view>
            <view class="source-summary-meta">有邮箱联系线索 · 有社交媒体联系线索 · A/B/C级线索 · D/E级线索</view>
          </view>
          <text class="source-tag source-tag-blue">{{ leads.length }} 条</text>
        </view>

        <view class="source-map">
          <view
            v-for="stat in leadStats"
            :key="stat.key"
            :class="['source-tile', 'lead-summary-tile', activeFilter === stat.filterKey ? 'lead-summary-tile-active' : '']"
            @click="selectSummaryFilter(stat)"
          >
            <text class="source-kicker">{{ stat.label }}</text>
            <text :class="['source-number', stat.className]">{{ stat.count }}</text>
          </view>
        </view>
      </view>

      <view class="lead-action-strip">
        <button class="lead-action-button lead-action-button-primary" @click="openLeadSources">
          <text class="lead-action-icon">⌁</text>
          <text>线索来源</text>
        </button>
        <button class="lead-action-button lead-action-button-secondary" @click="openCleanedLeads">
          <text class="lead-action-icon">⊘</text>
          <text>被清洗线索</text>
        </button>
      </view>

      <view class="lead-list-head">
        <text class="section-title">{{ activeFilterTitle }}</text>
        <text class="section-note">{{ cards.length }} 条</text>
      </view>

      <view v-if="cards.length" class="lead-list">
        <view
          v-for="card in cards"
          :key="card.id"
          :class="['pool-card', card.isDoNotContact ? 'pool-card-dnc' : '']"
          @click="openLead(card.id)"
        >
          <view class="pool-card-top">
            <view>
              <view class="pool-lead-name">{{ card.customerName }}</view>
              <view class="pool-lead-meta">
                {{ card.locationLabel }} · {{ card.customerType }}
              </view>
            </view>
            <text :class="['pool-tag', card.gradeClass]">{{ card.gradeLabel }}</text>
          </view>

          <view class="pool-tag-row">
            <text :class="['pool-tag', card.riskClass]">{{ card.riskLabel }}</text>
            <text class="pool-tag pool-tag-blue">{{ card.handoffLabel }}</text>
            <text v-if="card.complianceLabel" class="pool-tag pool-tag-red">{{ card.complianceLabel }}</text>
            <text v-if="card.isOverdue" class="pool-tag pool-tag-amber">SLA 超时</text>
            <text v-if="card.isDoNotContact" class="pool-tag pool-tag-red">勿扰</text>
            <text v-for="marker in card.riskMarkers" :key="`${card.id}-${marker}`" class="pool-tag pool-tag-red">
              {{ marker }}
            </text>
          </view>

          <view v-if="card.contacts.length" class="lead-info-section">
            <text class="lead-section-title">联系方式</text>
            <view class="lead-contact-list">
              <text v-for="contact in card.contacts" :key="`${card.id}-${contact.type}-${contact.value}`" class="lead-contact-pill">
                {{ contact.type }} · {{ contact.value }}
              </text>
            </view>
          </view>

          <view v-if="card.aiAdvice" class="lead-info-section lead-info-section-warm">
            <text class="lead-section-title">AI建议</text>
            <text class="lead-clamped-copy">{{ clipText(card.aiAdvice) }}</text>
          </view>

          <view v-if="manualFormLeadId === card.id" class="lead-inline-form" @click.stop>
            <input v-model="manualFieldName" class="lead-inline-input" placeholder="补录字段，如 customer_name" />
            <input v-model="manualCandidateValue" class="lead-inline-input" placeholder="补录内容" />
            <input v-model="manualEvidenceNote" class="lead-inline-input" placeholder="证据备注" />
            <button class="lead-inline-submit" @click.stop="submitManualEnrichment(card)">提交补录</button>
          </view>

          <view v-if="card.actions.length" class="lead-card-actions" @click.stop>
            <button
              v-for="action in card.actions"
              :key="`${card.id}-${action.key}`"
              class="lead-card-action"
              @click.stop="openLeadAction(card, action)"
            >
              {{ action.label }}
            </button>
          </view>
        </view>
      </view>
      <view v-else class="empty-state">当前筛选下没有可处理线索</view>
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
  </view>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';

import { mapStagingLeadListToLeadPool } from '../../services/apiAdapters.js';
import { apiClient } from '../../services/apiClient.js';
import { buildBottomTabs, navigateBottomTab } from '../../services/bottomTabs.js';
import { buildPromoteStagingPayload } from '../../services/leadDetail.js';
import { buildManualEnrichmentPayload } from '../../services/leadEnrichment.js';
import { buildLeadPoolStats, filterLeadPool, getLeadCardViewModel } from '../../services/leadPool.js';
import '../../styles/home.css';
import '../../styles/leadPool.css';
import '../../styles/sourceCandidates.css';

const activeFilter = ref('all');
const leads = ref([]);
const leadStats = computed(() => buildLeadPoolStats(leads.value));
const cards = computed(() => filterLeadPool(leads.value, activeFilter.value).map(getLeadCardViewModel));
const manualFormLeadId = ref('');
const manualFieldName = ref('');
const manualCandidateValue = ref('');
const manualEvidenceNote = ref('');
const activeFilterTitle = computed(() => {
  if (activeFilter.value === 'all') {
    return '全部线索';
  }
  return leadStats.value.find((stat) => stat.filterKey === activeFilter.value)?.label || '筛选线索';
});

const bottomTabs = buildBottomTabs('leads');

onMounted(async () => {
  try {
    await reloadLeads();
  } catch (_error) {
    leads.value = [];
  }
});

async function reloadLeads() {
  const stagingPayload = await apiClient.get('/staging-leads?limit=500');
  leads.value = mapStagingLeadListToLeadPool(stagingPayload);
}

function selectSummaryFilter(stat) {
  activeFilter.value = activeFilter.value === stat.filterKey ? 'all' : stat.filterKey;
}

function clipText(value, maxLength = 96) {
  const text = String(value || '').trim();
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, maxLength)}......`;
}

function openLead(id) {
  if (!id || !globalThis.uni?.navigateTo) {
    return;
  }

  globalThis.uni.navigateTo({ url: `/pages/leads/detail?id=${encodeURIComponent(id)}` });
}

async function openLeadAction(card, action) {
  if (action.key === 'manual-enrich') {
    manualFormLeadId.value = manualFormLeadId.value === card.id ? '' : card.id;
    return;
  }
  if (action.key === 'ai-outreach' && action.path && globalThis.uni?.navigateTo) {
    globalThis.uni.navigateTo({ url: action.path });
    return;
  }
  if (action.key === 'mark-dnc') {
    await markLeadDoNotContactInline(card);
    return;
  }
  if (action.key === 'promote') {
    await promoteLeadInline(card);
  }
}

async function markLeadDoNotContactInline(card) {
  await apiClient.post(`/customers/${encodeURIComponent(card.id)}/do-not-contact`, {
    actor: '当前用户',
    reason: '移动端线索池人工标记勿扰',
  });
  await reloadLeads();
}

async function promoteLeadInline(card) {
  await apiClient.post(`/staging-leads/${encodeURIComponent(card.id)}/promote-to-customer`, buildPromoteStagingPayload({
    actor: '当前用户',
    reviewNote: '移动端线索池人工复核通过，准入闸门允许晋级 core。',
  }));
  await reloadLeads();
}

async function submitManualEnrichment(card) {
  if (!manualFieldName.value.trim() || !manualCandidateValue.value.trim() || !manualEvidenceNote.value.trim()) {
    return;
  }
  await apiClient.post(`/staging-leads/${encodeURIComponent(card.id)}/manual-enrichment`, buildManualEnrichmentPayload({
    operator: '当前用户',
    note: '移动端线索池人工补录。',
    fields: [{
      fieldName: manualFieldName.value.trim(),
      candidateValue: manualCandidateValue.value.trim(),
      evidenceNote: manualEvidenceNote.value.trim(),
      sourceType: 'mobile_manual_review',
      confidenceScore: 1,
    }],
  }));
  manualFormLeadId.value = '';
  manualFieldName.value = '';
  manualCandidateValue.value = '';
  manualEvidenceNote.value = '';
  await reloadLeads();
}

function openLeadSources() {
  if (!globalThis.uni?.navigateTo) {
    return;
  }

  globalThis.uni.navigateTo({ url: '/pages/sources/index' });
}

function openCleanedLeads() {
  if (!globalThis.uni?.navigateTo) {
    return;
  }

  globalThis.uni.navigateTo({ url: '/pages/leads/cleaned' });
}

function openTab(tab) {
  navigateBottomTab(tab);
}
</script>
