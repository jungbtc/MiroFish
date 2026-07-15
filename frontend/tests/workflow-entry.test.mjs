import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const projectRoot = resolve(frontendRoot, '..')
const readFrontend = path => readFileSync(resolve(frontendRoot, path), 'utf8')
const readProject = path => readFileSync(resolve(projectRoot, path), 'utf8')

test('home remains the primary ontology and simulation launcher', () => {
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

test('core and optional decision routes coexist', () => {
  const router = readFrontend('src/router/index.js')

  for (const routeName of [
    'Home',
    'Process',
    'Simulation',
    'SimulationRun',
    'Report',
    'Interaction',
    'DecisionImport',
    'DecisionWorkspace'
  ]) {
    assert.match(router, new RegExp(`name:\\s*'${routeName}'`))
  }
  assert.match(router, /path:\s*'\/decision'/)
  assert.match(router, /path:\s*'\/decision\/:runId'/)
})

test('the optional importer owns Deep Research ingestion', () => {
  const importer = readFrontend('src/views/DecisionImportView.vue')

  assert.match(importer, /importDeepResearch/)
  assert.match(importer, /name:\s*'DecisionWorkspace'/)
  assert.match(importer, /\.pdf,\.md,\.markdown,\.json/)
  assert.match(importer, /decisionImport\.corePreservedTitle/)
})

test('pending simulation uploads retain model and reasoning controls', () => {
  const pendingUpload = readFrontend('src/store/pendingUpload.js')

  assert.match(pendingUpload, /model/)
  assert.match(pendingUpload, /reasoningEffort/)
  assert.match(pendingUpload, /DEFAULT_MODEL/)
  assert.match(pendingUpload, /DEFAULT_REASONING_EFFORT/)
})

test('English and Chinese copy position v2 as optional', () => {
  const english = JSON.parse(readProject('locales/en.json'))
  const chinese = JSON.parse(readProject('locales/zh.json'))

  assert.match(english.home.workflowSequence, /Workflow/)
  assert.match(english.decisionAddon.kicker, /Optional/i)
  assert.match(english.decisionImport.corePreservedTitle, /preserved/i)
  assert.match(chinese.home.workflowSequence, /工作流/)
  assert.match(chinese.decisionAddon.kicker, /可选/)
  assert.match(chinese.decisionImport.corePreservedTitle, /保留/)
})

test('README presents the primary workflow before the optional add-on', () => {
  const readme = readProject('README.md')
  const primaryIndex = readme.indexOf('## 🔄 Primary Workflow')
  const optionalIndex = readme.indexOf('## 🧭 Optional Add-on')

  assert.ok(primaryIndex >= 0)
  assert.ok(optionalIndex > primaryIndex)
  assert.doesNotMatch(readme, /newest main workflow/i)
  assert.doesNotMatch(readme, /legacy (?:engine|social|Graphiti|simulation|workflow)/i)
  assert.match(readme.slice(primaryIndex, optionalIndex), /Preview[\s\S]*Balanced[\s\S]*Full Fidelity/)
})
