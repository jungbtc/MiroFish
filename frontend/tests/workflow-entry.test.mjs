import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const projectRoot = resolve(frontendRoot, '..')
const readFrontend = path => readFileSync(resolve(frontendRoot, path), 'utf8')
const readProject = path => readFileSync(resolve(projectRoot, path), 'utf8')

test('home remains the ontology and simulation launcher', () => {
  const home = readFrontend('src/views/Home.vue')

  assert.match(home, /ModelSettingsSelector/)
  assert.match(home, /HistoryDatabase/)
  assert.match(home, /setPendingUpload\(/)
  assert.match(
    home,
    /setPendingUpload\([\s\S]*formData\.value\.model,[\s\S]*formData\.value\.reasoningEffort[\s\S]*\)/
  )
  assert.match(home, /name:\s*'Process'/)
  assert.match(home, /projectId:\s*'new'/)
  assert.match(home, /\['pdf', 'md', 'txt'\]/)
  assert.doesNotMatch(home, /importDeepResearch/)
})

test('core report continues into research and decision refinement', () => {
  const router = readFrontend('src/router/index.js')
  const reportStep = readFrontend('src/components/Step4Report.vue')

  for (const routeName of [
    'Home',
    'Process',
    'Simulation',
    'SimulationRun',
    'Report',
    'Interaction',
    'ReportRefinement',
    'DecisionWorkspace'
  ]) {
    assert.match(router, new RegExp(`name:\\s*'${routeName}'`))
  }
  assert.doesNotMatch(router, /name:\s*'DecisionImport'/)
  assert.match(router, /path:\s*'\/report\/:reportId\/refinement'/)
  assert.match(router, /path:\s*'\/decision\/:runId'/)
  assert.match(reportStep, /name:\s*'ReportRefinement'/)
  assert.doesNotMatch(reportStep, /name:\s*'Interaction'/)
})

test('the refinement workspace owns durable public research and private pruning', () => {
  const workspace = readFrontend('src/views/DecisionWorkspaceView.vue')
  const api = readFrontend('src/api/v2.js')

  assert.match(workspace, /getCoreRefinement/)
  assert.match(workspace, /startCoreResearch/)
  assert.match(workspace, /cancelCoreResearch/)
  assert.match(workspace, /confidential answers never enter web search/i)
  assert.match(workspace, /Competing decision paths/)
  assert.match(api, /\/api\/v2\/core\/reports\/\$\{encodeURIComponent\(reportId\)\}\/refinement/)
})

test('pending simulation uploads retain model and reasoning controls', () => {
  const pendingUpload = readFrontend('src/store/pendingUpload.js')

  assert.match(pendingUpload, /model/)
  assert.match(pendingUpload, /reasoningEffort/)
  assert.match(pendingUpload, /DEFAULT_MODEL/)
  assert.match(pendingUpload, /DEFAULT_REASONING_EFFORT/)
})

test('home no longer presents decision refinement as a separate add-on', () => {
  const home = readFrontend('src/views/Home.vue')

  assert.doesNotMatch(home, /DecisionImport/)
  assert.doesNotMatch(home, /decision-addon/)
})

test('README presents one continuous decision workflow', () => {
  const readme = readProject('README.md')

  assert.match(readme, /Deep Research/i)
  assert.match(readme, /internal (?:fact|evidence)/i)
  assert.doesNotMatch(readme, /Optional Add-on/i)
})
