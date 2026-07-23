// Demo fixture handlers for Phase 3 (simulation run), Phase 4 (report
// generation), and Phase 5 (report chat / agent interviews) against the
// route entry contract documented in src/demo/adapter.js.
//
// Endpoints implemented here:
//   POST /api/simulation/start
//   GET  /api/simulation/:id/run-status
//   GET  /api/simulation/:id/run-status/detail
//   POST /api/simulation/stop
//   POST /api/report/generate
//   GET  /api/report/:id
//   GET  /api/report/:id/agent-log
//   GET  /api/report/:id/console-log
//   POST /api/report/chat
//   POST /api/simulation/interview/batch

import { IDS, ts } from '../fixtures/scenario.js'
import { RUN_SECONDS, REPORT_SECONDS } from '../timings.js'
import { startJob, ensureCompletedJob, jobStarted, jobFraction } from '../clock.js'
import actions from '../fixtures/actions.js'
import report from '../fixtures/report.js'
import agentLog from '../fixtures/agentLog.js'
import consoleLog from '../fixtures/consoleLog.js'
import { REPORT_CHAT_RESPONSE, interviewReply } from '../fixtures/chat.js'

// 40 rounds at 30 simulated minutes each — matches the fixture time_config
// (20 simulated hours) and the frontend's locked 40-round demo run.
const TOTAL_ROUNDS = 40

// Derives the scripted simulation-run state from wall-clock elapsed time.
// Shared by /run-status and /run-status/detail so both endpoints always
// agree on the current round and action counts.
const deriveRun = () => {
  const fraction = jobFraction('run', RUN_SECONDS)
  const currentRound = Math.min(TOTAL_ROUNDS, Math.ceil(fraction * TOTAL_ROUNDS))
  const visibleActions = actions.filter(action => action.round_num <= currentRound)
  const twitterActions = visibleActions.filter(action => action.platform === 'twitter')
  const redditActions = visibleActions.filter(action => action.platform === 'reddit')
  const running = fraction < 1
  const attemptedRequests = currentRound * 8

  const status = {
    simulation_id: IDS.simulationId,
    runner_status: running ? 'running' : 'completed',
    total_rounds: TOTAL_ROUNDS,
    twitter_current_round: currentRound,
    reddit_current_round: currentRound,
    twitter_simulated_hours: currentRound * 0.5,
    reddit_simulated_hours: currentRound * 0.5,
    twitter_actions_count: twitterActions.length,
    reddit_actions_count: redditActions.length,
    total_actions_count: visibleActions.length,
    twitter_running: running,
    reddit_running: running,
    twitter_completed: !running,
    reddit_completed: !running,
    error: null,
    started_at: ts(0),
    updated_at: new Date().toISOString(),
    llm_attempted_requests: attemptedRequests,
    llm_successful_requests: attemptedRequests,
    llm_minimum_success_rate: 0.9
  }

  return { fraction, currentRound, visibleActions, status }
}

export const routes = [
  {
    method: 'post',
    pattern: /^\/api\/simulation\/start$/,
    latency: 'read',
    handler: () => {
      // Deep link straight into the run page (no Home upload this session):
      // show the finished run with the full action feed instead of replaying.
      if (!jobStarted('ontology')) ensureCompletedJob('run', RUN_SECONDS)
      startJob('run')
      const { status } = deriveRun()
      return {
        force_restarted: false,
        process_pid: 47113,
        run_mode: 'standard',
        run_mode_label: 'Standard (LLM agents)',
        platform: 'both',
        ...status
      }
    }
  },
  {
    method: 'get',
    pattern: /^\/api\/simulation\/(?<simulationId>[^/?]+)\/run-status$/,
    latency: 'read',
    handler: () => {
      ensureCompletedJob('run', RUN_SECONDS)
      return deriveRun().status
    }
  },
  {
    method: 'get',
    pattern: /^\/api\/simulation\/(?<simulationId>[^/?]+)\/run-status\/detail$/,
    latency: 'read',
    handler: () => {
      ensureCompletedJob('run', RUN_SECONDS)
      const { status, visibleActions, currentRound } = deriveRun()
      return {
        ...status,
        all_actions: visibleActions,
        rounds_count: currentRound
      }
    }
  },
  {
    method: 'post',
    pattern: /^\/api\/simulation\/stop$/,
    latency: 'read',
    handler: () => ({})
  },
  {
    method: 'post',
    pattern: /^\/api\/report\/generate$/,
    latency: 'read',
    handler: () => {
      if (!jobStarted('ontology')) ensureCompletedJob('reportGen', REPORT_SECONDS)
      startJob('reportGen')
      return { report_id: IDS.reportId }
    }
  },
  {
    method: 'get',
    pattern: /^\/api\/report\/(?<reportId>[^/?]+)$/,
    latency: 'read',
    handler: () => report
  },
  {
    method: 'get',
    pattern: /^\/api\/report\/(?<reportId>[^/?]+)\/agent-log$/,
    latency: 'read',
    handler: ({ query }) => {
      ensureCompletedJob('reportGen', REPORT_SECONDS)
      const fraction = jobFraction('reportGen', REPORT_SECONDS)
      const visible = agentLog.filter(entry => entry.at <= fraction)
      const fromLine = Number(query.from_line) || 0
      const logs = visible.slice(fromLine).map(({ at, ...entry }) => entry)
      return { logs, from_line: fromLine }
    }
  },
  {
    method: 'get',
    pattern: /^\/api\/report\/(?<reportId>[^/?]+)\/console-log$/,
    latency: 'read',
    handler: ({ query }) => {
      ensureCompletedJob('reportGen', REPORT_SECONDS)
      const fraction = jobFraction('reportGen', REPORT_SECONDS)
      const visible = consoleLog.filter(entry => entry.at <= fraction).map(entry => entry.line)
      const fromLine = Number(query.from_line) || 0
      const logs = visible.slice(fromLine)
      return { logs, from_line: fromLine }
    }
  },
  {
    method: 'post',
    pattern: /^\/api\/report\/chat$/,
    latency: 'ai',
    handler: () => ({ response: REPORT_CHAT_RESPONSE })
  },
  {
    method: 'post',
    pattern: /^\/api\/simulation\/interview\/batch$/,
    latency: 'ai',
    handler: ({ body }) => {
      const interviews = Array.isArray(body?.interviews) ? body.interviews : []
      const results = {}
      interviews.forEach(interview => {
        results[`reddit_${interview.agent_id}`] = { response: interviewReply(interview.agent_id) }
      })
      return { result: { results } }
    }
  }
]
