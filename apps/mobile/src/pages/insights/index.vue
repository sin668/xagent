<template>
  <view class="source-candidates-page">
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
        <view class="nav-title">洞察</view>
        <view class="nav-subtitle">来源、清洗和 Agent 运行入口</view>
      </view>
      <view class="nav-action" aria-label="刷新">⌁</view>
    </view>

    <scroll-view scroll-y class="source-content">
      <view class="source-summary-card">
        <view class="source-summary-top">
          <view>
            <view class="source-summary-title">运营洞察工作台</view>
            <view class="source-summary-meta">从这里进入来源审核、清洗建议和被清洗线索审计</view>
          </view>
          <text class="source-tag source-tag-blue">只读</text>
        </view>
        <view class="source-map">
          <view class="source-tile" @click="openPath('/pages/sources/index')">
            <text class="source-kicker">线索来源</text>
            <text class="source-number source-number-blue">来源</text>
          </view>
          <view class="source-tile" @click="openPath('/pages/lead-cleanup/index')">
            <text class="source-kicker">清洗建议</text>
            <text class="source-number source-number-amber">复核</text>
          </view>
          <view class="source-tile" @click="openPath('/pages/leads/cleaned')">
            <text class="source-kicker">被清洗线索</text>
            <text class="source-number source-number-red">无效</text>
          </view>
          <view class="source-tile" @click="openPath('/pages/agent-run/index')">
            <text class="source-kicker">Agent 任务</text>
            <text class="source-number source-number-green">运行</text>
          </view>
        </view>
      </view>

      <view class="section-head">
        <text class="section-title">常用入口</text>
        <text class="section-note">不触达客户</text>
      </view>

      <view class="source-list">
        <view class="source-card" @click="openPath('/pages/sources/index')">
          <view class="source-card-top">
            <view class="source-card-main">
              <view class="source-name">线索来源</view>
              <view class="source-meta">查看来源候选、风险等级、审核状态和抽取准入</view>
            </view>
            <text class="source-tag source-tag-blue">进入</text>
          </view>
          <view class="source-evidence">原底部导航来源页已迁移到这里，线索池也保留快捷入口。</view>
        </view>

        <view class="source-card" @click="openPath('/pages/leads/cleaned')">
          <view class="source-card-top">
            <view class="source-card-main">
              <view class="source-name">被清洗线索</view>
              <view class="source-meta">查看已清洗为无效、重复或放弃的线索和事实依据</view>
            </view>
            <text class="source-tag source-tag-red">审计</text>
          </view>
          <view class="source-evidence">用于复盘线索质量，沉淀清洗事实和原因。</view>
        </view>
      </view>
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
import { buildBottomTabs, navigateBottomTab } from '../../services/bottomTabs.js';
import '../../styles/home.css';
import '../../styles/sourceCandidates.css';

const bottomTabs = buildBottomTabs('insights');

function openPath(path) {
  if (!globalThis.uni?.navigateTo) {
    return;
  }

  globalThis.uni.navigateTo({ url: path });
}

function openTab(tab) {
  navigateBottomTab(tab);
}
</script>
