<template>
  <div class="admin-shell">
    <aside class="sidebar">
      <h1>XAgent CRM</h1>
      <nav class="side-nav">
        <a class="active" href="#overview">总览</a>
        <a href="#channels">渠道</a>
        <a href="#risk-config">风险配置</a>
        <a href="#queues">队列</a>
        <a href="#risk-audit">审计</a>
        <a href="#sync-audit">同步</a>
        <a href="#phase2">第二阶段</a>
        <a href="#phase3">第三阶段</a>
        <a href="#prompt-governance">Prompt 治理</a>
        <a href="#llm-governance">LLM 治理</a>
      </nav>
    </aside>
    <main id="overview" class="admin-main">
      <header class="admin-top">
        <div>
          <h2>后台总览</h2>
          <p>候选线索、团队队列、SLA 风险与阻断任务集中看板</p>
        </div>
        <span class="tag green">MVP 试运行</span>
      </header>

      <section class="admin-grid-cards">
        <article class="admin-card">
          <strong>{{ overview.summary.candidateCount }}</strong>
          <span>候选线索</span>
        </article>
        <article class="admin-card">
          <strong>{{ overview.summary.bcGradeCount }}</strong>
          <span>B/C 级线索</span>
        </article>
        <article class="admin-card">
          <strong>{{ overview.summary.responseRateText }}</strong>
          <span>回复率</span>
        </article>
        <article class="admin-card">
          <strong>{{ overview.summary.slaRiskCount }}</strong>
          <span>SLA 风险</span>
        </article>
      </section>

      <section id="channels" class="admin-card channel-card">
        <div class="card-head">
          <h3>渠道产出</h3>
          <span>按 B/C 级线索排序</span>
        </div>
        <table class="table">
          <thead>
            <tr>
              <th>渠道</th>
              <th>风险</th>
              <th>状态</th>
              <th>候选</th>
              <th>B/C</th>
              <th>无效率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="channel in overview.channelOutputs" :key="channel.channelName">
              <td>{{ channel.displayName }}</td>
              <td>
                <span :class="['tag', channel.riskLevel === 'Low' ? 'green' : channel.riskLevel === 'Medium' ? 'amber' : 'red']">
                  {{ channel.riskLabel }}
                </span>
              </td>
              <td>{{ channel.statusLabel }}</td>
              <td>{{ channel.candidateCount }}</td>
              <td>{{ channel.bcText }}</td>
              <td>{{ channel.invalidRateText }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section id="risk-config" class="admin-card risk-config-card">
        <div class="card-head">
          <h3>渠道风险配置</h3>
          <span>允许动作、禁止动作、政策来源和变更留痕</span>
        </div>
        <table class="table">
          <thead>
            <tr>
              <th>渠道</th>
              <th>风险</th>
              <th>允许动作</th>
              <th>禁止动作</th>
              <th>政策来源</th>
              <th>变更人</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="rule in riskConfig.rules" :key="rule.channelName">
              <td>{{ rule.channelName }}</td>
              <td>
                <span :class="['tag', rule.riskLevel === 'Low' ? 'green' : rule.riskLevel === 'Medium' ? 'amber' : 'red']">
                  {{ rule.riskLabel }}
                </span>
              </td>
              <td>{{ rule.allowedActions }}</td>
              <td>{{ rule.forbiddenActions }}</td>
              <td class="source-cell">{{ rule.policySourceUrl }}</td>
              <td>{{ rule.updatedBy }}</td>
              <td>{{ rule.statusLabel }}</td>
            </tr>
          </tbody>
        </table>
        <div class="blocked-reasons">
          <article v-for="rule in riskConfig.blockedRules" :key="`${rule.channelName}-blocked`">
            <strong>{{ rule.channelName }}</strong>
            <span>{{ rule.blockReason }}</span>
          </article>
        </div>
      </section>

      <section id="sync-audit" class="admin-card sync-audit-card">
        <div class="card-head">
          <h3>飞书同步与 AI 审计</h3>
          <span>最近同步 {{ syncAudit.summary.latestSyncAt || '暂无' }}</span>
        </div>
        <div class="sync-audit-grid">
          <div>
            <strong>{{ syncAudit.summary.syncSuccessCount }}</strong>
            <span>同步成功</span>
          </div>
          <div>
            <strong>{{ syncAudit.summary.syncFailureCount }}</strong>
            <span>同步失败</span>
          </div>
          <div>
            <strong>{{ syncAudit.summary.aiTaskCount }}</strong>
            <span>AI 审计日志</span>
          </div>
          <div>
            <strong>{{ syncAudit.summary.aiBlockedCount }}</strong>
            <span>被阻断任务</span>
          </div>
        </div>
        <div class="audit-columns">
          <section>
            <h4>同步日志</h4>
            <article v-for="item in syncAudit.syncLogs" :key="item.id" class="audit-row">
              <div>
                <strong>{{ item.objectName }}</strong>
                <span>{{ item.successCount }} 成功 / {{ item.failureCount }} 失败</span>
              </div>
              <p>{{ item.errorSummary || item.statusLabel }}</p>
            </article>
          </section>
          <section>
            <h4>AI 执行审计</h4>
            <article v-for="item in syncAudit.aiAuditLogs" :key="item.id" class="audit-row">
              <div>
                <strong>{{ item.taskType }}</strong>
                <span>{{ item.modelName }} · {{ item.promptVersion }}</span>
              </div>
              <p>{{ item.riskBlockReason || item.statusLabel }}</p>
            </article>
          </section>
        </div>
      </section>

      <section id="queues" class="admin-card queue-card">
        <div class="card-head">
          <h3>今日队列</h3>
          <span>{{ overview.queueSummaryText }}</span>
        </div>
        <div class="queue-grid">
          <article class="queue-column">
            <strong>{{ overview.teamQueues.operations.count }}</strong>
            <span>运营待复核</span>
            <p v-for="item in overview.teamQueues.operations.items" :key="item.customerId">
              {{ item.customerName }} · {{ item.grade }} · {{ item.owner }}
            </p>
          </article>
          <article class="queue-column">
            <strong>{{ overview.teamQueues.customerService.count }}</strong>
            <span>客服待跟进</span>
            <p v-for="item in overview.teamQueues.customerService.items" :key="item.customerId">
              {{ item.customerName }} · {{ item.grade }} · {{ item.owner }}
            </p>
          </article>
          <article class="queue-column">
            <strong>{{ overview.teamQueues.sales.count }}</strong>
            <span>销售待承接</span>
            <p v-for="item in overview.teamQueues.sales.items" :key="item.customerId">
              {{ item.customerName }} · {{ item.grade }} · {{ item.owner }}
            </p>
          </article>
        </div>
      </section>

      <section id="risk-audit" class="admin-card risk-card">
        <div class="card-head">
          <h3>风险事件与阻断任务</h3>
          <span>管理者必须可见阻断原因</span>
        </div>
        <div class="risk-list">
          <article v-for="event in overview.riskEvents" :key="event.id" class="risk-row">
            <div>
              <strong>{{ event.taskType }}</strong>
              <span>{{ event.sourceUrl || '无来源链接' }}</span>
            </div>
            <p>{{ event.riskBlockReason || '未填写阻断原因' }}</p>
          </article>
        </div>
        <p class="guardrail">High/Forbidden 渠道和勿扰客户不得进入自动化触达；C 级线索报价或合同前必须合规复核。</p>
      </section>

      <section id="phase2" class="admin-card phase2-card">
        <div class="card-head">
          <div>
            <h3>第二阶段小范围运行看板</h3>
            <span>Source Discovery -> 来源审核 -> LEAD_EXTRACTION -> staging/core</span>
          </div>
          <span :class="['tag', phase2StatusClass]">{{ phase2StatusText }}</span>
        </div>

        <p v-if="phase2Error" class="guardrail">{{ phase2Error }}</p>

        <div class="phase2-summary">
          <article>
            <strong>{{ phase2.summary.sourceCandidateCount }}</strong>
            <span>来源新增</span>
          </article>
          <article>
            <strong>{{ phase2.summary.extractableSourceCount }}</strong>
            <span>可抽取来源</span>
          </article>
          <article class="danger-metric">
            <strong>{{ phase2.summary.highReviewBacklogCount }}</strong>
            <span>High 待审</span>
          </article>
          <article>
            <strong>{{ phase2.summary.llmCostText }}</strong>
            <span>LLM 成本</span>
          </article>
        </div>

        <div class="phase2-flow">
          <article v-for="node in phase2.taskFlow" :key="node.title" class="phase2-flow-node">
            <strong>{{ node.title }}</strong>
            <span>{{ node.metricText }}</span>
            <p>{{ node.description }}</p>
          </article>
        </div>

        <div class="phase2-split">
          <section>
            <div class="card-head compact-head">
              <h4>Agent Task Runs</h4>
              <span>真实 API 审计事实</span>
            </div>
            <table class="table">
              <thead>
                <tr>
                  <th>Run</th>
                  <th>任务</th>
                  <th>模型</th>
                  <th>状态</th>
                  <th>输出</th>
                  <th>成本</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="run in phase2.llmTaskRuns" :key="run.runId">
                  <td>{{ run.runId || '-' }}</td>
                  <td>{{ run.taskType }}</td>
                  <td>{{ run.provider }}</td>
                  <td><span :class="['tag', run.statusClass]">{{ run.statusLabel }}</span></td>
                  <td>{{ run.outputText }}</td>
                  <td>{{ run.costText }}</td>
                </tr>
                <tr v-if="phase2.llmTaskRuns.length === 0">
                  <td colspan="6">暂无真实 LLM 任务成本数据</td>
                </tr>
              </tbody>
            </table>
          </section>

          <section>
            <div class="card-head compact-head">
              <h4>自动暂停阈值</h4>
              <span>触发后停止自动任务</span>
            </div>
            <div class="pause-list">
              <article v-for="threshold in phase2PauseThresholds" :key="threshold.label">
                <div>
                  <strong>{{ threshold.label }}</strong>
                  <span>{{ threshold.text || `${threshold.current} / ${threshold.limit}` }}</span>
                </div>
                <div class="progress"><span :class="threshold.className" :style="{ width: `${threshold.percent}%` }"></span></div>
              </article>
            </div>
          </section>
        </div>

        <div class="phase2-risk-list">
          <div class="card-head compact-head">
            <h4>High/Forbidden 风险事件</h4>
            <span>{{ phase2.summary.highForbiddenRiskEventCount }} 个高风险事件</span>
          </div>
          <article v-for="event in phase2.highForbiddenRiskEvents" :key="event.id" class="risk-row">
            <div>
              <strong>{{ event.channel }}</strong>
              <span>{{ event.eventType }} · {{ event.createdAt }}</span>
            </div>
            <p>
              <span :class="['tag', event.highlightClass]">{{ event.riskLabel }}</span>
              {{ event.blockReason }}
            </p>
          </article>
          <p v-if="phase2.highForbiddenRiskEvents.length === 0" class="empty-note">暂无 High/Forbidden 风险事件。</p>
        </div>

        <p class="guardrail">{{ phase2.guardrail }}</p>
      </section>

      <section id="phase3" class="admin-card phase3-card">
        <div class="card-head">
          <div>
            <h3>第三阶段指标与风控</h3>
            <span>客户承接、线索深挖补全、清洗治理和风险违规目标 0</span>
          </div>
          <span :class="['tag', phase3StatusClass]">{{ phase3StatusText }}</span>
        </div>

        <p v-if="phase3Error" class="guardrail">{{ phase3Error }}</p>

        <div class="phase3-summary">
          <article>
            <strong>{{ phase3.customerAcceptance.effectiveCustomerAcceptanceRateText }}</strong>
            <span>有效客户承接率</span>
            <small>{{ phase3.customerAcceptance.acceptedFirstFollowupCount }} / {{ phase3.customerAcceptance.promotedCustomerCount }} 已首次跟进</small>
          </article>
          <article>
            <strong>{{ phase3.enrichment.enrichmentSuccessRateText }}</strong>
            <span>深挖补全成功率</span>
            <small>{{ phase3.enrichment.succeededEnrichmentCount }} / {{ phase3.enrichment.enrichmentResultCount }} AI 补全成功</small>
          </article>
          <article>
            <strong>{{ phase3.enrichment.promotionRateText }}</strong>
            <span>客户晋级率</span>
            <small>{{ phase3.enrichment.promotedCustomerCount }} / {{ phase3.enrichment.stagingLeadCount }} staging 晋级</small>
          </article>
          <article :class="['risk-target-card', phase3.risk.statusClass]">
            <strong>{{ phase3.risk.riskViolationCount }}</strong>
            <span>风险违规目标 0</span>
            <small>{{ phase3.risk.targetText }} · {{ phase3.risk.statusText }}</small>
          </article>
        </div>

        <div class="phase3-split">
          <section>
            <div class="card-head compact-head">
              <h4>线索完善与客户管理</h4>
              <span>从 staging 完善区人工确认后进入客户管理</span>
            </div>
            <div class="phase3-metric-grid">
              <article>
                <strong>{{ phase3.enrichment.fieldAdoptionRateText }}</strong>
                <span>字段采纳率</span>
                <p>{{ phase3.enrichment.acceptedFieldCount }} / {{ phase3.enrichment.fieldCandidateCount }} 个字段候选被人工采纳</p>
              </article>
              <article>
                <strong>{{ phase3.enrichment.contactCompletenessRateText }}</strong>
                <span>联系方式完整率</span>
                <p>{{ phase3.enrichment.contactCompleteCustomerCount }} 个客户具备有效联系方式</p>
              </article>
              <article>
                <strong>{{ phase3.enrichment.vehicleIntentRateText }}</strong>
                <span>意向车型覆盖率</span>
                <p>{{ phase3.enrichment.vehicleIntentCustomerCount }} 个客户已有意向车型记录</p>
              </article>
            </div>
          </section>

          <section>
            <div class="card-head compact-head">
              <h4>清洗治理</h4>
              <span>建议不等于执行，必须人工确认</span>
            </div>
            <div class="phase3-cleanup-list">
              <article>
                <strong>{{ phase3.cleanup.adoptionRateText }}</strong>
                <span>建议采纳率</span>
                <p>{{ phase3.cleanup.approvedCount }} / {{ phase3.cleanup.createdCount }} 条建议已通过</p>
              </article>
              <article>
                <strong>{{ phase3.cleanup.duplicateMergeRateText }}</strong>
                <span>重复归并率</span>
                <p>{{ phase3.cleanup.duplicateMergeCount }} 条重复线索由人工执行归并</p>
              </article>
              <article>
                <strong>{{ phase3.cleanup.watchRestoreRateText }}</strong>
                <span>D 级恢复率</span>
                <p>{{ phase3.cleanup.watchRestoreCount }} 条 Watch 线索经人工恢复</p>
              </article>
            </div>
          </section>
        </div>

        <div class="phase3-guardrail-grid">
          <article>
            <strong>客户触达</strong>
            <span :class="['tag', phase3.guardrails.autoOutreachAllowed ? 'red' : 'green']">
              {{ phase3.guardrails.autoOutreachAllowed ? '异常开启' : '仅人工' }}
            </span>
          </article>
          <article>
            <strong>好友请求</strong>
            <span :class="['tag', phase3.guardrails.autoFriendRequestAllowed ? 'red' : 'green']">
              {{ phase3.guardrails.autoFriendRequestAllowed ? '异常开启' : '禁止' }}
            </span>
          </article>
          <article>
            <strong>登录批量采集禁用</strong>
            <span :class="['tag', phase3.guardrails.loginBatchCollectionAllowed ? 'red' : 'green']">
              {{ phase3.guardrails.loginBatchCollectionAllowed ? '异常开启' : '已禁用' }}
            </span>
          </article>
        </div>

        <p class="guardrail">第三阶段只展示指标和风控状态；AI 不得自动晋级客户、自动归并客户、自动恢复 Invalid，客户触达必须人工确认。</p>
      </section>

      <section id="prompt-governance" class="admin-card prompt-governance-card">
        <div class="card-head">
          <div>
            <h3>Prompt 全量入库与版本治理</h3>
            <span>文件保留为基线，运行时读取数据库 active default；草稿校验、发布和回滚全审计</span>
          </div>
          <span :class="['tag', promptGovernance.summary.coverageStatusClass]">覆盖率 {{ promptGovernance.summary.coverageRateText }}</span>
        </div>

        <p v-if="promptGovernanceError" class="guardrail">{{ promptGovernanceError }}</p>

        <div class="prompt-summary">
          <article>
            <strong>{{ promptGovernance.summary.importedPromptCount }}</strong>
            <span>已入库 Prompt</span>
          </article>
          <article>
            <strong>{{ promptGovernance.summary.activeDefaultCount }}</strong>
            <span>active default</span>
          </article>
          <article>
            <strong>{{ promptGovernance.summary.draftValidationPendingCount }}</strong>
            <span>草稿待校验</span>
          </article>
          <article>
            <strong>{{ promptGovernance.summary.schemaErrorCount }}</strong>
            <span>schema error</span>
          </article>
        </div>

        <div class="prompt-governance-grid">
          <section>
            <div class="card-head compact-head">
              <h4>Prompt 版本</h4>
              <span>来源 hash、校验状态、默认版本</span>
            </div>
            <table class="table">
              <thead>
                <tr>
                  <th>名称</th>
                  <th>任务</th>
                  <th>版本</th>
                  <th>状态</th>
                  <th>来源 hash</th>
                  <th>校验</th>
                  <th>默认</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="template in promptGovernance.templates" :key="template.id">
                  <td>{{ template.name }}</td>
                  <td>{{ template.taskType }}</td>
                  <td>{{ template.version }}</td>
                  <td><span :class="['tag', template.statusClass]">{{ template.statusLabel }}</span></td>
                  <td>{{ template.sourceHashShort }}</td>
                  <td>{{ template.validationStatusLabel }}</td>
                  <td>{{ template.defaultLabel }}</td>
                </tr>
                <tr v-if="promptGovernance.templates.length === 0">
                  <td colspan="7">暂无真实 Prompt 入库数据</td>
                </tr>
              </tbody>
            </table>
          </section>

          <section>
            <div class="card-head compact-head">
              <h4>草稿校验与操作入口</h4>
              <span>{{ promptGovernance.canPublish ? '管理员受控操作' : '权限不足已禁用' }}</span>
            </div>
            <div class="prompt-action-list">
              <article v-for="entry in promptGovernance.actionEntrypoints" :key="entry.label">
                <strong>{{ entry.label }}</strong>
                <span :class="['tag', entry.enabled ? 'blue' : 'amber']">{{ entry.enabled ? '可操作' : '禁用' }}</span>
              </article>
            </div>
            <p class="guardrail">{{ promptGovernance.permissionNotice }}</p>
          </section>
        </div>

        <section class="schema-preview">
          <div class="card-head compact-head">
            <h4>校验失败摘要</h4>
            <span>用于发布前修正</span>
          </div>
          <pre>{{ promptValidationErrorsText }}</pre>
        </section>
      </section>

      <section id="llm-governance" class="admin-card llm-card">
        <div class="card-head">
          <div>
            <h3>LLM Provider 与 Prompt Schema</h3>
            <span>Provider 健康、prompt/schema 版本、fallback 边界和只读治理</span>
          </div>
          <span :class="['tag', llmStatusClass]">{{ llmStatusText }}</span>
        </div>

        <p v-if="llmError" class="guardrail">{{ llmError }}</p>

        <div class="provider-grid">
          <article class="provider-card">
            <strong>{{ llmGovernance.providerHealth.providerName }}</strong>
            <small>{{ llmGovernance.providerHealth.modelSummary || '暂无模型配置' }}</small>
            <span :class="['tag', llmGovernance.providerHealth.statusClass]">{{ llmGovernance.providerHealth.statusLabel }}</span>
          </article>
          <article class="provider-card">
            <strong>Base URL</strong>
            <small>仅展示配置状态，不展示具体密钥或敏感配置</small>
            <span :class="['tag', llmGovernance.providerHealth.baseUrlConfigured ? 'green' : 'amber']">
              {{ llmGovernance.providerHealth.baseUrlConfigured ? 'configured' : 'missing' }}
            </span>
          </article>
          <article class="provider-card">
            <strong>API Key</strong>
            <small>页面只显示是否已配置，禁止展示 API key 原文</small>
            <span :class="['tag', llmGovernance.providerHealth.apiKeyConfigured ? 'green' : 'amber']">
              {{ llmGovernance.providerHealth.apiKeyConfigured ? 'configured' : 'missing' }}
            </span>
          </article>
          <article class="provider-card">
            <strong>Read Only</strong>
            <small>{{ llmGovernance.readOnlyNotice }}</small>
            <span class="tag blue">governance</span>
          </article>
        </div>

        <div class="llm-split">
          <section>
            <div class="card-head compact-head">
              <h4>Prompt Template 版本</h4>
              <span>仅管理员维护</span>
            </div>
            <table class="table">
              <thead>
                <tr>
                  <th>名称</th>
                  <th>任务</th>
                  <th>Provider</th>
                  <th>版本</th>
                  <th>状态</th>
                  <th>Schema</th>
                  <th>默认</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="template in llmGovernance.promptTemplates" :key="template.id">
                  <td>{{ template.name }}</td>
                  <td>{{ template.taskType }}</td>
                  <td>{{ template.provider }} / {{ template.model }}</td>
                  <td>{{ template.version }}</td>
                  <td><span :class="['tag', template.statusClass]">{{ template.statusLabel }}</span></td>
                  <td>{{ template.schemaSummary }}</td>
                  <td>{{ template.defaultLabel }}</td>
                </tr>
                <tr v-if="llmGovernance.promptTemplates.length === 0">
                  <td colspan="7">暂无真实 prompt template 数据</td>
                </tr>
              </tbody>
            </table>
          </section>

          <section>
            <div class="card-head compact-head">
              <h4>Fallback 边界</h4>
              <span>合规失败不得 fallback</span>
            </div>
            <div class="fallback-list">
              <article v-for="item in llmGovernance.fallbackBoundaries" :key="item.condition">
                <strong>{{ item.condition }}</strong>
                <span :class="['tag', item.className]">{{ item.decisionLabel }}</span>
              </article>
            </div>
          </section>
        </div>

        <section class="schema-preview">
          <div class="card-head compact-head">
            <h4>{{ llmGovernance.schemaPreview.name }} 输出 Schema</h4>
            <span>{{ llmGovernance.schemaPreview.version || '无版本' }}</span>
          </div>
          <pre>{{ llmGovernance.schemaPreview.schemaText }}</pre>
        </section>

        <p class="guardrail">{{ llmGovernance.readOnlyNotice }} 页面不展示 API key、secret 或完整敏感连接配置。</p>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';

import { adminOverviewSeed } from './data/adminOverviewSeed.js';
import { channelRiskConfigSeed } from './data/channelRiskConfigSeed.js';
import { syncAiAuditSeed } from './data/syncAiAuditSeed.js';
import { buildAdminOverviewView } from './services/adminOverview.js';
import { buildChannelRiskConfigView } from './services/channelRiskConfig.js';
import { buildLlmGovernanceView, buildPromptGovernanceView, fetchLlmGovernance, fetchPromptGovernance } from './services/llmGovernance.js';
import { buildPhase2DashboardView, fetchPhase2Dashboard } from './services/phase2Dashboard.js';
import { buildPhase3DashboardView, fetchPhase3Dashboard } from './services/phase3Dashboard.js';
import { buildSyncAiAuditView } from './services/syncAiAudit.js';

const overview = computed(() => buildAdminOverviewView(adminOverviewSeed));
const riskConfig = computed(() => buildChannelRiskConfigView(channelRiskConfigSeed));
const syncAudit = computed(() => buildSyncAiAuditView(syncAiAuditSeed));
const phase2Payload = ref(null);
const phase2Loading = ref(true);
const phase2Error = ref('');
const phase3Payload = ref(null);
const phase3Loading = ref(true);
const phase3Error = ref('');
const llmGovernancePayload = ref(null);
const llmLoading = ref(true);
const llmError = ref('');
const promptGovernancePayload = ref(null);
const promptGovernanceLoading = ref(true);
const promptGovernanceError = ref('');
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '';
const adminActorRole = import.meta.env.VITE_ADMIN_ACTOR_ROLE || 'operator';

const phase2 = computed(() => buildPhase2DashboardView(phase2Payload.value || {}));
const phase3 = computed(() => buildPhase3DashboardView(phase3Payload.value || {}));
const llmGovernance = computed(() => buildLlmGovernanceView(llmGovernancePayload.value || {}));
const promptGovernance = computed(() => buildPromptGovernanceView({
  templates: promptGovernancePayload.value?.templates || {},
  actorRole: promptGovernancePayload.value?.actorRole || adminActorRole,
}));
const promptValidationErrorsText = computed(() => {
  const failed = promptGovernance.value.templates.filter((template) => template.validationErrorsText);
  if (failed.length === 0) return '暂无 schema 校验失败。';
  return failed.map((template) => `${template.name}: ${template.validationErrorsText}`).join('\n');
});
const phase2PauseThresholds = computed(() => Object.values(phase2.value.pauseThresholds));
const phase2StatusText = computed(() => {
  if (phase2Loading.value) return '加载中';
  if (phase2Error.value) return 'API 异常';
  if (phase2.value.summary.highForbiddenRiskEventCount > 0) return '需复核';
  return '运行中';
});
const phase2StatusClass = computed(() => {
  if (phase2Error.value || phase2.value.summary.highForbiddenRiskEventCount > 0) return 'red';
  if (phase2Loading.value) return 'amber';
  return 'green';
});
const phase3StatusText = computed(() => {
  if (phase3Loading.value) return '加载中';
  if (phase3Error.value) return 'API 异常';
  return phase3.value.risk.riskViolationTargetZero ? '风险达标' : '需处理';
});
const phase3StatusClass = computed(() => {
  if (phase3Loading.value) return 'amber';
  if (phase3Error.value || !phase3.value.risk.riskViolationTargetZero) return 'red';
  return 'green';
});
const llmStatusText = computed(() => {
  if (llmLoading.value) return '加载中';
  if (llmError.value) return 'API 异常';
  return llmGovernance.value.providerHealth.statusLabel;
});
const llmStatusClass = computed(() => {
  if (llmError.value) return 'red';
  if (llmLoading.value) return 'amber';
  return llmGovernance.value.providerHealth.statusClass;
});

onMounted(async () => {
  const [phase2Result, phase3Result, promptGovernanceResult, llmGovernanceResult] = await Promise.allSettled([
    fetchPhase2Dashboard({ baseUrl: apiBaseUrl }),
    fetchPhase3Dashboard({ baseUrl: apiBaseUrl }),
    fetchPromptGovernance({ baseUrl: apiBaseUrl, actorRole: adminActorRole }),
    fetchLlmGovernance({ baseUrl: apiBaseUrl }),
  ]);

  if (phase2Result.status === 'fulfilled') {
    phase2Payload.value = phase2Result.value;
  } else {
    phase2Error.value = `无法加载第二阶段真实 API 指标：${phase2Result.reason.message}`;
  }

  if (phase3Result.status === 'fulfilled') {
    phase3Payload.value = phase3Result.value;
  } else {
    phase3Error.value = `无法加载第三阶段真实 API 指标：${phase3Result.reason.message}`;
  }

  if (promptGovernanceResult.status === 'fulfilled') {
    promptGovernancePayload.value = promptGovernanceResult.value;
  } else {
    promptGovernanceError.value = `无法加载 Prompt 入库治理真实 API：${promptGovernanceResult.reason.message}`;
  }

  if (llmGovernanceResult.status === 'fulfilled') {
    llmGovernancePayload.value = llmGovernanceResult.value;
  } else {
    llmError.value = `无法加载 LLM/Prompt 治理真实 API：${llmGovernanceResult.reason.message}`;
  }

  phase2Loading.value = false;
  phase3Loading.value = false;
  promptGovernanceLoading.value = false;
  llmLoading.value = false;
});
</script>
