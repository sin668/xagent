<template>
  <section id="lead-channels" class="admin-page admin-combined-page">
    <ChannelsPage />
    <RiskConfigPage />
    <QueuesPage />
    <RiskAuditPage />
  </section>
</template>

<script setup>
import ChannelsPage from './ChannelsPage.vue';
import QueuesPage from './QueuesPage.vue';
import RiskAuditPage from './RiskAuditPage.vue';
import RiskConfigPage from './RiskConfigPage.vue';
</script>
