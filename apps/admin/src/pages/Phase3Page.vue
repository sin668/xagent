<template>
  <section id="phase3" class="admin-card phase3-card">
    <div class="card-head">
      <div>
        <h3>第三阶段指标与风控</h3>
        <span>客户承接、线索深挖补全、清洗治理和风险违规目标 0</span>
      </div>
      <span :class="['tag', statusClass]">{{ statusText }}</span>
    </div>
    <p v-if="errorMessage" class="guardrail">{{ errorMessage }}</p>
    <p v-else-if="isLoading" class="guardrail">正在加载第三阶段真实 API 指标...</p>
    <div class="phase3-summary">
      <article><strong>{{ phase3.customerAcceptance.effectiveCustomerAcceptanceRateText }}</strong><span>有效客户承接率</span><small>{{ phase3.customerAcceptance.acceptedFirstFollowupCount }} / {{ phase3.customerAcceptance.promotedCustomerCount }} 已首次跟进</small></article>
      <article><strong>{{ phase3.enrichment.enrichmentSuccessRateText }}</strong><span>深挖补全成功率</span><small>{{ phase3.enrichment.succeededEnrichmentCount }} / {{ phase3.enrichment.enrichmentResultCount }} AI 补全成功</small></article>
      <article><strong>{{ phase3.enrichment.promotionRateText }}</strong><span>客户晋级率</span><small>{{ phase3.enrichment.promotedCustomerCount }} / {{ phase3.enrichment.stagingLeadCount }} staging 晋级</small></article>
      <article :class="['risk-target-card', phase3.risk.statusClass]"><strong>{{ phase3.risk.riskViolationCount }}</strong><span>风险违规目标 0</span><small>{{ phase3.risk.targetText }} · {{ phase3.risk.statusText }}</small></article>
    </div>
    <div class="phase3-split">
      <section>
        <div class="card-head compact-head"><h4>线索完善与客户管理</h4><span>人工确认后进入客户管理</span></div>
        <div class="phase3-metric-grid">
          <article><strong>{{ phase3.enrichment.fieldAdoptionRateText }}</strong><span>字段采纳率</span><p>{{ phase3.enrichment.acceptedFieldCount }} / {{ phase3.enrichment.fieldCandidateCount }} 个字段候选被人工采纳</p></article>
          <article><strong>{{ phase3.enrichment.contactCompletenessRateText }}</strong><span>联系方式完整率</span><p>{{ phase3.enrichment.contactCompleteCustomerCount }} 个客户具备有效联系方式</p></article>
          <article><strong>{{ phase3.enrichment.vehicleIntentRateText }}</strong><span>意向车型覆盖率</span><p>{{ phase3.enrichment.vehicleIntentCustomerCount }} 个客户已有意向车型记录</p></article>
        </div>
      </section>
      <section>
        <div class="card-head compact-head"><h4>清洗治理</h4><span>建议不等于执行，必须人工确认</span></div>
        <div class="phase3-cleanup-list">
          <article><strong>{{ phase3.cleanup.adoptionRateText }}</strong><span>建议采纳率</span><p>{{ phase3.cleanup.approvedCount }} / {{ phase3.cleanup.createdCount }} 条建议已通过</p></article>
          <article><strong>{{ phase3.cleanup.duplicateMergeRateText }}</strong><span>重复归并率</span><p>{{ phase3.cleanup.duplicateMergeCount }} 条重复线索由人工执行归并</p></article>
          <article><strong>{{ phase3.cleanup.watchRestoreRateText }}</strong><span>D 级恢复率</span><p>{{ phase3.cleanup.watchRestoreCount }} 条 Watch 线索经人工恢复</p></article>
        </div>
      </section>
    </div>
    <div class="phase3-guardrail-grid">
      <article><strong>客户触达</strong><span :class="['tag', phase3.guardrails.autoOutreachAllowed ? 'red' : 'green']">{{ phase3.guardrails.autoOutreachAllowed ? '异常开启' : '仅人工' }}</span></article>
      <article><strong>好友请求</strong><span :class="['tag', phase3.guardrails.autoFriendRequestAllowed ? 'red' : 'green']">{{ phase3.guardrails.autoFriendRequestAllowed ? '异常开启' : '禁止' }}</span></article>
      <article><strong>登录批量采集禁用</strong><span :class="['tag', phase3.guardrails.loginBatchCollectionAllowed ? 'red' : 'green']">{{ phase3.guardrails.loginBatchCollectionAllowed ? '异常开启' : '已禁用' }}</span></article>
    </div>
    <p class="guardrail">第三阶段只展示指标和风控状态；AI 不得自动晋级客户、自动归并客户、自动恢复 Invalid，客户触达必须人工确认。</p>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';

import { buildPhase3DashboardView, fetchPhase3Dashboard } from '../services/phase3Dashboard.js';
import { apiBaseUrl, formatLoadError } from './pageRuntime.js';

const payload = ref(null);
const isLoading = ref(true);
const errorMessage = ref('');
const phase3 = computed(() => buildPhase3DashboardView(payload.value || {}));
const statusText = computed(() => {
  if (isLoading.value) return '加载中';
  if (errorMessage.value) return 'API 异常';
  return phase3.value.risk.riskViolationTargetZero ? '风险达标' : '需处理';
});
const statusClass = computed(() => {
  if (isLoading.value) return 'amber';
  if (errorMessage.value || !phase3.value.risk.riskViolationTargetZero) return 'red';
  return 'green';
});

onMounted(async () => {
  try {
    payload.value = await fetchPhase3Dashboard({ baseUrl: apiBaseUrl });
  } catch (error) {
    errorMessage.value = formatLoadError('无法加载第三阶段真实 API 指标', error);
  } finally {
    isLoading.value = false;
  }
});
</script>
