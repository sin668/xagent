<template>
  <view class="inventory-page">
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
      <view class="nav-title">车源匹配</view>
      <view class="nav-action" aria-label="筛选">≡</view>
    </view>

    <scroll-view scroll-y class="inventory-content">
      <section class="inventory-hero">
        <image class="inventory-hero-image" :src="heroImage" mode="aspectFill" />
        <view class="inventory-hero-overlay">
          <text class="inventory-eyebrow">Siberia Auto Trade · C 级</text>
          <view>
            <view class="inventory-title">{{ priorityItems.length }} 台车源可优先匹配</view>
            <view class="inventory-note">报价前需完成俄罗斯贸易合规复核，未确认价格不会进入 AI 承诺。</view>
          </view>
        </view>
      </section>

      <view class="chip-row">
        <text class="filter-chip filter-chip-active">SUV</text>
        <text class="filter-chip">2022+</text>
        <text class="filter-chip">准新</text>
        <text class="filter-chip">可出口</text>
      </view>

      <section class="inventory-list">
        <article v-for="item in inventoryCards" :key="item.id" class="inventory-card">
          <view class="inventory-card-main">
            <image class="inventory-thumb" :src="item.imageUrl || heroImage" mode="aspectFill" />
            <view class="inventory-card-copy">
              <view class="inventory-name">{{ item.title }}</view>
              <view class="inventory-meta">{{ item.meta }}</view>
              <view class="inventory-price">{{ item.priceText }}</view>
              <view class="pool-tag-row">
                <text :class="['pool-tag', item.canAiQuote ? 'risk-low' : 'pool-tag-red']">
                  {{ item.canAiQuote ? '可用于AI回复' : '禁止AI承诺' }}
                </text>
                <text :class="['pool-tag', item.expiryLabel === '已过期' ? 'pool-tag-red' : 'pool-tag-amber']">
                  {{ item.expiryLabel }}
                </text>
                <text class="pool-tag pool-tag-blue">{{ item.mediaCountText }}</text>
              </view>
            </view>
          </view>
          <view class="inventory-copy">{{ item.conditionSummary }} · {{ item.configuration }}</view>
          <view v-if="item.blockingReasons.length" class="inventory-copy">
            阻断原因：{{ item.blockingReasons.join('、') }}
          </view>
        </article>
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
import { computed, onMounted, ref } from 'vue';

import { inventorySeed } from '../../data/inventorySeed.js';
import { mapInventoryItems } from '../../services/apiAdapters.js';
import { apiClient } from '../../services/apiClient.js';
import { buildBottomTabs, navigateBottomTab } from '../../services/bottomTabs.js';
import { buildInventoryCardView, filterPriorityInventory } from '../../services/inventory.js';
import '../../styles/home.css';
import '../../styles/leadPool.css';
import '../../styles/inventory.css';

const heroImage = 'https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?auto=format&fit=crop&w=900&q=80';
const now = '2026-05-28T00:00:00Z';
const bottomTabs = buildBottomTabs('insights');
const inventoryItems = ref([]);
const inventoryCards = computed(() => inventoryItems.value.map((item) => buildInventoryCardView(item, { now })));
const priorityItems = computed(() => filterPriorityInventory(inventoryItems.value, { now }));

onMounted(async () => {
  try {
    const payload = await apiClient.get('/inventory/items');
    const mappedItems = mapInventoryItems(payload);
    inventoryItems.value = mappedItems.length ? mappedItems : inventorySeed;
  } catch (_error) {
    inventoryItems.value = inventorySeed;
  }
});

function goBack() {
  if (globalThis.uni?.navigateBack) {
    globalThis.uni.navigateBack();
  }
}

function openTab(tab) {
  navigateBottomTab(tab);
}
</script>
