import { createRouter, createWebHistory } from 'vue-router'
import { isDevReplayEnabled } from '../dev/devReplay'

const Home = () => import('../views/Home.vue')
const DevReplayView = () => import('../views/DevReplayView.vue')
const Process = () => import('../views/MainView.vue')
const SimulationView = () => import('../views/SimulationView.vue')
const SimulationRunView = () => import('../views/SimulationRunView.vue')
const ReportView = () => import('../views/ReportView.vue')
const InteractionView = () => import('../views/InteractionView.vue')
const DecisionWorkspaceView = () => import('../views/DecisionWorkspaceView.vue')

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  ...(isDevReplayEnabled() ? [{
    path: '/dev/replay',
    name: 'DevReplay',
    component: DevReplayView
  }] : []),
  {
    path: '/process/:projectId',
    name: 'Process',
    component: Process,
    props: true
  },
  {
    path: '/simulation/:simulationId',
    name: 'Simulation',
    component: SimulationView,
    props: true
  },
  {
    path: '/simulation/:simulationId/start',
    name: 'SimulationRun',
    component: SimulationRunView,
    props: true
  },
  {
    path: '/report/:reportId',
    name: 'Report',
    component: ReportView,
    props: true
  },
  {
    path: '/interaction/:reportId',
    name: 'Interaction',
    component: InteractionView,
    props: true
  },
  {
    path: '/report/:reportId/refinement',
    name: 'ReportRefinement',
    component: DecisionWorkspaceView,
    props: true
  },
  {
    path: '/decision/:runId',
    name: 'DecisionWorkspace',
    component: DecisionWorkspaceView,
    props: true
  },
  {
    path: '/decision',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
