import { createDemoAdapter as buildDemoAdapter } from './adapter.js'
import routes from './routes.js'
import * as demoClock from './clock.js'

export function createDemoAdapter() {
  // Debug handle so a demo presenter/tester can inspect or reset scripted
  // job progress from the console (e.g. `__forefoldDemo.resetAll()`)
  // without knowing the sessionStorage key.
  if (typeof window !== 'undefined') {
    window.__forefoldDemo = demoClock
  }
  return buildDemoAdapter(routes)
}
