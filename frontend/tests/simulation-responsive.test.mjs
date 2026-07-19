import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const simulation = readFileSync(resolve(frontendRoot, 'src/components/Step3Simulation.vue'), 'utf8')

test('simulation platform summaries use readable non-compressing metric cards', () => {
  assert.match(simulation, /container-type:\s*inline-size/)
  assert.match(simulation, /\.status-group\s*\{[\s\S]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/)
  assert.match(simulation, /\.platform-status\s*\{[\s\S]*min-height:\s*64px[\s\S]*min-width:\s*0/)
  assert.match(simulation, /\.platform-stats\s*\{[\s\S]*grid-template-columns:\s*repeat\(3,\s*minmax\(0,\s*1fr\)\)/)
  assert.match(simulation, /\.stat-label\s*\{[\s\S]*font-size:\s*9px/)
})

test('saved report action moves below platform summaries when the workbench narrows', () => {
  assert.match(simulation, /@container\s*\(max-width:\s*860px\)/)
  assert.match(simulation, /@container\s*\(max-width:\s*860px\)[\s\S]*\.control-bar\s*\{[\s\S]*grid-template-columns:\s*1fr/)
  assert.match(simulation, /@container\s*\(max-width:\s*860px\)[\s\S]*\.action-controls\s*\{[\s\S]*width:\s*100%/)
  assert.match(simulation, /@container\s*\(max-width:\s*520px\)[\s\S]*\.status-group\s*\{[\s\S]*grid-template-columns:\s*1fr/)
})
