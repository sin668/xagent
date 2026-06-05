<template>
  <view class="customers-page">
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
        <view class="nav-title">客户工作台</view>
        <view class="nav-subtitle">由完善线索晋级 · core customers</view>
      </view>
      <view class="nav-action" aria-label="刷新" @click="loadCustomers">↻</view>
    </view>

    <scroll-view scroll-y class="customers-content">
      <section class="customers-hero">
        <image
          class="customers-hero-image"
          mode="aspectFill"
          src="https://images.unsplash.com/photo-1549921296-3a6b7b5b56a2?auto=format&fit=crop&w=900&q=80"
        />
        <view class="customers-hero-overlay">
          <text class="customers-hero-kicker">线索完善后进入客户池</text>
          <text class="customers-hero-title">{{ customers.length }} 个有效客户正在跟进</text>
          <text class="customers-hero-desc">
            B/C 级 {{ bcCount }} · 今日待跟进 {{ todayCount }} · 有车型意向 {{ intentCount }} · 合规待复核 {{ complianceCount }}
          </text>
        </view>
      </section>

      <view class="customers-metric-row">
        <view class="customers-metric-card">
          <text class="customers-metric-number">{{ bcCount }}</text>
          <text class="customers-metric-label">B/C 级客户</text>
        </view>
        <view class="customers-metric-card">
          <text class="customers-metric-number customers-number-green">{{ intentCount }}</text>
          <text class="customers-metric-label">车型意向</text>
        </view>
        <view class="customers-metric-card">
          <text class="customers-metric-number customers-number-amber">{{ todayCount }}</text>
          <text class="customers-metric-label">今日跟进</text>
        </view>
      </view>

      <scroll-view scroll-x class="customers-chip-row">
        <text
          v-for="tab in tabs"
          :key="tab.key"
          :class="['customers-chip', activeFilter === tab.key ? 'customers-chip-active' : '']"
          @click="setActiveFilter(tab.key)"
        >
          {{ tab.label }} {{ tab.count }}
        </text>
      </scroll-view>

      <view class="section-head">
        <text class="section-title">重点客户</text>
        <text class="section-note">按下一步动作排序</text>
      </view>

      <view v-if="errorMessage" class="customers-alert">{{ errorMessage }}</view>
      <view v-else-if="isLoading" class="customers-empty">正在从真实 API 加载客户工作台...</view>
      <view v-else-if="!cards.length" class="customers-empty">当前筛选下没有已晋级客户</view>

      <view v-else class="customers-list">
        <view v-for="card in cards" :key="card.id" class="customer-card" @click="openCustomer(card.id)">
          <view class="customer-card-top">
            <view class="customer-card-main">
              <view class="customer-name">{{ card.name }}</view>
              <view class="customer-meta">
                {{ card.countryCityText }} · {{ card.customerType }} · {{ card.completenessText }}
              </view>
            </view>
            <text :class="['customer-tag', card.gradeClass]">{{ card.gradeLabel }}</text>
          </view>

          <view class="customer-contact-strip">
            <text>{{ card.contactSummaryText }}</text>
            <text>{{ card.ownerText }}</text>
          </view>

          <view class="customer-intent-card">
            <view class="customer-card-main">
              <text class="customer-intent-title">{{ card.vehicleIntentText }}</text>
              <text class="customer-intent-subtitle">来源证据：{{ card.evidenceNote || '已晋级客户来源' }}</text>
            </view>
            <text :class="['customer-tag', card.grade === 'C' ? 'customer-tag-amber' : 'customer-tag-blue']">
              {{ card.grade === 'C' ? '合规关注' : '人工跟进' }}
            </text>
          </view>

          <view class="customer-next">
            <view>
              <text class="customer-mini-label">下一步</text>
              <text class="customer-mini-value">{{ card.nextAction }}</text>
            </view>
            <button class="customer-detail-button">进入详情</button>
          </view>
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
import { computed, onMounted, ref } from 'vue';

import { buildBottomTabs, navigateBottomTab } from '../../services/bottomTabs.js';
import { buildCustomerFilterTabs, customersService, filterCustomers, getCustomerCardViewModel } from '../../services/customers.js';
import '../../styles/home.css';
import '../../styles/customers.css';

const customers = ref([]);
const isLoading = ref(false);
const errorMessage = ref('');
const activeFilter = ref('all');
const bottomTabs = buildBottomTabs('customers');
const customerFilterKeys = ['all', 'today', 'c_compliance', 'has_intent', 'unassigned'];

const tabs = computed(() => buildCustomerFilterTabs(customers.value));
const cards = computed(() => filterCustomers(customers.value, activeFilter.value).map(getCustomerCardViewModel));
const bcCount = computed(() => customers.value.filter((customer) => ['B', 'C'].includes(customer.grade)).length);
const todayCount = computed(() => filterCustomers(customers.value, 'today').length);
const intentCount = computed(() => filterCustomers(customers.value, 'has_intent').length);
const complianceCount = computed(() => filterCustomers(customers.value, 'c_compliance').length);

onMounted(loadCustomers);

async function loadCustomers() {
  isLoading.value = true;
  errorMessage.value = '';
  try {
    const payload = await customersService.listCustomers({ limit: 100 });
    customers.value = payload.items;
  } catch (error) {
    customers.value = [];
    errorMessage.value = `客户工作台加载失败：${error.message || 'Unknown'}`;
  } finally {
    isLoading.value = false;
  }
}

function openCustomer(customerId) {
  if (!customerId || !globalThis.uni?.navigateTo) {
    return;
  }
  globalThis.uni.navigateTo({ url: `/pages/customers/detail?id=${encodeURIComponent(customerId)}` });
}

function setActiveFilter(filterKey) {
  activeFilter.value = customerFilterKeys.includes(filterKey) ? filterKey : 'all';
}

function openTab(tab) {
  navigateBottomTab(tab);
}
</script>
