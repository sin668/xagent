<template>
  <slot />
</template>

<style>
*,
*::before,
*::after {
  box-sizing: border-box;
}

page {
  --phone-width: 430px;
  --phone-radius: 44px;
  --safe-bottom: env(safe-area-inset-bottom, 0px);
  --xagent-paper: oklch(96% 0.012 245);
  --xagent-paper-deep: oklch(92.5% 0.018 245);
  --xagent-surface: oklch(99% 0.006 245);
  --xagent-surface-2: oklch(97.2% 0.01 245);
  --xagent-line: oklch(87% 0.018 245);
  --xagent-ink: oklch(24% 0.025 250);
  --xagent-muted: oklch(53% 0.035 250);
  --xagent-blue: oklch(50% 0.18 255);
  --xagent-green: oklch(51% 0.13 165);
  --xagent-amber: oklch(55% 0.13 72);
  --xagent-red: oklch(52% 0.15 28);
  --xagent-shadow-sm: 0 12px 26px rgba(15, 23, 42, 0.06);
  --xagent-shadow-hero: 0 22px 44px rgba(13, 27, 48, 0.2);
  min-height: 100%;
  background: var(--xagent-paper);
  color: var(--xagent-ink);
  font-family:
    -apple-system, BlinkMacSystemFont, "SF Pro Text", "PingFang SC", "Microsoft YaHei",
    sans-serif;
  overflow-x: hidden;
}

body {
  margin: 0;
  overflow-x: hidden;
  background:
    radial-gradient(circle at 50% 0%, rgba(29, 78, 216, 0.10), transparent 28%),
    linear-gradient(180deg, #dde7f1 0%, #cfdbe7 100%);
}

#app {
  width: 100%;
  min-height: 100vh;
}

@media (min-width: 431px) {
  body {
    display: flex;
    justify-content: center;
    min-height: 100vh;
    padding: 18px 0;
  }

  #app {
    max-width: var(--phone-width);
    height: min(932px, calc(100vh - 36px));
    min-height: min(932px, calc(100vh - 36px));
    overflow-x: hidden;
    border-radius: var(--phone-radius);
    background: var(--xagent-paper);
    box-shadow:
      0 0 0 10px #0d131b,
      0 28px 70px rgba(15, 23, 42, 0.28);
  }

  :is(
    .home-page,
    .lead-pool-page,
    .lead-detail-page,
    .inventory-page,
    .source-candidates-page,
    .source-detail-page,
    .agent-run-page,
    .customers-page,
    .customer-detail-page,
    .customer-followups-page,
    .lead-cleanup-page,
    .outreach-send-page,
    .email-replies-page,
    .email-reply-detail-page
  ) {
    min-height: min(932px, calc(100vh - 36px));
    border-radius: var(--phone-radius);
    overflow: hidden;
  }
}
</style>
