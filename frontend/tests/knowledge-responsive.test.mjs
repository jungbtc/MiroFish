import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const readFrontend = path => readFileSync(resolve(frontendRoot, path), 'utf8')

test('Knowledge ontology and build cards reflow instead of clipping in narrow panels', () => {
  const step = readFrontend('src/components/Step1GraphBuild.vue')

  assert.match(step, /class="ontology-tags-scroll"/)
  assert.match(step, /\.ontology-tags-scroll\s*\{[\s\S]*max-height:[\s\S]*overflow-y:\s*auto/)
  assert.match(step, /container-type:\s*inline-size/)
  assert.match(step, /@container\s*\(max-width:\s*640px\)/)
  assert.match(step, /\.step-card\s*\{[\s\S]*flex:\s*0\s+0\s+auto/)
  assert.match(step, /grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/)
  assert.match(step, /\.stat-card:last-child\s*\{[\s\S]*grid-column:\s*1\s*\/\s*-1/)
  assert.match(step, /white-space:\s*normal/)
})

test('Knowledge split view stacks and remains vertically scrollable on narrow screens', () => {
  const view = readFrontend('src/views/MainView.vue')

  assert.match(view, /@media\s*\(max-width:\s*900px\)/)
  assert.match(view, /\.content-area\s*\{[\s\S]*flex-direction:\s*column[\s\S]*overflow-y:\s*auto/)
  assert.match(view, /\.panel-wrapper\s*\{[\s\S]*width:\s*100%\s*!important/)
})

test('Knowledge graph responds to panel resizes and gives dense node sets more space', () => {
  const graph = readFrontend('src/components/GraphPanel.vue')

  assert.match(graph, /densityScale/)
  assert.match(graph, /showEdgeLabels\s*=\s*ref\(false\)/)
  assert.match(graph, /forceManyBody\(\)\.strength\(-480 \* densityScale\)/)
  assert.match(graph, /forceCollide\(42 \+ densityScale \* 10\)/)
  assert.match(graph, /simulation\.on\(['"]end['"]/)
  assert.match(graph, /fitTimer\s*=\s*setTimeout/)
  assert.match(graph, /d3\.quantileSorted\(sortedX, lowerQuantile\)/)
  assert.match(graph, /positionedNodes\.length > 24 \? 0\.04 : 0/)
  assert.match(graph, /zoomBehavior\.transform/)
  assert.match(graph, /event\.transform\.k >= 0\.58/)
  assert.match(graph, /new ResizeObserver\(entries =>/)
  assert.match(graph, /Math\.abs\(bounds\.width - lastGraphWidth\) < 1/)
  assert.match(graph, /resizeObserver\.observe\(graphContainer\.value\)/)
  assert.match(graph, /resizeObserver\?\.disconnect\(\)/)
})

test('workflow logs use a readable dark surface and high-contrast text', () => {
  const design = readFrontend('src/styles/design-system.css')

  assert.match(design, /\.system-logs,[\s\S]*\.console-logs\s*\{[\s\S]*background:\s*#111216/)
  assert.match(design, /\.log-msg\s*\{\s*color:\s*#ececf1/)
})
