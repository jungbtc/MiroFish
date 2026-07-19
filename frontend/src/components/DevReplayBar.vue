<template>
  <aside
    v-if="visible"
    class="dev-replay-bar"
    :class="{ collapsed }"
    aria-label="Developer replay controls"
  >
    <button
      v-if="collapsed"
      class="replay-expand-button"
      type="button"
      aria-label="Open developer replay controls"
      @click="collapsed = false"
    >
      <span aria-hidden="true"></span>
      DEV REPLAY
    </button>

    <template v-else>
      <div class="replay-context">
        <div class="replay-mode-label">
          <span aria-hidden="true"></span>
          DEV REPLAY
        </div>
        <div class="replay-run-copy">
          <strong :title="manifest?.title">{{ manifest?.title || 'No run selected' }}</strong>
          <small>{{ manifest ? shortId(manifest.simulationId) : 'Choose a completed run' }} · READ ONLY</small>
        </div>
      </div>

      <nav class="replay-phases" aria-label="Replay workflow phases">
        <button
          v-for="phase in phases"
          :key="phase.id"
          type="button"
          :disabled="!phase.available"
          :class="{ current: currentPhase === phase.id }"
          :aria-current="currentPhase === phase.id ? 'page' : undefined"
          :title="phase.available ? `Open ${phase.label}` : `${phase.label} is unavailable for this run`"
          @click="goToPhase(phase)"
        >
          <span>{{ String(phase.step).padStart(2, '0') }}</span>
          {{ phase.label }}
        </button>
      </nav>

      <div class="replay-actions">
        <button class="choose-run-button" type="button" @click="chooseRun">Choose run</button>
        <button class="icon-action" type="button" aria-label="Collapse replay controls" @click="collapsed = true">−</button>
        <button class="icon-action exit-action" type="button" aria-label="Exit developer replay" @click="exitReplay">×</button>
      </div>
    </template>
  </aside>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  clearReplayManifest,
  getReplayManifest,
  getReplayPhases,
  isDevReplayActive
} from '../dev/devReplay'

const route = useRoute()
const router = useRouter()
const collapsed = ref(false)
const manifest = ref(null)

const visible = computed(() => isDevReplayActive(route) && route.name !== 'DevReplay')
const phases = computed(() => getReplayPhases(manifest.value))

const currentPhase = computed(() => {
  const phaseByRoute = {
    Home: 'intake',
    Process: 'knowledge',
    Simulation: 'setup',
    SimulationRun: 'simulation',
    Report: 'report',
    ReportRefinement: 'decision',
    DecisionWorkspace: 'decision'
  }
  return phaseByRoute[route.name] || ''
})

const syncManifest = () => {
  manifest.value = getReplayManifest()
}

const goToPhase = phase => {
  if (phase.target) router.push(phase.target)
}

const chooseRun = () => {
  router.push({ name: 'DevReplay', query: { replay: '1' } })
}

const exitReplay = () => {
  clearReplayManifest()
  router.push({ name: 'Home' })
}

const shortId = value => {
  const id = String(value || '')
  return id.length > 17 ? `${id.slice(0, 10)}…${id.slice(-4)}` : id
}

watch(() => route.fullPath, syncManifest, { immediate: true })
</script>

<style scoped>
.dev-replay-bar {
  position: fixed;
  z-index: 5000;
  right: 18px;
  bottom: 18px;
  left: 18px;
  min-height: 66px;
  padding: 9px 10px 9px 14px;
  display: grid;
  grid-template-columns: minmax(190px, 0.9fr) auto minmax(160px, 0.7fr);
  align-items: center;
  gap: 15px;
  color: #f5f5f7;
  border: 1px solid rgba(255, 255, 255, 0.13);
  border-radius: 17px;
  background: rgba(22, 22, 24, 0.92);
  box-shadow: 0 18px 65px rgba(0, 0, 0, 0.32), 0 1px 0 rgba(255, 255, 255, 0.08) inset;
  backdrop-filter: saturate(150%) blur(28px);
  -webkit-backdrop-filter: saturate(150%) blur(28px);
}

.dev-replay-bar.collapsed {
  right: 18px;
  left: auto;
  min-height: 42px;
  padding: 0;
  display: block;
  border-radius: 999px;
}

.replay-expand-button {
  min-height: 42px;
  padding: 0 15px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 0;
  border-radius: inherit;
  color: #f5f5f7;
  background: transparent;
  font: 700 9px/1 var(--mf-mono, ui-monospace, monospace);
  letter-spacing: 0.09em;
  cursor: pointer;
}

.replay-expand-button span,
.replay-mode-label span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #5ee29d;
  box-shadow: 0 0 0 3px rgba(94, 226, 157, 0.12);
}

.replay-context {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 13px;
}

.replay-mode-label {
  min-height: 30px;
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border-radius: 8px;
  color: #c9f7de;
  background: rgba(94, 226, 157, 0.10);
  font: 700 8px/1 var(--mf-mono, ui-monospace, monospace);
  letter-spacing: 0.08em;
  white-space: nowrap;
}

.replay-run-copy {
  min-width: 0;
  display: grid;
  gap: 4px;
}

.replay-run-copy strong {
  overflow: hidden;
  font-size: 11px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.replay-run-copy small {
  overflow: hidden;
  color: #939399;
  font: 600 8px/1.2 var(--mf-mono, ui-monospace, monospace);
  letter-spacing: 0.04em;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.replay-phases {
  min-width: 0;
  padding: 3px;
  display: flex;
  align-items: center;
  gap: 2px;
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.07);
}

.replay-phases button {
  min-height: 38px;
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 0;
  border-radius: 8px;
  color: #aaaab0;
  background: transparent;
  font: 620 10px/1 var(--mf-font, system-ui, sans-serif);
  white-space: nowrap;
  cursor: pointer;
  transition: color 150ms ease, background 150ms ease;
}

.replay-phases button span {
  color: #6f6f75;
  font: 650 7px/1 var(--mf-mono, ui-monospace, monospace);
}

.replay-phases button:hover:not(:disabled) { color: #fff; }
.replay-phases button.current {
  color: #fff;
  background: rgba(255, 255, 255, 0.13);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.22);
}
.replay-phases button.current span { color: #91ebba; }
.replay-phases button:disabled { cursor: not-allowed; opacity: 0.32; }

.replay-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
}

.choose-run-button,
.icon-action {
  min-height: 34px;
  border: 1px solid rgba(255, 255, 255, 0.11);
  color: #ededf0;
  background: rgba(255, 255, 255, 0.07);
  font: 620 10px/1 var(--mf-font, system-ui, sans-serif);
  cursor: pointer;
}

.choose-run-button { padding: 0 11px; border-radius: 8px; }
.icon-action { width: 34px; padding: 0; border-radius: 50%; font-size: 17px; }
.choose-run-button:hover,
.icon-action:hover { background: rgba(255, 255, 255, 0.13); }
.exit-action:hover { color: #ffbbb4; background: rgba(255, 91, 76, 0.14); }

.dev-replay-bar button:focus-visible {
  outline: 3px solid rgba(118, 181, 255, 0.7);
  outline-offset: 2px;
}

@media (max-width: 1120px) {
  .dev-replay-bar { grid-template-columns: minmax(160px, 0.6fr) minmax(0, 1fr) auto; }
  .replay-mode-label { display: none; }
  .replay-phases { overflow-x: auto; scrollbar-width: none; }
  .replay-phases::-webkit-scrollbar { display: none; }
  .replay-phases button { flex: 0 0 auto; }
}

@media (max-width: 700px) {
  .dev-replay-bar {
    right: 10px;
    bottom: 10px;
    left: 10px;
    padding: 8px;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 8px;
  }
  .replay-context { display: none; }
  .replay-actions .choose-run-button { display: none; }
  .replay-phases button { min-height: 36px; padding-inline: 9px; }
}

@media (prefers-reduced-motion: reduce) {
  .replay-phases button { transition: none; }
}
</style>
