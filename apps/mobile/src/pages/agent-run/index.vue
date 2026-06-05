<template>
  <view class="agent-run-page">
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
        <view class="nav-title">启动 Agent</view>
        <view class="nav-subtitle">手动触发同样写入 agent_task_runs</view>
      </view>
      <view class="nav-action" aria-label="刷新状态" @click="refreshTaskStatus">↻</view>
    </view>

    <scroll-view scroll-y class="agent-run-content">
      <section class="agent-form-card">
        <view class="source-card-top">
          <view>
            <view class="source-summary-title">{{ taskType }}</view>
            <view class="source-summary-meta">只发现来源或只抽取已审核来源，不触达客户</view>
          </view>
          <text class="source-tag source-tag-green">LLM</text>
        </view>

        <view class="agent-segment">
          <text
            v-for="type in taskTypes"
            :key="type"
            :class="['agent-segment-item', taskType === type ? 'agent-segment-active' : '']"
            @click="taskType = type"
          >
            {{ type }}
          </text>
        </view>

        <view class="agent-field">
          <text class="agent-label">国家</text>
          <input v-model="country" class="agent-input" />
        </view>
        <view class="agent-field">
          <text class="agent-label">城市</text>
          <input v-model="citiesText" class="agent-input" placeholder="Moscow, Vladivostok" />
        </view>
        <view class="agent-field">
          <text class="agent-label">渠道策略</text>
          <input v-model="channelStrategy" class="agent-input" />
        </view>
        <view class="agent-field">
          <text class="agent-label">Prompt Template</text>
          <input v-model="promptTemplateKey" class="agent-input" />
        </view>
        <view class="agent-field">
          <text class="agent-label">运行上限</text>
          <input v-model="limit" class="agent-input" type="number" />
        </view>

        <button class="agent-run-button" :disabled="isRunning" @click="startAgentRun">
          {{ isRunning ? '运行中' : '创建并启动任务' }}
        </button>
      </section>

      <view class="section-head">
        <text class="section-title">运行状态</text>
        <text class="section-note">最近一次</text>
      </view>
      <section class="agent-console">
        <view class="agent-console-head">
          <text>agent_task_runs {{ agentTaskRunId || 'Unknown' }}</text>
          <text class="source-tag source-tag-blue">{{ taskStatus || 'idle' }}</text>
        </view>
        <view class="agent-console-body">
          <view class="agent-console-line">
            <text>任务类型</text>
            <view>{{ latestRun.taskType || taskType }}</view>
          </view>
          <view class="agent-console-line">
            <text>输出数量</text>
            <view>created {{ createdCount }} · blocked {{ blockedCount }} · duplicate {{ duplicateCount }}</view>
          </view>
          <view class="agent-console-line">
            <text>失败原因</text>
            <view>{{ failureReason }}</view>
          </view>
          <view class="agent-console-line">
            <text>模型审计</text>
            <view>{{ latestRun.llmProvider || 'Unknown' }} · {{ latestRun.llmModel || 'Unknown' }} · {{ latestRun.promptVersion || promptTemplateKey }}</view>
          </view>
        </view>
      </section>

      <view class="section-head">
        <text class="section-title">安全边界</text>
        <text class="section-note">硬规则</text>
      </view>
      <section class="agent-safety-grid">
        <view class="source-tile">
          <text class="source-kicker">自动私信</text>
          <text class="agent-safe-value">禁用</text>
        </view>
        <view class="source-tile">
          <text class="source-kicker">登录采集</text>
          <text class="agent-safe-value">禁用</text>
        </view>
        <view class="source-tile">
          <text class="source-kicker">High 抽取</text>
          <text class="agent-safe-value agent-safe-warn">人工审核</text>
        </view>
        <view class="source-tile">
          <text class="source-kicker">Forbidden</text>
          <text class="agent-safe-value">阻断</text>
        </view>
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
  </view>
</template>

<script setup>
import { computed, ref } from 'vue';

import { agentTasksService } from '../../services/agentTasks.js';
import { buildBottomTabs, navigateBottomTab } from '../../services/bottomTabs.js';
import '../../styles/home.css';
import '../../styles/sourceCandidates.css';

const taskTypes = ['SOURCE_DISCOVERY', 'LEAD_EXTRACTION'];
const taskType = ref('SOURCE_DISCOVERY');
const country = ref('Russia');
const citiesText = ref('Moscow, Vladivostok');
const channelStrategy = ref('official_website_public_directory_search_engine');
const promptTemplateKey = ref('source_discovery_default');
const limit = ref(50);
const latestRun = ref({});
const isRunning = ref(false);
const bottomTabs = buildBottomTabs('sources');

const agentTaskRunId = computed(() => latestRun.value.agentTaskRunId || latestRun.value.id || '');
const taskStatus = computed(() => latestRun.value.status || '');
const createdCount = computed(() => latestRun.value.createdCount ?? latestRun.value.outputSummary?.createdCount ?? 0);
const blockedCount = computed(() => latestRun.value.blockedCount ?? latestRun.value.outputSummary?.blockedCount ?? 0);
const duplicateCount = computed(() => latestRun.value.duplicateCount ?? latestRun.value.outputSummary?.duplicateCount ?? 0);
const failureReason = computed(() => latestRun.value.errorMessage || latestRun.value.outputSummary?.error?.message || '无');

function getCities() {
  return citiesText.value
    .split(',')
    .map((city) => city.trim())
    .filter(Boolean);
}

async function startAgentRun() {
  isRunning.value = true;
  try {
    const payload = {
      country: country.value,
      cities: getCities(),
      channelStrategy: channelStrategy.value,
      promptTemplateKey: promptTemplateKey.value,
      limit: Number(limit.value || 20),
    };
    latestRun.value = taskType.value === 'LEAD_EXTRACTION'
      ? await agentTasksService.startLeadExtraction(payload)
      : await agentTasksService.startSourceDiscovery(payload);
  } catch (error) {
    latestRun.value = {
      taskType: taskType.value,
      status: 'failed',
      errorMessage: error?.message || '启动失败',
    };
  } finally {
    isRunning.value = false;
  }
}

async function refreshTaskStatus() {
  if (!agentTaskRunId.value) {
    return;
  }

  try {
    latestRun.value = await agentTasksService.getAgentTaskRun(agentTaskRunId.value);
  } catch (error) {
    latestRun.value = {
      ...latestRun.value,
      errorMessage: error?.message || '状态查询失败',
    };
  }
}

function openTab(tab) {
  navigateBottomTab(tab);
}
</script>
