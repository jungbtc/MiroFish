<template>
  <div class="replay-picker-shell">
    <header class="replay-picker-header">
      <BrandLockup class="replay-brand" />
      <button class="replay-home-link" type="button" @click="exitReplay">Exit developer mode</button>
    </header>

    <main class="replay-picker-main">
      <section class="replay-intro" aria-labelledby="replay-picker-title">
        <div>
          <p class="replay-kicker">DEVELOPER REPLAY</p>
          <h1 id="replay-picker-title">Review the real workflow without running it again.</h1>
          <p>
            Select a completed run. WHAT IF WHAT IF will reuse its saved graph, environment,
            simulation, report, and decision state while you move page by page.
          </p>
        </div>
        <div class="read-only-badge" aria-label="Replay is read only">
          <span aria-hidden="true"></span>
          READ ONLY
        </div>
      </section>

      <section class="replay-library" aria-labelledby="completed-runs-title" aria-busy="loading">
        <div class="library-heading">
          <div>
            <p class="section-label">SAVED OUTCOMES</p>
            <h2 id="completed-runs-title">Completed runs</h2>
          </div>
          <button class="refresh-button" type="button" :disabled="loading" @click="loadRuns">
            {{ loading ? 'Refreshing…' : 'Refresh' }}
          </button>
        </div>

        <div v-if="!replayEnabled" class="replay-state warning-state" role="alert">
          <h3>Developer replay is disabled.</h3>
          <p>Run the Vite development server or set <code>VITE_ENABLE_DEV_REPLAY=true</code>.</p>
        </div>

        <div v-else-if="error" class="replay-state error-state" role="alert">
          <h3>Completed runs could not be loaded.</h3>
          <p>{{ error }}</p>
          <button type="button" @click="loadRuns">Try again</button>
        </div>

        <div v-else-if="loading" class="replay-state loading-state" role="status">
          <span class="loading-indicator" aria-hidden="true"></span>
          <p>Loading saved workflow outcomes…</p>
        </div>

        <div v-else-if="runs.length === 0" class="replay-state empty-state">
          <h3>No complete replay is available yet.</h3>
          <p>A run appears here after its simulation and report have completed.</p>
        </div>

        <ol v-else class="run-grid" aria-label="Completed runs">
          <li v-for="run in runs" :key="run.simulationId">
            <button
              class="run-card"
              type="button"
              :disabled="openingId === run.simulationId"
              :aria-label="`Replay ${displayTitle(run)}`"
              @click="openReplay(run)"
            >
              <span class="run-card-topline">
                <span class="run-status"><i aria-hidden="true"></i> COMPLETE</span>
                <time :datetime="run.createdAt">{{ formatDate(run.createdAt) }}</time>
              </span>
              <strong>{{ displayTitle(run) }}</strong>
              <span class="run-prompt">{{ run.simulation_requirement || 'Saved simulation outcome' }}</span>
              <span class="run-metadata">
                <span>{{ formatRounds(run) }}</span>
                <span>{{ shortId(run.simulationId) }}</span>
              </span>
              <span class="run-action">
                {{ openingId === run.simulationId ? 'Opening replay…' : 'Review every phase' }}
                <span aria-hidden="true">→</span>
              </span>
            </button>
          </li>
        </ol>
      </section>
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import BrandLockup from '../components/BrandLockup.vue'
import { getReport } from '../api/report'
import { getSimulationHistory } from '../api/simulation'
import { getDecisionRunLineage } from '../api/v2'
import { summarizeCaseTitle } from '../utils/caseTitle'
import {
  buildReplayTarget,
  clearReplayManifest,
  isDevReplayEnabled,
  selectLatestReplayRunId,
  selectReplayCandidates,
  setReplayManifest
} from '../dev/devReplay'

const router = useRouter()
const replayEnabled = isDevReplayEnabled()
const loading = ref(false)
const error = ref('')
const runs = ref([])
const openingId = ref('')

const loadRuns = async () => {
  if (!replayEnabled) return

  loading.value = true
  error.value = ''
  try {
    const response = await getSimulationHistory(100)
    runs.value = selectReplayCandidates(response.data || [])
  } catch (loadError) {
    runs.value = []
    error.value = loadError.message || 'The saved-run index is unavailable.'
  } finally {
    loading.value = false
  }
}

const openReplay = async run => {
  if (openingId.value) return

  openingId.value = run.simulationId
  error.value = ''
  try {
    const reportResponse = await getReport(run.reportId)
    const report = reportResponse.data || {}
    if (String(report.status || '').toLowerCase() !== 'completed') {
      throw new Error('The selected report has not completed and cannot be replayed safely.')
    }

    const baselineRunId = String(report.refinement_run_id || '')
    let refinementRunId = baselineRunId
    if (baselineRunId) {
      try {
        const lineageResponse = await getDecisionRunLineage(baselineRunId)
        refinementRunId = selectLatestReplayRunId(lineageResponse.data, baselineRunId)
      } catch {
        // A readable baseline still provides a safe replay when no child
        // lineage is available to the current local actor.
      }
    }

    const manifest = setReplayManifest({
      projectId: run.projectId,
      simulationId: run.simulationId,
      reportId: run.reportId,
      refinementRunId,
      title: displayTitle(run),
      createdAt: run.createdAt
    })
    await router.push(buildReplayTarget('knowledge', manifest))
  } catch (openError) {
    error.value = openError.message || 'This run could not be opened for replay.'
  } finally {
    openingId.value = ''
  }
}

const exitReplay = () => {
  clearReplayManifest()
  router.push({ name: 'Home' })
}

const displayTitle = run => summarizeCaseTitle(run.project_name, run.simulation_requirement)

const formatDate = value => {
  if (!value) return 'Date unavailable'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('en', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

const formatRounds = run => {
  const current = Number(run.current_round || 0)
  const total = Number(run.total_rounds || 0)
  return total ? `${current}/${total} rounds` : 'Completed simulation'
}

const shortId = value => {
  const id = String(value || '')
  return id.length > 18 ? `${id.slice(0, 10)}…${id.slice(-5)}` : id
}

onMounted(loadRuns)
</script>

<style scoped>
.replay-picker-shell {
  min-height: 100vh;
  color: #1d1d1f;
  background:
    radial-gradient(circle at 88% 8%, rgba(64, 124, 255, 0.11), transparent 28rem),
    linear-gradient(180deg, #f7f8fb 0%, #eef0f5 100%);
}

.replay-picker-header {
  min-height: 68px;
  padding: 10px clamp(20px, 4vw, 56px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  border-bottom: 1px solid rgba(29, 29, 31, 0.10);
  background: rgba(250, 250, 252, 0.76);
  backdrop-filter: saturate(180%) blur(24px);
  -webkit-backdrop-filter: saturate(180%) blur(24px);
}

.replay-brand {
  --brand-icon-size: 36px;
  --brand-name-size: 13px;
}

.replay-home-link {
  min-height: 36px;
  padding: 0 14px;
  display: inline-flex;
  align-items: center;
  border: 1px solid rgba(29, 29, 31, 0.12);
  border-radius: 999px;
  color: #1d1d1f;
  background: rgba(255, 255, 255, 0.72);
  font-size: 12px;
  font-weight: 650;
  text-decoration: none;
  cursor: pointer;
}

.replay-home-link:hover { background: #fff; }

.replay-picker-main {
  width: min(1180px, calc(100% - 40px));
  margin: 0 auto;
  padding: clamp(58px, 8vw, 104px) 0 150px;
}

.replay-intro {
  display: grid;
  grid-template-columns: minmax(0, 760px) auto;
  align-items: end;
  justify-content: space-between;
  gap: 40px;
}

.replay-kicker,
.section-label {
  margin: 0 0 13px;
  color: #5f6470;
  font: 700 10px/1.2 var(--mf-mono, ui-monospace, monospace);
  letter-spacing: 0.14em;
}

.replay-intro h1 {
  max-width: 760px;
  margin: 0;
  font-size: clamp(38px, 5.4vw, 72px);
  font-weight: 650;
  line-height: 0.98;
  letter-spacing: -0.052em;
}

.replay-intro p:not(.replay-kicker) {
  max-width: 680px;
  margin: 26px 0 0;
  color: #62636a;
  font-size: 16px;
  line-height: 1.65;
}

.read-only-badge {
  min-height: 34px;
  padding: 0 13px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid rgba(17, 122, 82, 0.17);
  border-radius: 999px;
  color: #0b6b49;
  background: rgba(20, 151, 101, 0.09);
  font: 700 9px/1 var(--mf-mono, ui-monospace, monospace);
  letter-spacing: 0.1em;
  white-space: nowrap;
}

.read-only-badge span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #149765;
}

.replay-library {
  margin-top: clamp(64px, 9vw, 112px);
}

.library-heading {
  padding-bottom: 18px;
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 20px;
  border-bottom: 1px solid rgba(29, 29, 31, 0.12);
}

.library-heading h2 {
  margin: 0;
  font-size: 24px;
  letter-spacing: -0.03em;
}

.refresh-button,
.replay-state button {
  min-height: 34px;
  padding: 0 13px;
  border: 1px solid rgba(29, 29, 31, 0.12);
  border-radius: 9px;
  color: #1d1d1f;
  background: rgba(255, 255, 255, 0.75);
  font: 650 12px/1 var(--mf-font, system-ui, sans-serif);
  cursor: pointer;
}

.refresh-button:disabled { cursor: wait; opacity: 0.55; }

.run-grid {
  margin: 24px 0 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
  list-style: none;
}

.run-card {
  width: 100%;
  min-height: 288px;
  padding: 22px;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  text-align: left;
  border: 1px solid rgba(29, 29, 31, 0.10);
  border-radius: 20px;
  color: #1d1d1f;
  background: rgba(255, 255, 255, 0.74);
  box-shadow: 0 1px 1px rgba(0, 0, 0, 0.02), 0 18px 45px rgba(28, 35, 54, 0.06);
  cursor: pointer;
  transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
}

.run-card:hover:not(:disabled) {
  transform: translateY(-3px);
  border-color: rgba(29, 29, 31, 0.20);
  box-shadow: 0 24px 58px rgba(28, 35, 54, 0.11);
}

.run-card:focus-visible,
.replay-home-link:focus-visible,
.refresh-button:focus-visible {
  outline: 3px solid rgba(0, 113, 227, 0.35);
  outline-offset: 3px;
}

.run-card:disabled { cursor: wait; opacity: 0.66; }

.run-card-topline,
.run-metadata,
.run-action {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.run-card-topline {
  color: #777981;
  font: 650 10px/1.2 var(--mf-mono, ui-monospace, monospace);
  letter-spacing: 0.03em;
}

.run-status { display: inline-flex; align-items: center; gap: 7px; color: #0b6b49; }
.run-status i { width: 6px; height: 6px; border-radius: 50%; background: #149765; }

.run-card strong {
  margin-top: 30px;
  font-size: 24px;
  font-weight: 650;
  line-height: 1.08;
  letter-spacing: -0.035em;
}

.run-prompt {
  margin-top: 13px;
  display: -webkit-box;
  overflow: hidden;
  color: #686970;
  font-size: 13px;
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.run-metadata {
  margin-top: auto;
  padding-top: 24px;
  color: #777981;
  font: 600 10px/1.2 var(--mf-mono, ui-monospace, monospace);
}

.run-action {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid rgba(29, 29, 31, 0.09);
  color: #075dc7;
  font-size: 12px;
  font-weight: 700;
}

.replay-state {
  min-height: 220px;
  margin-top: 24px;
  padding: 36px;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: 10px;
  text-align: center;
  border: 1px solid rgba(29, 29, 31, 0.10);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.68);
}

.replay-state h3,
.replay-state p { margin: 0; }
.replay-state p { color: #686970; font-size: 13px; }
.error-state { border-color: rgba(190, 45, 38, 0.22); }
.warning-state code { padding: 2px 5px; border-radius: 5px; background: #ececf0; }

.loading-indicator {
  width: 22px;
  height: 22px;
  border: 2px solid rgba(29, 29, 31, 0.14);
  border-top-color: #1d1d1f;
  border-radius: 50%;
  animation: replaySpin 0.8s linear infinite;
}

@keyframes replaySpin { to { transform: rotate(360deg); } }

@media (max-width: 760px) {
  .replay-picker-header { padding-inline: 16px; }
  .replay-picker-main { width: min(100% - 28px, 1180px); padding-top: 48px; }
  .replay-intro { grid-template-columns: 1fr; align-items: start; gap: 24px; }
  .read-only-badge { justify-self: start; }
  .run-grid { grid-template-columns: 1fr; }
  .run-card { min-height: 264px; }
}

@media (prefers-reduced-motion: reduce) {
  .run-card { transition: none; }
  .run-card:hover:not(:disabled) { transform: none; }
  .loading-indicator { animation-duration: 1.8s; }
}
</style>
