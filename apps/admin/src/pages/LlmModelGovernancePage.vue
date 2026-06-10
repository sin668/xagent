<template>
  <section id="llm-model-governance" class="admin-page admin-combined-page">
    <PromptGovernancePage />
    <LlmGovernancePage />
  </section>
</template>

<script setup>
import LlmGovernancePage from './LlmGovernancePage.vue';
import PromptGovernancePage from './PromptGovernancePage.vue';
</script>
