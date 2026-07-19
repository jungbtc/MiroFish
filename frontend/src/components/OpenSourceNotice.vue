<template>
  <footer class="open-source-notice">
    <p>
      <strong>FOREFOLD</strong> originated as a modified version of
      <a :href="UPSTREAM_PROJECT_URL" target="_blank" rel="noopener noreferrer">MiroFish</a>.
      Original and subsequent copyrights remain with their respective contributors.
    </p>
    <nav aria-label="Open-source and legal information">
      <a :href="SOURCE_CODE_URL" target="_blank" rel="noopener noreferrer">View corresponding source</a>
      <a :href="UPSTREAM_PROJECT_URL" target="_blank" rel="noopener noreferrer">Upstream project</a>
      <a :href="LICENSE_URL" target="_blank" rel="noopener noreferrer">GNU AGPL v3</a>
      <span>No warranty.</span>
    </nav>
  </footer>
</template>

<script setup>
import { LICENSE_URL, SOURCE_CODE_URL, UPSTREAM_PROJECT_URL } from '../constants/brand'
</script>

<style scoped>
.open-source-notice {
  position: relative;
  z-index: 5;
  min-height: 76px;
  padding: 18px max(24px, calc((100vw - 1280px) / 2));
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px 32px;
  border-top: 1px solid rgba(29, 29, 31, 0.10);
  color: #6e6e73;
  background: #f5f5f7;
  font: 400 11px/1.5 var(--mf-font, system-ui, sans-serif);
}

.open-source-notice p { max-width: 720px; margin: 0; }
.open-source-notice strong { color: #1d1d1f; letter-spacing: 0.04em; }
.open-source-notice nav { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px 14px; }
.open-source-notice a { color: #424245; font-weight: 600; text-decoration: none; }
.open-source-notice a:hover { color: #0071e3; text-decoration: underline; }

@media (max-width: 760px) {
  .open-source-notice { align-items: flex-start; flex-direction: column; }
  .open-source-notice nav { justify-content: flex-start; }
}
</style>
