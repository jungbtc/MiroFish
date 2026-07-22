import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const readFrontend = path => readFileSync(resolve(frontendRoot, path), 'utf8')

test('Setup keeps previews compact and scrolls expanded persona/config lists in place', () => {
  const setup = readFrontend('src/components/Step2EnvSetup.vue')

  assert.match(setup, /\.scroll-container\s*\{[\s\S]*overflow-y:\s*auto/)
  assert.match(setup, /scrollbar-gutter:\s*stable/)
  assert.match(setup, /\.step-card\s*\{[\s\S]*flex:\s*0\s+0\s+auto/)

  const profiles = setup.slice(setup.indexOf('.profiles-list {'), setup.indexOf('.profile-card {'))
  assert.match(profiles, /\.profiles-list\.is-expanded,[\s\S]*max-height:[\s\S]*overflow-y:\s*auto/)
  assert.match(setup, /\.agents-cards\.is-expanded\s*\{[\s\S]*max-height:[\s\S]*overflow-y:\s*auto/)
  assert.match(setup, /PROFILE_PREVIEW_LIMIT\s*=\s*6/)
  assert.match(setup, /AGENT_CONFIG_PREVIEW_LIMIT\s*=\s*4/)
  assert.match(setup, /v-for="\(profile, idx\) in visibleProfiles"/)
  assert.match(setup, /v-for="agent in visibleAgentConfigs"/)
  assert.match(setup, /Show all \$\{profiles\.length\} personas/)
  assert.match(setup, /Show all \$\{agentConfigs\.length\} agent configurations/)
})

test('Setup hides model controls and uses consistent white configuration blocks', () => {
  const setup = readFrontend('src/components/Step2EnvSetup.vue')
  const designSystem = readFrontend('src/styles/design-system.css')

  assert.doesNotMatch(setup, /class="llm-settings-panel"/)
  assert.doesNotMatch(setup, /class="llm-select-control"/)
  assert.doesNotMatch(setup, /\{\{ selectedModel \}\}/)
  assert.doesNotMatch(setup, /\{\{ selectedReasoningEffort \}\}/)
  assert.match(setup, /\.step-card\.active\s*\{[\s\S]*background:\s*#FFF/)
  assert.match(setup, /\.config-detail-panel\s*\{[\s\S]*gap:\s*20px/)
  assert.match(setup, /\.config-block\s*\{[\s\S]*margin:\s*0;[\s\S]*background:\s*#FFF/)
  assert.match(
    designSystem,
    /\.main-view\s+\.step-card\s*>\s*\.card-header\s*\{\s*background:\s*#fff;/
  )
})

test('Setup numbered section headers scroll normally with their cards', () => {
  const setup = readFrontend('src/components/Step2EnvSetup.vue')
  const designSystem = readFrontend('src/styles/design-system.css')

  assert.doesNotMatch(setup, /\.card-header\s*\{[\s\S]*position:\s*sticky;/)
  assert.doesNotMatch(designSystem, /\.env-setup-panel\s+\.step-card\s*\{\s*overflow:\s*visible;/)
})

test('Setup completes cleanly with its simulation locked to 40 rounds', () => {
  const setup = readFrontend('src/components/Step2EnvSetup.vue')

  assert.match(setup, /class="step-card"\s+:class="\{ 'completed': phase >= 4 \}"/)
  assert.match(setup, /v-if="phase >= 4"\s+class="badge success"/)
  assert.doesNotMatch(setup, /class="rounds-config-section"/)
  assert.doesNotMatch(setup, /class="run-mode-grid"/)
  assert.match(setup, /const LOCKED_DEMO_ROUNDS = 40/)
  assert.match(setup, /emit\('next-step', \{ maxRounds: LOCKED_DEMO_ROUNDS \}\)/)
})

test('Setup cards and controls reflow for narrow workbench panels', () => {
  const setup = readFrontend('src/components/Step2EnvSetup.vue')

  assert.match(setup, /container-type:\s*inline-size/)
  assert.match(setup, /\.stat-card\s*\{[\s\S]*min-height:\s*86px[\s\S]*padding:\s*14px\s+12px/)
  assert.match(setup, /\.stat-label\s*\{[\s\S]*font-size:\s*11px[\s\S]*line-height:\s*1\.35/)
  assert.match(setup, /@container\s*\(max-width:\s*760px\)/)
  assert.match(setup, /\.stats-grid,[\s\S]*\.config-grid\s*\{[\s\S]*repeat\(2,\s*minmax\(0,\s*1fr\)\)/)
  assert.match(setup, /\.agents-cards\s*\{\s*grid-template-columns:\s*1fr/)
  assert.match(setup, /\.action-group\.dual\s*\{[\s\S]*grid-template-columns:\s*1fr/)
})

test('Setup becomes a single page-level scroll after graph and workbench stack', () => {
  const setup = readFrontend('src/components/Step2EnvSetup.vue')
  const view = readFrontend('src/views/SimulationView.vue')

  assert.match(view, /@media\s*\(max-width:\s*900px\)/)
  assert.match(view, /\.content-area\s*\{[\s\S]*flex-direction:\s*column[\s\S]*overflow-y:\s*auto/)
  assert.match(view, /\.panel-wrapper\.right\s*\{[\s\S]*height:\s*auto[\s\S]*overflow:\s*visible/)
  assert.match(setup, /@media\s*\(max-width:\s*900px\)[\s\S]*\.scroll-container\s*\{[\s\S]*overflow:\s*visible/)
})
