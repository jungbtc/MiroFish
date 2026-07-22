import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const readFrontend = path => readFileSync(resolve(frontendRoot, path), 'utf8')

test('static demo locks five YC evidence files and the exact scenario prompt', () => {
  const home = readFrontend('src/views/Home.vue')
  const scenario = readFrontend('src/demo/fixtures/scenario.js')

  assert.match(home, /VITE_DEMO_MODE/)
  assert.match(home, /yc_agi_native_batch_blueprint_w27\.pdf/)
  assert.match(home, /frontier_lab_agent_economy_outlook_2027\.pdf/)
  assert.match(home, /agent_leverage_signals_w27\.txt/)
  assert.match(home, /tiny_team_selection_signals\.md/)
  assert.match(home, /lp_thesis_agi_native_accelerators\.md/)
  assert.match(home, /REQUIREMENT as DEMO_REQUIREMENT/)
  assert.match(home, /:readonly="inputLocked"/)
  assert.doesNotMatch(home, /Locked demo evidence/)
  assert.match(scenario, /Y Combinator is deciding how to prepare for the AGI era/)
})

test('static demo uses the simple launcher without metrics or model configuration', () => {
  const home = readFrontend('src/views/Home.vue')

  assert.doesNotMatch(home, /ModelSettingsSelector/)
  assert.doesNotMatch(home, /metrics-row/)
  assert.match(home, /whatIfDemo v\.0\.0\.1/)
})
