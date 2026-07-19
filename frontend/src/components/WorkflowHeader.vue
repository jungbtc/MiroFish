<template>
  <header class="workflow-header">
    <BrandLockup class="workflow-brand" />

    <div class="workflow-layout-control" role="group" aria-label="Workspace layout">
      <button
        v-for="mode in layoutModes"
        :key="mode.id"
        type="button"
        :class="{ active: viewMode === mode.id }"
        :aria-pressed="viewMode === mode.id"
        @click="emit('update:viewMode', mode.id)"
      >
        {{ mode.label }}
      </button>
    </div>

    <div class="workflow-header-meta">
      <LanguageSwitcher />
      <div class="workflow-progress" :aria-label="`Step ${step} of 5: ${stepName}`">
        <span class="workflow-progress-copy">
          <small>STEP {{ step }} OF 5</small>
          <strong>{{ stepName }}</strong>
        </span>
        <span class="workflow-progress-dots" aria-hidden="true">
          <i v-for="index in 5" :key="index" :class="{ complete: index < step, current: index === step }"></i>
        </span>
      </div>
      <span class="workflow-status" :class="statusClass" role="status">
        <i aria-hidden="true"></i>
        {{ statusText }}
      </span>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import BrandLockup from './BrandLockup.vue'
import LanguageSwitcher from './LanguageSwitcher.vue'

defineProps({
  step: { type: Number, required: true },
  stepName: { type: String, default: '' },
  statusClass: { type: String, default: 'processing' },
  statusText: { type: String, default: '' },
  viewMode: { type: String, default: 'split' }
})

const emit = defineEmits(['update:viewMode'])
const { t } = useI18n({ useScope: 'global' })

const layoutModes = computed(() => [
  { id: 'graph', label: t('main.layoutGraph') },
  { id: 'split', label: t('main.layoutSplit') },
  { id: 'workbench', label: t('main.layoutWorkbench') }
])
</script>

<style scoped>
.workflow-header {
  position: relative;
  z-index: 100;
  min-height: 64px;
  padding: 8px 20px;
  display: grid;
  grid-template-columns: minmax(150px, 1fr) auto minmax(310px, 1fr);
  align-items: center;
  gap: 18px;
  color: var(--mf-ink);
  background: color-mix(in srgb, var(--mf-surface) 88%, transparent);
  border-bottom: 1px solid var(--mf-separator);
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.64) inset;
  backdrop-filter: saturate(180%) blur(22px);
  -webkit-backdrop-filter: saturate(180%) blur(22px);
}

.workflow-brand {
  --brand-icon-size: 34px;
  --brand-name-size: 13px;
  min-height: 44px;
}

.workflow-layout-control {
  min-height: 36px;
  padding: 3px;
  display: flex;
  gap: 2px;
  border: 1px solid rgba(29, 29, 31, 0.04);
  border-radius: 10px;
  background: rgba(118, 118, 128, 0.10);
}

.workflow-layout-control button {
  min-height: 30px;
  padding: 0 14px;
  border: 0;
  border-radius: 7px;
  color: var(--mf-secondary);
  background: transparent;
  font: 600 12px/1 var(--mf-font);
  cursor: pointer;
  transition: color 160ms ease, background 160ms ease, box-shadow 160ms ease;
}

.workflow-layout-control button:hover { color: var(--mf-ink); }
.workflow-layout-control button.active {
  color: var(--mf-ink);
  background: var(--mf-surface);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.12), 0 0 0 0.5px rgba(0, 0, 0, 0.04);
}

.workflow-header-meta {
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 14px;
}

.workflow-progress {
  min-width: 150px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 11px;
}

.workflow-progress-copy { display: grid; gap: 1px; text-align: right; }
.workflow-progress-copy small {
  color: var(--mf-tertiary);
  font: 650 8px/1.2 var(--mf-mono);
  letter-spacing: 0.08em;
}
.workflow-progress-copy strong {
  max-width: 132px;
  overflow: hidden;
  color: var(--mf-ink);
  font-size: 11px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workflow-progress-dots { display: flex; gap: 4px; }
.workflow-progress-dots i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: rgba(118, 118, 128, 0.20);
}
.workflow-progress-dots i.complete { background: var(--mf-success); }
.workflow-progress-dots i.current {
  width: 14px;
  border-radius: 999px;
  background: var(--mf-accent);
}

.workflow-status {
  min-height: 32px;
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border-radius: 999px;
  color: var(--mf-secondary);
  background: rgba(118, 118, 128, 0.09);
  font-size: 10px;
  font-weight: 620;
  white-space: nowrap;
}

.workflow-status i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--mf-tertiary);
}
.workflow-status.processing i { background: var(--mf-accent); animation: statusPulse 1.4s ease-in-out infinite; }
.workflow-status.ready i,
.workflow-status.completed i { background: var(--mf-success); }
.workflow-status.degraded i { background: var(--mf-warning); }
.workflow-status.error i { background: var(--mf-danger); }

@keyframes statusPulse { 50% { opacity: 0.38; transform: scale(0.82); } }

@media (max-width: 1020px) {
  .workflow-header { grid-template-columns: auto 1fr auto; }
  .workflow-layout-control { justify-self: center; }
  .workflow-progress-copy, .workflow-progress-dots { display: none; }
  .workflow-progress { min-width: 0; }
}

@media (max-width: 760px) {
  .workflow-header {
    min-height: 112px;
    padding: 8px 12px 9px;
    grid-template-columns: 1fr auto;
    grid-template-rows: 44px 42px;
    gap: 4px 10px;
  }
  .workflow-layout-control { grid-column: 1 / -1; grid-row: 2; width: 100%; }
  .workflow-layout-control button { flex: 1; min-height: 36px; padding: 0 7px; }
  .workflow-header-meta { gap: 7px; }
  .workflow-status { display: none; }
}

@media (prefers-reduced-motion: reduce) {
  .workflow-status.processing i { animation: none; }
}
</style>
