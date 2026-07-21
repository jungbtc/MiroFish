import { createDemoAdapter as buildDemoAdapter } from './adapter.js'
import routes from './routes.js'
import * as demoClock from './clock.js'

let badgeInstalled = false

// Appends a small fixed-position "you are in a demo" marker to the page.
// Guarded so it's a no-op outside a DOM (SSR/tests) and only ever injects
// once even if createDemoAdapter() is called more than once.
export function installDemoBadge() {
  if (typeof document === 'undefined') return
  if (badgeInstalled) return
  badgeInstalled = true

  const badge = document.createElement('div')
  badge.textContent = 'DEMO — simulated data, no live AI'
  Object.assign(badge.style, {
    position: 'fixed',
    left: '12px',
    bottom: '12px',
    padding: '6px 14px',
    borderRadius: '999px',
    background: 'rgba(20, 20, 24, 0.82)',
    color: 'rgba(255, 255, 255, 0.92)',
    fontSize: '12px',
    fontFamily: 'system-ui, -apple-system, sans-serif',
    letterSpacing: '0.02em',
    pointerEvents: 'none',
    zIndex: 2147483647
  })
  document.body.appendChild(badge)
}

export function createDemoAdapter() {
  installDemoBadge()
  // Debug handle so a demo presenter/tester can inspect or reset scripted
  // job progress from the console (e.g. `__forefoldDemo.resetAll()`)
  // without knowing the sessionStorage key.
  if (typeof window !== 'undefined') {
    window.__forefoldDemo = demoClock
  }
  return buildDemoAdapter(routes)
}
