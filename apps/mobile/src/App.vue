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
  --phone-radius: 34px;
  --safe-bottom: env(safe-area-inset-bottom, 0px);
  min-height: 100%;
  background: #eef3f8;
  color: #132033;
  font-family:
    -apple-system, BlinkMacSystemFont, "SF Pro Text", "PingFang SC", "Microsoft YaHei",
    sans-serif;
  overflow-x: hidden;
}

body {
  margin: 0;
  overflow-x: hidden;
  background: #dce5ef;
}

#app {
  width: 100%;
  min-height: 100vh;
}

@media (min-width: 431px) {
  body {
    display: flex;
    justify-content: center;
    padding: 18px 0;
  }

  #app {
    max-width: var(--phone-width);
    min-height: calc(100vh - 36px);
    overflow-x: hidden;
    border-radius: var(--phone-radius);
    background: #eef3f8;
    box-shadow: 0 22px 60px rgba(15, 23, 42, 0.22);
  }

  :is(
    .home-page,
    .lead-pool-page,
    .lead-detail-page,
    .inventory-page,
    .source-candidates-page,
    .source-detail-page,
    .agent-run-page
  ) {
    min-height: calc(100vh - 36px);
    border-radius: var(--phone-radius);
    overflow: hidden;
  }
}
</style>
