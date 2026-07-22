import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const report = readFileSync(resolve(frontendRoot, 'src/components/Step4Report.vue'), 'utf8')

test('prediction report sections use consistently inset white surfaces', () => {
  assert.match(report, /\.sections-list\s*\{[\s\S]*gap:\s*20px/)
  assert.match(report, /\.report-section-item\s*\{[\s\S]*padding:\s*18px\s+20px\s+20px[\s\S]*background:\s*#FFFFFF[\s\S]*box-sizing:\s*border-box/)
  assert.match(report, /\.section-header-row\s*\{[\s\S]*padding:\s*0;[\s\S]*margin:\s*0;/)
})
