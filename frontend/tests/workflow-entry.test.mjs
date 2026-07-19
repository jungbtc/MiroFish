import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
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

test('core report continues into bounded decision refinement', () => {
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

test('the refinement workspace uses report evidence and bounded private pruning', () => {
  const workspace = readFrontend('src/views/DecisionWorkspaceView.vue')
  const api = readFrontend('src/api/v2.js')

  assert.match(workspace, /getCoreRefinement/)
  assert.doesNotMatch(workspace, /startCoreResearch/)
  assert.doesNotMatch(workspace, /cancelCoreResearch/)
  assert.doesNotMatch(workspace, /PUBLIC DEEP RESEARCH/)
  assert.match(workspace, /bounded, high-value internal facts/i)
  assert.match(workspace, /case_title/)
  assert.match(workspace, /FINAL APPROVAL OUTCOME/)
  assert.match(workspace, /EVIDENCE REFINEMENT COMPLETE · DECISION BLOCKED/)
  assert.match(workspace, /Provide next internal input/)
  assert.match(workspace, /COMPILED EXECUTION PLAN/)
  assert.match(workspace, /EVIDENCE OPERATIONALIZED/)
  assert.match(workspace, /Why this action exists/)
  assert.match(workspace, /Management action gate/i)
  assert.match(workspace, /Download final brief/)
  assert.match(workspace, /Download current brief/)
  assert.match(workspace, /Finalize qualitative decision/)
  assert.match(workspace, /COMPILED EXECUTION PLAN/)
  assert.match(workspace, /Decision record & methodology/)
  assert.match(workspace, /looksLikeExecutableAction/)
  assert.match(workspace, /Competing decision paths/)
  assert.match(workspace, /Add missing question/)
  assert.match(workspace, /Decision knowledge tree/)
  assert.match(workspace, /knowledgeBloom/)
  assert.match(workspace, /MAX_INTERNAL_QUESTIONS = 4/)
  assert.match(workspace, /slice\(0, MAX_INTERNAL_QUESTIONS\)/)
  assert.match(workspace, /setTimeout\(revealLatestBranch, 780\)/)
  assert.match(workspace, /Choose the decision method/)
  assert.match(workspace, /Confirm model and calculate/)
  assert.match(workspace, /confirmDecisionModel/)
  assert.match(workspace, /confirmDecisionActions/)
  assert.match(workspace, /assignExecutionOwners/)
  assert.match(workspace, /Assign accountable owners/)
  assert.match(workspace, /evaluateDecisionAnalysis/)
  assert.match(workspace, /ensureInternalRun/)
  assert.match(workspace, /forkDecisionRun/)
  assert.match(api, /proposeInternalQuestion/)
  assert.match(api, /forkDecisionRun/)
  assert.match(api, /decision-model\/confirm/)
  assert.match(api, /actions\/confirm/)
  assert.match(api, /decision-analysis\/evaluate/)
  assert.match(api, /decision-analysis\/waive/)
  assert.match(api, /\/api\/v2\/runs\/\$\{encodeURIComponent\(runId\)\}\/fork/)
  assert.doesNotMatch(api, /startCoreResearch/)
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

  assert.match(readme, /bounded/i)
  assert.match(readme, /Information Value/i)
  assert.match(readme, /internal (?:fact|evidence)/i)
  assert.doesNotMatch(readme, /Optional Add-on/i)
})

test('Chinese is not exposed or restored as an application locale', () => {
  const languages = JSON.parse(readProject('locales/languages.json'))
  const i18n = readFrontend('src/i18n/index.js')
  const switcher = readFrontend('src/components/LanguageSwitcher.vue')
  const process = readFrontend('src/views/Process.vue')

  assert.equal(languages.zh, undefined)
  assert.equal(existsSync(resolve(projectRoot, 'locales/zh.json')), false)
  assert.match(i18n, /const DEFAULT_LOCALE = 'en'/)
  assert.match(i18n, /savedLocale && messages\[savedLocale\] \? savedLocale : DEFAULT_LOCALE/)
  assert.match(i18n, /fallbackLocale: DEFAULT_LOCALE/)
  assert.match(switcher, /availableLocales\.length > 1/)
  assert.doesNotMatch(process, /zh-CN/)
})
