// Demo fixture handlers for Phase 1 (ontology/graph build) and Phase 2
// (simulation environment prepare). Route contract: see src/demo/adapter.js.
//
// Two scripted clock jobs drive everything here (src/demo/clock.js):
//   - 'graphBuild' (src/demo/timings.js GRAPH_BUILD_SECONDS) backs the
//     ontology -> graph_building -> graph_completed lifecycle and the
//     progressive graph node/edge reveal.
//   - 'prepare' (PREPARE_SECONDS) backs the Step 2 environment setup
//     staging: analyzing_entities -> generating_profiles ->
//     generating_config -> copying_scripts -> completed.
//
// Endpoints that belong here:
//   GET  /api/simulation/history
//   POST /api/simulation/import
//   GET  /api/simulation/:id/export
//   POST /api/graph/ontology/generate
//   POST /api/graph/build
//   GET  /api/graph/task/:taskId
//   GET  /api/graph/data/:graphId
//   GET  /api/graph/project/:projectId
//   POST /api/simulation/create
//   POST /api/simulation/env-status
//   POST /api/simulation/close-env
//   POST /api/simulation/stop
//   GET  /api/simulation/:id
//   POST /api/simulation/prepare
//   POST /api/simulation/prepare/status
//   GET  /api/simulation/:id/profiles/realtime
//   GET  /api/simulation/:id/config/realtime
//   GET  /api/simulation/:id/config

import { startJob, ensureJob, jobStarted, jobFraction } from '../clock.js'
import { GRAPH_BUILD_SECONDS, PREPARE_SECONDS } from '../timings.js'
import { IDS } from '../fixtures/scenario.js'
import projectFixture from '../fixtures/project.js'
import { nodes as graphNodes, edges as graphEdges } from '../fixtures/graph.js'
import profilesFixture from '../fixtures/profiles.js'
import simConfigFixture from '../fixtures/simConfig.js'
import historyFixture from '../fixtures/history.js'

const GRAPH_BUILD_TASK_ID = 'task_demo_build'
const PREPARE_TASK_ID = 'task_demo_prepare'
const CHUNK_COUNT = 19

const clamp01 = f => Math.min(1, Math.max(0, f))

// --- Phase 1: graph build task staging ------------------------------------
// 4 stages, thresholds are cumulative fractions of GRAPH_BUILD_SECONDS.
const GRAPH_STAGES = [
  { key: 'extracting_entities', name: 'Extracting Entities', end: 0.25, message: 'Extracting entities from uploaded documents...' },
  { key: 'resolving_relations', name: 'Resolving Relations', end: 0.55, message: 'Resolving relationships between entities...' },
  { key: 'writing_episodes', name: 'Writing Episodes', end: 0.85, message: 'Writing episodes into the knowledge graph...' },
  { key: 'indexing', name: 'Indexing', end: 1, message: 'Indexing knowledge graph for retrieval...' }
]

const resolveStage = (f, stages) => {
  const clamped = clamp01(f)
  let start = 0
  for (let i = 0; i < stages.length; i++) {
    const stage = stages[i]
    if (clamped < stage.end || i === stages.length - 1) {
      const span = stage.end - start
      const stageProgress = span > 0 ? clamp01((clamped - start) / span) : 1
      return { index: i + 1, stage, stageProgress }
    }
    start = stage.end
  }
  // Unreachable (stages always has a last element), but keep a safe fallback.
  return { index: stages.length, stage: stages[stages.length - 1], stageProgress: 1 }
}

const buildGraphTaskPayload = taskId => {
  const f = jobFraction('graphBuild', GRAPH_BUILD_SECONDS)
  const done = f >= 1
  const { index, stage, stageProgress } = resolveStage(f, GRAPH_STAGES)
  const currentItem = Math.min(CHUNK_COUNT, Math.ceil(clamp01(f) * CHUNK_COUNT))

  return {
    task_id: taskId || GRAPH_BUILD_TASK_ID,
    task_type: 'graph_build',
    status: done ? 'completed' : 'processing',
    progress: Math.round(clamp01(f) * 100),
    message: stage.message,
    progress_detail: {
      current_stage: stage.key,
      current_stage_name: stage.name,
      stage_index: index,
      total_stages: GRAPH_STAGES.length,
      stage_progress: stageProgress,
      current_item: currentItem,
      total_items: CHUNK_COUNT,
      item_description: `Processing chunk ${currentItem} of ${CHUNK_COUNT}`
    },
    result: done
      ? {
          project_id: IDS.projectId,
          graph_id: IDS.graphId,
          node_count: graphNodes.length,
          edge_count: graphEdges.length,
          chunk_count: CHUNK_COUNT
        }
      : null,
    error: null
  }
}

const revealedGraphData = () => {
  const f = jobFraction('graphBuild', GRAPH_BUILD_SECONDS)
  const done = f >= 1
  const sorted = [...graphNodes].sort((a, b) => Date.parse(a.created_at) - Date.parse(b.created_at))
  const total = sorted.length
  const revealCount = done ? total : Math.ceil(clamp01(f) * total)
  const revealedNodes = sorted.slice(0, revealCount)
  const revealedIds = new Set(revealedNodes.map(n => n.uuid))
  const revealedEdges = done
    ? graphEdges
    : graphEdges.filter(e => revealedIds.has(e.source_node_uuid) && revealedIds.has(e.target_node_uuid))

  return {
    nodes: revealedNodes,
    edges: revealedEdges,
    node_count: revealedNodes.length,
    edge_count: revealedEdges.length
  }
}

const currentProjectStatus = () => {
  if (!jobStarted('graphBuild')) return { status: 'ontology_generated' }
  const f = jobFraction('graphBuild', GRAPH_BUILD_SECONDS)
  if (f >= 1) return { status: 'graph_completed' }
  return { status: 'graph_building', graph_build_task_id: GRAPH_BUILD_TASK_ID }
}

// --- Phase 2: simulation prepare staging ----------------------------------
// 4 stages; current_stage/current_stage_name must literally be these
// snake_case keys — Step2EnvSetup.vue string-matches current_stage_name
// against 'generating_profiles' / 'generating_config' / 'copying_scripts'.
const PREPARE_STAGES = [
  { key: 'analyzing_entities', end: 0.15 },
  { key: 'generating_profiles', end: 0.70 },
  { key: 'generating_config', end: 0.90 },
  { key: 'copying_scripts', end: 1 }
]

const PREPARE_STAGE_MESSAGES = {
  analyzing_entities: 'Analyzing knowledge graph entities...',
  generating_profiles: 'Generating agent personas...',
  generating_config: 'Generating dual-platform simulation configuration...',
  copying_scripts: 'Copying simulation runtime scripts...'
}

// The generating_profiles window (0.15..0.70 of the prepare job) maps onto
// revealing all 16 profiles; 0 before it starts, 1 once it's done.
const profileFractionFor = f => clamp01((f - 0.15) / 0.55)
const profilesRevealedCount = f => Math.min(profilesFixture.length, Math.ceil(profileFractionFor(f) * profilesFixture.length))

const buildPrepareStatusPayload = () => {
  const f = jobFraction('prepare', PREPARE_SECONDS)
  const done = f >= 1
  const { index, stage, stageProgress } = resolveStage(f, PREPARE_STAGES)

  let currentItem = 0
  let totalItems = 0
  let itemDescription = ''

  if (stage.key === 'generating_profiles') {
    currentItem = profilesRevealedCount(f)
    totalItems = profilesFixture.length
    itemDescription = profilesFixture[Math.max(0, currentItem - 1)]?.username || 'Preparing first persona...'
  } else if (stage.key === 'analyzing_entities') {
    itemDescription = 'Scanning knowledge graph for simulation-relevant entities'
  } else if (stage.key === 'generating_config') {
    itemDescription = 'Compiling platform recommendation-algorithm weights'
  } else if (stage.key === 'copying_scripts') {
    itemDescription = 'Copying agent runtime scripts into the simulation sandbox'
  }

  return {
    task_id: PREPARE_TASK_ID,
    task_type: 'simulation_prepare',
    status: done ? 'completed' : 'processing',
    already_prepared: done,
    progress: Math.round(clamp01(f) * 100),
    message: done ? 'Simulation environment prepared.' : PREPARE_STAGE_MESSAGES[stage.key],
    progress_detail: {
      current_stage: stage.key,
      current_stage_name: stage.key,
      stage_index: index,
      total_stages: PREPARE_STAGES.length,
      stage_progress: stageProgress,
      current_item: currentItem,
      total_items: totalItems,
      item_description: itemDescription
    },
    result: done ? { simulation_id: IDS.simulationId, entities_processed: profilesFixture.length } : null,
    error: null
  }
}

export const routes = [
  // --- Home -----------------------------------------------------------
  {
    method: 'get',
    pattern: /^\/api\/simulation\/history$/,
    latency: 'read',
    handler: ({ query }) => {
      const limit = Number(query.limit) || historyFixture.length
      return historyFixture.slice(0, limit)
    }
  },
  {
    method: 'post',
    pattern: /^\/api\/simulation\/import$/,
    latency: 'read',
    handler: () => ({ imported: { simulations: [] }, skipped: { simulations: [] } })
  },
  {
    method: 'get',
    pattern: /^\/api\/simulation\/(?<id>[^/?]+)\/export$/,
    latency: 'read',
    handler: () => new Blob([JSON.stringify({ demo: true })], { type: 'application/zip' })
  },

  // --- Phase 1: ontology + graph build ---------------------------------
  {
    method: 'post',
    pattern: /^\/api\/graph\/ontology\/generate$/,
    latency: 'ai',
    handler: () => ({ ...projectFixture, status: 'ontology_generated' })
  },
  {
    method: 'post',
    pattern: /^\/api\/graph\/build$/,
    latency: 'read',
    handler: () => {
      startJob('graphBuild')
      return { task_id: GRAPH_BUILD_TASK_ID }
    }
  },
  {
    method: 'get',
    pattern: /^\/api\/graph\/task\/(?<taskId>[^/?]+)$/,
    latency: 'read',
    handler: ({ params }) => {
      ensureJob('graphBuild')
      return buildGraphTaskPayload(params.taskId)
    }
  },
  {
    method: 'get',
    pattern: /^\/api\/graph\/data\/(?<graphId>[^/?]+)$/,
    latency: 'read',
    handler: () => {
      ensureJob('graphBuild')
      return revealedGraphData()
    }
  },
  {
    method: 'get',
    pattern: /^\/api\/graph\/project\/(?<projectId>[^/?]+)$/,
    latency: 'read',
    handler: () => {
      const { status, graph_build_task_id } = currentProjectStatus()
      return {
        ...projectFixture,
        status,
        ...(graph_build_task_id ? { graph_build_task_id } : {})
      }
    }
  },

  // --- Phase 2: simulation environment setup ----------------------------
  {
    method: 'post',
    pattern: /^\/api\/simulation\/create$/,
    latency: 'read',
    handler: () => ({ simulation_id: IDS.simulationId })
  },
  {
    method: 'post',
    pattern: /^\/api\/simulation\/env-status$/,
    latency: 'read',
    handler: () => ({ env_alive: false })
  },
  {
    method: 'post',
    pattern: /^\/api\/simulation\/close-env$/,
    latency: 'read',
    handler: () => ({})
  },
  {
    method: 'post',
    pattern: /^\/api\/simulation\/stop$/,
    latency: 'read',
    handler: () => ({})
  },
  {
    method: 'post',
    pattern: /^\/api\/simulation\/prepare$/,
    latency: 'read',
    handler: () => {
      const wasFinished = jobStarted('prepare') && jobFraction('prepare', PREPARE_SECONDS) >= 1
      startJob('prepare')
      return {
        already_prepared: wasFinished,
        task_id: PREPARE_TASK_ID,
        expected_entities_count: profilesFixture.length,
        entity_types: [...new Set(profilesFixture.map(p => p.entity_type))]
      }
    }
  },
  {
    method: 'post',
    pattern: /^\/api\/simulation\/prepare\/status$/,
    latency: 'read',
    handler: () => {
      ensureJob('prepare')
      return buildPrepareStatusPayload()
    }
  },
  {
    method: 'get',
    pattern: /^\/api\/simulation\/(?<id>[^/?]+)\/profiles\/realtime$/,
    latency: 'read',
    handler: () => {
      const f = jobFraction('prepare', PREPARE_SECONDS)
      const count = profilesRevealedCount(f)
      return { profiles: profilesFixture.slice(0, count), total_expected: profilesFixture.length }
    }
  },
  {
    method: 'get',
    pattern: /^\/api\/simulation\/(?<id>[^/?]+)\/config\/realtime$/,
    latency: 'read',
    handler: () => {
      const f = jobFraction('prepare', PREPARE_SECONDS)
      if (f < 0.70) return { generation_stage: 'waiting_for_profiles', config_generated: false }
      if (f < 0.90) return { generation_stage: 'generating', config_generated: false }
      return {
        generation_stage: 'completed',
        config_generated: true,
        config: simConfigFixture,
        summary: {
          total_agents: simConfigFixture.agent_configs.length,
          simulation_hours: simConfigFixture.time_config.total_simulation_hours,
          initial_posts_count: simConfigFixture.event_config.initial_posts.length,
          hot_topics_count: simConfigFixture.event_config.hot_topics.length,
          has_twitter_config: Boolean(simConfigFixture.twitter_config),
          has_reddit_config: Boolean(simConfigFixture.reddit_config)
        }
      }
    }
  },
  {
    method: 'get',
    pattern: /^\/api\/simulation\/(?<id>[^/?]+)\/config$/,
    latency: 'read',
    handler: () => simConfigFixture
  },
  {
    method: 'get',
    pattern: /^\/api\/simulation\/(?<id>[^/?]+)$/,
    latency: 'read',
    handler: ({ params }) => {
      const prepared = jobStarted('prepare') && jobFraction('prepare', PREPARE_SECONDS) >= 1
      return {
        simulation_id: params.id,
        project_id: IDS.projectId,
        graph_id: IDS.graphId,
        status: prepared ? 'prepared' : 'created'
      }
    }
  }
]
