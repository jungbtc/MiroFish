import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import test from 'node:test'
import { fileURLToPath, pathToFileURL } from 'node:url'

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const fromFrontend = path => resolve(frontendRoot, path)
const readFrontend = path => readFileSync(fromFrontend(path), 'utf8')

const replayModulePath = fromFrontend('src/dev/devReplay.js')
const replayModule = async () => import(pathToFileURL(replayModulePath).href)

const fullManifest = {
  projectId: 'proj_replay_fixture',
  simulationId: 'sim_replay_fixture',
  reportId: 'report_replay_fixture',
  refinementRunId: 'v2_20260719000000_replay',
  title: 'Replay fixture'
}

const sourceSection = (source, startMarker, endMarker) => {
  const start = source.indexOf(startMarker)
  assert.notEqual(start, -1, `Missing source marker: ${startMarker}`)
  const end = source.indexOf(endMarker, start + startMarker.length)
  assert.notEqual(end, -1, `Missing source marker after ${startMarker}: ${endMarker}`)
  return source.slice(start, end)
}

test('developer replay is a real production-page route with a global phase bar', () => {
  const router = readFrontend('src/router/index.js')
  const app = readFrontend('src/App.vue')
  const home = readFrontend('src/views/Home.vue')
  const history = readFrontend('src/components/HistoryDatabase.vue')

  assert.equal(existsSync(replayModulePath), true)
  assert.equal(existsSync(fromFrontend('src/views/DevReplayView.vue')), true)
  assert.equal(existsSync(fromFrontend('src/components/DevReplayBar.vue')), true)

  assert.match(router, /path:\s*['"]\/dev\/replay['"]/)
  assert.match(router, /name:\s*['"]DevReplay['"]/)
  assert.match(router, /isDevReplayEnabled/)
  assert.match(app, /<DevReplayBar\b/)
  assert.match(app, /import DevReplayBar/)
  assert.match(home, /name:\s*['"]DevReplay['"]/)
  assert.match(home, /<HistoryDatabase\s+:dev-replay="replayReadOnly"/)
  assert.match(history, /:disabled="importing \|\| devReplay"/)
  assert.match(history, /:disabled="devReplay"/)

  const importHandler = sourceSection(history, 'const handleImportFile = async (event) => {', 'const downloadBlob = (blob, filename) => {')
  assert.match(importHandler, /if\s*\(props\.devReplay\)\s*\{[\s\S]*return/)
  assert.ok(importHandler.indexOf('if (props.devReplay)') < importHandler.indexOf('importSimulationBundle(file)'))

  const bar = readFrontend('src/components/DevReplayBar.vue')
  assert.match(bar, /getReplayPhases/)
  assert.match(bar, /isDevReplayActive/)
  assert.match(bar, /phase\.available|:disabled=/)
})

test('phase targets use the actual workflow routes and preserve replay=1', async () => {
  const { buildReplayTarget, getReplayPhases } = await replayModule()

  assert.equal(typeof buildReplayTarget, 'function')
  assert.equal(typeof getReplayPhases, 'function')

  const expectations = {
    intake: ['Home', undefined],
    knowledge: ['Process', ['projectId', fullManifest.projectId]],
    setup: ['Simulation', ['simulationId', fullManifest.simulationId]],
    simulation: ['SimulationRun', ['simulationId', fullManifest.simulationId]],
    report: ['Report', ['reportId', fullManifest.reportId]],
    decision: ['DecisionWorkspace', ['runId', fullManifest.refinementRunId]]
  }

  for (const [phase, [routeName, param]] of Object.entries(expectations)) {
    const target = buildReplayTarget(phase, fullManifest)
    assert.ok(target, `${phase} should be available for a complete manifest`)
    assert.equal(target.name, routeName)
    assert.equal(target.query?.replay, '1')
    if (param) assert.equal(target.params?.[param[0]], param[1])
  }

  // These hand-off IDs let the production Step 3 and Step 4 controls advance
  // without generating a new report or initializing a new decision run.
  assert.equal(buildReplayTarget('simulation', fullManifest).query.report, fullManifest.reportId)
  assert.equal(buildReplayTarget('report', fullManifest).query.run, fullManifest.refinementRunId)

  const phases = getReplayPhases(fullManifest)
  assert.deepEqual(phases.map(phase => phase.id), [
    'intake',
    'knowledge',
    'setup',
    'simulation',
    'report',
    'decision'
  ])
  assert.equal(phases.every(phase => phase.available && phase.target?.query?.replay === '1'), true)
})

test('partial manifests progressively disable only phases whose saved IDs are missing', async () => {
  const { getReplayPhases } = await replayModule()
  const availability = manifest => Object.fromEntries(
    getReplayPhases(manifest).map(phase => [phase.id, phase.available])
  )

  assert.deepEqual(availability({ projectId: fullManifest.projectId }), {
    intake: true,
    knowledge: true,
    setup: false,
    simulation: false,
    report: false,
    decision: false
  })

  assert.deepEqual(availability({
    projectId: fullManifest.projectId,
    simulationId: fullManifest.simulationId
  }), {
    intake: true,
    knowledge: true,
    setup: true,
    simulation: true,
    report: false,
    decision: false
  })

  assert.deepEqual(availability({
    projectId: fullManifest.projectId,
    simulationId: fullManifest.simulationId,
    reportId: fullManifest.reportId
  }), {
    intake: true,
    knowledge: true,
    setup: true,
    simulation: true,
    report: true,
    decision: false
  })
})

test('Axios fails closed on every non-GET request while replay is active', async () => {
  const replay = await replayModule()
  const api = readFrontend('src/api/index.js')

  assert.equal(replay.DEV_REPLAY_MUTATION_BLOCKED, 'DEV_REPLAY_MUTATION_BLOCKED')
  assert.equal(typeof replay.isReplayMutationBlocked, 'function')
  assert.equal(replay.isReplayMutationBlocked('get', true), false)
  assert.equal(replay.isReplayMutationBlocked('GET', true), false)
  assert.equal(replay.isReplayMutationBlocked('post', false), false)

  for (const method of ['post', 'put', 'patch', 'delete', 'head', 'options']) {
    assert.equal(
      replay.isReplayMutationBlocked(method, true),
      true,
      `${method.toUpperCase()} must be blocked before Axios reaches its adapter`
    )
  }

  assert.match(api, /service\.interceptors\.request\.use/)
  assert.match(api, /isReplayMutationBlocked/)
  assert.match(api, /DEV_REPLAY_MUTATION_BLOCKED/)
  assert.match(api, /config\.method/)
  assert.match(api, /\.code\s*=\s*DEV_REPLAY_MUTATION_BLOCKED/)
})

test('knowledge replay loads the saved graph without creating or rebuilding workflow state', () => {
  const process = readFrontend('src/views/MainView.vue')
  const graphStep = readFrontend('src/components/Step1GraphBuild.vue')

  assert.match(process, /:devReplay="isDevReplay"/)
  assert.match(process, /currentProjectId\.value === ['"]new['"][\s\S]*Replay blocked/)

  const loadProject = sourceSection(process, 'const loadProject = async () => {', 'const updatePhaseByStatus = (status) => {')
  assert.match(loadProject, /if\s*\(isDevReplay\.value\)/)
  assert.match(loadProject, /await loadGraph\(res\.data\.graph_id\)/)
  assert.match(loadProject, /else if[\s\S]*startBuildGraph\(\)/)

  const build = sourceSection(process, 'const startBuildGraph = async () => {', 'const startGraphPolling = () => {')
  assert.match(build, /if\s*\(isDevReplay\.value\)\s*\{[\s\S]*return/)
  assert.ok(build.indexOf('if (isDevReplay.value)') < build.indexOf('buildGraph({'))

  const enterSetup = sourceSection(graphStep, 'const handleEnterEnvSetup = async () => {', 'const selectOntologyItem = (item, type) => {')
  assert.match(enterSetup, /if\s*\(props\.devReplay\)\s*return/)
  assert.ok(enterSetup.indexOf('if (props.devReplay)') < enterSetup.indexOf('createSimulation({'))
})

test('Step 2 hydrates saved profiles and configuration instead of preparing again', () => {
  const setup = readFrontend('src/components/Step2EnvSetup.vue')
  const view = readFrontend('src/views/SimulationView.vue')

  assert.match(view, /:devReplay="isDevReplay"/)
  assert.match(setup, /devReplay:\s*\{\s*type:\s*Boolean/)

  const mounted = sourceSection(setup, 'onMounted(() => {', 'onUnmounted(() => {')
  assert.match(mounted, /props\.devReplay/)
  assert.match(mounted, /loadPreparedData\(\)/)
  assert.match(mounted, /else\s*\{[\s\S]*startPrepareSimulation\(\)/)

  const hydration = sourceSection(setup, 'const loadPreparedData = async () => {', '// Scroll log to bottom')
  assert.match(hydration, /fetchProfilesRealtime\(\)/)
  assert.match(hydration, /getSimulationConfigRealtime\(props\.simulationId\)/)
  assert.doesNotMatch(hydration, /prepareSimulation\s*\(/)

  const prepare = sourceSection(setup, 'const startPrepareSimulation = async () => {', 'const startPolling = () => {')
  assert.match(prepare, /if\s*\(props\.devReplay\)\s*\{[\s\S]*return/)
  assert.ok(
    prepare.indexOf('if (props.devReplay)') < prepare.indexOf('prepareSimulation({'),
    'the replay guard must run before the preparation POST'
  )
})

test('Step 3 hydrates persisted GET outcomes and never starts or regenerates in replay', () => {
  const simulation = readFrontend('src/components/Step3Simulation.vue')
  const view = readFrontend('src/views/SimulationRunView.vue')

  assert.match(view, /:devReplay="isDevReplay"/)
  assert.match(view, /:reportId="replayReportId"/)
  assert.match(simulation, /devReplay:\s*\{\s*type:\s*Boolean/)
  assert.match(simulation, /getRunStatus/)
  assert.match(simulation, /getRunStatusDetail/)

  const mounted = sourceSection(simulation, 'onMounted(() => {', 'onUnmounted(() => {')
  assert.match(mounted, /if\s*\(props\.devReplay\)/)
  assert.match(mounted, /fetchRunStatus\(\)/)
  assert.match(mounted, /fetchRunStatusDetail\(\)/)
  assert.match(mounted, /else\s*\{[\s\S]*doStartSimulation\(\)/)

  const start = sourceSection(simulation, 'const doStartSimulation = async () => {', '// \u505c\u6b62\u6a21\u62df')
  assert.match(start, /if\s*\(props\.devReplay\)\s*\{[\s\S]*return/)
  assert.ok(
    start.indexOf('if (props.devReplay)') < start.indexOf('startSimulation(params)'),
    'the replay guard must run before the simulation-start POST'
  )

  const next = sourceSection(simulation, 'const handleNextStep = async () => {', '// Scroll log to bottom')
  const replayBranch = next.indexOf('if (props.devReplay)')
  const generation = next.indexOf('generateReport({')
  assert.ok(replayBranch >= 0 && generation > replayBranch)
  assert.match(next.slice(replayBranch, generation), /name:\s*['"]Report['"]/)
  assert.match(next.slice(replayBranch, generation), /return/)
})

test('simulation page lifecycles bypass stop, close, restart, and refresh behavior in replay', () => {
  const setupView = readFrontend('src/views/SimulationView.vue')
  const runView = readFrontend('src/views/SimulationRunView.vue')

  const setupMount = sourceSection(setupView, 'onMounted(async () => {', '</script>')
  assert.match(setupMount, /if\s*\(!isDevReplay\.value\)\s*\{[\s\S]*checkAndStopRunningSimulation\(\)/)
  assert.match(setupMount, /else\s*\{[\s\S]*Dev Replay/)

  const goBack = sourceSection(runView, 'const handleGoBack = async () => {', 'const handleNextStep = () => {')
  const replayGuard = goBack.indexOf('if (isDevReplay.value)')
  const firstDestructiveCall = Math.min(
    ...['getEnvStatus(', 'closeSimulationEnv(', 'stopSimulation(']
      .map(call => goBack.indexOf(call))
      .filter(index => index >= 0)
  )
  assert.ok(replayGuard >= 0 && firstDestructiveCall > replayGuard)
  assert.match(goBack.slice(replayGuard, firstDestructiveCall), /router\.push\([\s\S]*return/)
  assert.match(runView, /const isSimulating = computed\(\(\) => !isDevReplay\.value/)
})

test('decision replay disables controls and guards every mutation handler', () => {
  const workspace = readFrontend('src/views/DecisionWorkspaceView.vue')

  assert.match(workspace, /const isDevReplay = computed\(\(\) => route\.query\.replay === ['"]1['"]\)/)
  assert.match(workspace, /dev-replay-readonly/)
  assert.match(workspace, /EDITING CONTROLS ARE READ-ONLY/)
  assert.match(workspace, /:disabled="isDevReplay \|\| evaluatingStop"/)
  assert.match(workspace, /:disabled="isDevReplay \|\| calculatingAnalysis"/)
  assert.match(workspace, /:disabled="isDevReplay \|\| !allModelConfirmations \|\| confirmingModel"/)
  assert.match(workspace, /:disabled="isDevReplay \|\| proposingQuestion/)
  assert.match(workspace, /:disabled="isDevReplay \|\| submittingAnswer/)

  const handlers = [
    ['submitAnswer', 'submitQuestionProposal'],
    ['submitQuestionProposal', 'confirmCurrentDecisionModel'],
    ['confirmCurrentDecisionModel', 'recalculateDecisionAnalysis'],
    ['recalculateDecisionAnalysis', 'reevaluateStop'],
    ['reevaluateStop', 'downloadMemo']
  ]

  for (const [handler, nextHandler] of handlers) {
    const body = sourceSection(
      workspace,
      `const ${handler} = async () => {`,
      `const ${nextHandler} = async () => {`
    )
    assert.match(body, /if\s*\(isDevReplay\.value\)\s*return/, `${handler} must fail closed in replay`)
  }

  const loadRun = sourceSection(workspace, 'const loadRun = async () => {', 'const chooseNextQuestion = () => {')
  assert.match(loadRun, /isDevReplay\.value && reportId\.value/)
  assert.match(loadRun, /getDecisionRun\(runId\.value\)/)
})
