import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const projectRoot = resolve(frontendRoot, '..')
const readFrontend = path => readFileSync(resolve(frontendRoot, path), 'utf8')
const readProject = path => readFileSync(resolve(projectRoot, path), 'utf8')

test('WHAT IF WHAT IF brand copy and supplied icon are installed', () => {
  const messages = JSON.parse(readProject('locales/en.json'))
  const index = readFrontend('index.html')
  const home = readFrontend('src/views/Home.vue')
  const lockup = readFrontend('src/components/BrandLockup.vue')
  const readme = readProject('README.md')

  assert.equal(existsSync(resolve(frontendRoot, 'public/brand/forefold-icon.png')), true)
  assert.equal(messages.home.tagline, 'One report. Many possible futures.')
  assert.equal(messages.home.heroTitle1, 'Upload Evidence,')
  assert.equal(messages.home.heroTitle2, 'Rehearse What Happens Next')
  assert.equal(
    messages.home.heroDesc,
    'Turn public research and internal knowledge into branching simulations. Test decisions across millions of agents before committing in the real world.'
  )
  assert.match(index, /<html lang="en">/)
  assert.match(index, /WHAT IF WHAT IF — One report\. Many possible futures\./)
  assert.match(index, /\/brand\/forefold-icon\.png/)
  assert.doesNotMatch(index, /MiroFish|lang="zh"|预测万物/)
  assert.match(home, /<BrandLockup class="nav-brand"/)
  assert.match(home, /@pointermove="handleHeroPointerMove"/)
  assert.match(home, /class="visual-links"/)
  assert.doesNotMatch(home, /visual-core|\/brand\/forefold-icon\.png/)
  assert.match(lockup, /BRAND_NAME/)
  assert.match(lockup, /BRAND_ICON_PATH/)
  assert.match(readme, /# WHAT IF WHAT IF/)
  assert.doesNotMatch(readme, /MiroFish/i)
})

test('every route exposes upstream credit, license, warranty, and modified source', () => {
  const app = readFrontend('src/App.vue')
  const notice = readFrontend('src/components/OpenSourceNotice.vue')
  const brand = readFrontend('src/constants/brand.js')
  const repositoryNotice = readProject('NOTICE')

  assert.match(app, /<OpenSourceNotice/)
  assert.match(notice, /modified version of/)
  assert.match(notice, /WHAT IF WHAT IF/)
  assert.match(notice, /MiroFish/)
  assert.match(notice, /View corresponding source/)
  assert.match(notice, /GNU AGPL v3/)
  assert.match(notice, /No warranty\./)
  assert.match(brand, /VITE_SOURCE_CODE_URL/)
  assert.match(brand, /github\.com\/666ghj\/MiroFish/)
  assert.match(brand, /github\.com\/jungbtc\/MiroFish/)
  assert.match(repositoryNotice, /Modifications and rebranding for WHAT IF WHAT IF began in July 2026/)
  assert.doesNotMatch(repositoryNotice, /FOREFOLD/)
})

test('active headers use the shared WHAT IF WHAT IF lockup', () => {
  const workflowHeader = readFrontend('src/components/WorkflowHeader.vue')
  const decisionWorkspace = readFrontend('src/views/DecisionWorkspaceView.vue')

  assert.match(workflowHeader, /<BrandLockup class="workflow-brand"/)
  assert.match(decisionWorkspace, /<BrandLockup class="brand-button"/)
  assert.doesNotMatch(workflowHeader, /Go to MiroFish home|>MiroFish</)
  assert.doesNotMatch(decisionWorkspace, />MIROFISH</)
})
