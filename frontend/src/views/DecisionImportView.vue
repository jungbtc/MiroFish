<template>
  <div class="decision-import-page">
    <nav class="topbar">
      <router-link :to="{ name: 'Home' }" class="back-link">
        <span>←</span> {{ $t('decisionImport.backToCore') }}
      </router-link>
      <div class="topbar-right">
        <span class="optional-badge">{{ $t('decisionImport.optionalBadge') }}</span>
        <LanguageSwitcher />
      </div>
    </nav>

    <main>
      <header class="intro">
        <p class="eyebrow">{{ $t('decisionImport.eyebrow') }}</p>
        <h1>{{ $t('decisionImport.title') }}</h1>
        <p class="intro-copy">{{ $t('decisionImport.description') }}</p>
        <div class="core-boundary">
          <span class="boundary-mark">◇</span>
          <p><strong>{{ $t('decisionImport.corePreservedTitle') }}</strong> {{ $t('decisionImport.corePreservedDesc') }}</p>
        </div>
      </header>

      <section class="import-layout">
        <aside class="extension-map">
          <p class="section-kicker">{{ $t('decisionImport.relationshipKicker') }}</p>
          <h2>{{ $t('decisionImport.relationshipTitle') }}</h2>
          <ol>
            <li>
              <span>01</span>
              <div>
                <strong>{{ $t('decisionImport.coreStepTitle') }}</strong>
                <p>{{ $t('decisionImport.coreStepDesc') }}</p>
              </div>
            </li>
            <li>
              <span>＋</span>
              <div>
                <strong>{{ $t('decisionImport.addonStepTitle') }}</strong>
                <p>{{ $t('decisionImport.addonStepDesc') }}</p>
              </div>
            </li>
            <li>
              <span>03</span>
              <div>
                <strong>{{ $t('decisionImport.outputStepTitle') }}</strong>
                <p>{{ $t('decisionImport.outputStepDesc') }}</p>
              </div>
            </li>
          </ol>
          <div class="zero-token-note">
            <span class="token-dot"></span>
            <div>
              <strong>{{ $t('decisionImport.zeroTokenTitle') }}</strong>
              <p>{{ $t('decisionImport.zeroTokenDesc') }}</p>
            </div>
          </div>
        </aside>

        <form class="import-form" @submit.prevent="submitImport">
          <div class="form-heading">
            <div>
              <p class="section-kicker">{{ $t('decisionImport.formKicker') }}</p>
              <h2>{{ $t('decisionImport.formTitle') }}</h2>
            </div>
            <span class="format-label">PDF · MD · JSON</span>
          </div>

          <div
            class="drop-zone"
            :class="{ active: isDragOver, populated: files.length }"
            @click="openFilePicker"
            @dragover.prevent="isDragOver = true"
            @dragleave.prevent="isDragOver = false"
            @drop.prevent="handleDrop"
          >
            <input
              ref="fileInput"
              type="file"
              multiple
              accept=".pdf,.md,.markdown,.json,application/pdf,application/json,text/markdown"
              :disabled="loading"
              @change="handleFileSelect"
            />
            <div v-if="!files.length" class="drop-placeholder">
              <span class="upload-arrow">↑</span>
              <strong>{{ $t('decisionImport.dropTitle') }}</strong>
              <p>{{ $t('decisionImport.dropHint') }}</p>
            </div>
            <ul v-else class="file-list">
              <li v-for="(file, index) in files" :key="`${file.name}-${file.size}-${index}`">
                <div>
                  <strong>{{ file.name }}</strong>
                  <span>{{ formatBytes(file.size) }}</span>
                </div>
                <button type="button" :aria-label="$t('decisionImport.removeFile')" @click.stop="removeFile(index)">×</button>
              </li>
            </ul>
          </div>

          <label class="field">
            <span>{{ $t('decisionImport.projectName') }}</span>
            <input
              v-model="projectName"
              type="text"
              maxlength="300"
              :placeholder="$t('decisionImport.projectNamePlaceholder')"
              :disabled="loading"
            />
          </label>

          <label class="field">
            <span>{{ $t('decisionImport.question') }} <b>{{ $t('decisionImport.required') }}</b></span>
            <textarea
              v-model="decisionQuestion"
              rows="5"
              maxlength="12000"
              :placeholder="$t('decisionImport.questionPlaceholder')"
              :disabled="loading"
            ></textarea>
          </label>

          <div class="privacy-note">
            <span>◆</span>
            <p><strong>{{ $t('decisionImport.privacyTitle') }}</strong> {{ $t('decisionImport.privacyDesc') }}</p>
          </div>

          <p v-if="statusMessage" class="status success">✓ {{ statusMessage }}</p>
          <p v-if="error" class="status error">! {{ error }}</p>

          <button class="submit-button" type="submit" :disabled="!canSubmit || loading">
            <span>{{ loading ? $t('decisionImport.importing') : $t('decisionImport.submit') }}</span>
            <span>→</span>
          </button>
        </form>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import LanguageSwitcher from '../components/LanguageSwitcher.vue'
import { importDeepResearch } from '../api/v2'

const router = useRouter()
const { t } = useI18n()
const files = ref([])
const projectName = ref('')
const decisionQuestion = ref('')
const loading = ref(false)
const error = ref('')
const statusMessage = ref('')
const isDragOver = ref(false)
const fileInput = ref(null)

const canSubmit = computed(() => files.value.length > 0 && decisionQuestion.value.trim().length > 0)

const openFilePicker = () => {
  if (!loading.value) fileInput.value?.click()
}

const addFiles = (incoming) => {
  error.value = ''
  statusMessage.value = ''
  const valid = incoming.filter(file => {
    const extension = file.name.split('.').pop()?.toLowerCase()
    return ['pdf', 'md', 'markdown', 'json'].includes(extension)
  })
  if (valid.length !== incoming.length) {
    error.value = t('decisionImport.unsupportedFiles')
  }
  const identities = new Set(files.value.map(file => `${file.name}:${file.size}:${file.lastModified}`))
  for (const file of valid) {
    const identity = `${file.name}:${file.size}:${file.lastModified}`
    if (!identities.has(identity)) {
      files.value.push(file)
      identities.add(identity)
    }
  }
}

const handleFileSelect = event => {
  addFiles(Array.from(event.target.files || []))
  event.target.value = ''
}

const handleDrop = event => {
  isDragOver.value = false
  if (!loading.value) addFiles(Array.from(event.dataTransfer.files || []))
}

const removeFile = index => files.value.splice(index, 1)

const formatBytes = bytes => {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const submitImport = async () => {
  if (!canSubmit.value || loading.value) return
  loading.value = true
  error.value = ''
  statusMessage.value = ''

  try {
    const payload = new FormData()
    files.value.forEach(file => payload.append('files', file))
    payload.append('question', decisionQuestion.value.trim())
    payload.append('project_name', projectName.value.trim() || 'Deep Research Decision')

    const response = await importDeepResearch(payload)
    const run = response?.data
    if (!response?.success || !run?.run_id) {
      throw new Error(response?.error || t('decisionImport.invalidRun'))
    }
    statusMessage.value = t('decisionImport.imported')
    await router.push({ name: 'DecisionWorkspace', params: { runId: run.run_id } })
  } catch (importError) {
    error.value = importError.message || t('decisionImport.importFailed')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.decision-import-page {
  min-height: 100vh;
  color: #171713;
  background: #f4f3ef;
  font-family: 'Space Grotesk', 'Noto Sans SC', system-ui, sans-serif;
}

.topbar {
  min-height: 58px;
  padding: 0 34px;
  color: #fff;
  background: #11110f;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.back-link {
  color: inherit;
  text-decoration: none;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.optional-badge {
  padding: 6px 9px;
  border: 1px solid #5e5e58;
  color: #c9c8c0;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

main {
  width: min(1180px, calc(100% - 48px));
  margin: 0 auto;
  padding: 68px 0 90px;
}

.intro {
  max-width: 900px;
  margin-bottom: 44px;
}

.eyebrow,
.section-kicker {
  margin: 0 0 12px;
  color: #e4481d;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.intro h1 {
  max-width: 800px;
  margin: 0;
  font-size: clamp(38px, 6vw, 72px);
  font-weight: 520;
  line-height: 1.04;
  letter-spacing: -0.045em;
}

.intro-copy {
  max-width: 760px;
  margin: 22px 0;
  color: #5f5e58;
  font-size: 17px;
  line-height: 1.65;
}

.core-boundary {
  max-width: 840px;
  padding: 14px 17px;
  border: 1px solid #cfcec6;
  background: #faf9f5;
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.core-boundary p,
.privacy-note p {
  margin: 0;
  color: #53524d;
  font-size: 13px;
  line-height: 1.55;
}

.boundary-mark {
  color: #e4481d;
}

.import-layout {
  display: grid;
  grid-template-columns: minmax(280px, 0.78fr) minmax(440px, 1.22fr);
  gap: 24px;
  align-items: start;
}

.extension-map,
.import-form {
  border: 1px solid #cfcec6;
  background: #fff;
}

.extension-map {
  padding: 28px;
}

.extension-map h2,
.import-form h2 {
  margin: 0;
  font-size: 23px;
  font-weight: 550;
}

.extension-map ol {
  margin: 28px 0;
  padding: 0;
  list-style: none;
}

.extension-map li {
  padding: 18px 0;
  border-top: 1px solid #e5e4de;
  display: grid;
  grid-template-columns: 34px 1fr;
  gap: 12px;
}

.extension-map li > span {
  color: #9b9a92;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
}

.extension-map li strong {
  font-size: 14px;
}

.extension-map li p,
.zero-token-note p {
  margin: 5px 0 0;
  color: #6c6a64;
  font-size: 12px;
  line-height: 1.55;
}

.zero-token-note {
  padding: 15px;
  background: #edf7f1;
  display: flex;
  gap: 11px;
}

.token-dot {
  width: 8px;
  height: 8px;
  margin-top: 5px;
  border-radius: 50%;
  background: #238b61;
  box-shadow: 0 0 0 4px rgba(35, 139, 97, 0.12);
}

.import-form {
  padding: 30px;
}

.form-heading {
  margin-bottom: 24px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.format-label {
  color: #85847d;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
}

.drop-zone {
  min-height: 180px;
  margin-bottom: 22px;
  border: 1px dashed #aaa9a0;
  background: #faf9f5;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.2s, background 0.2s;
}

.drop-zone.active {
  border-color: #e4481d;
  background: #fff4ee;
}

.drop-zone.populated {
  align-items: stretch;
}

.drop-zone input {
  display: none;
}

.drop-placeholder {
  padding: 28px;
  text-align: center;
}

.upload-arrow {
  width: 40px;
  height: 40px;
  margin: 0 auto 13px;
  border: 1px solid #cfcec6;
  color: #e4481d;
  display: grid;
  place-items: center;
}

.drop-placeholder strong {
  display: block;
}

.drop-placeholder p {
  margin: 7px 0 0;
  color: #85847d;
  font-size: 12px;
}

.file-list {
  width: 100%;
  max-height: 240px;
  margin: 0;
  padding: 13px;
  list-style: none;
  overflow-y: auto;
}

.file-list li {
  padding: 11px 12px;
  border-bottom: 1px solid #e5e4de;
  background: #fff;
  display: flex;
  justify-content: space-between;
  gap: 15px;
}

.file-list strong,
.file-list span {
  display: block;
  word-break: break-word;
}

.file-list strong {
  font-size: 12px;
}

.file-list span {
  margin-top: 3px;
  color: #8a8981;
  font-size: 10px;
}

.file-list button {
  border: 0;
  background: transparent;
  color: #77766f;
  cursor: pointer;
  font-size: 18px;
}

.field {
  margin-top: 18px;
  display: block;
}

.field > span {
  margin-bottom: 8px;
  color: #5d5c56;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  display: flex;
  justify-content: space-between;
}

.field b {
  color: #e4481d;
  font-size: 9px;
  text-transform: uppercase;
}

.field input,
.field textarea {
  box-sizing: border-box;
  width: 100%;
  padding: 13px 14px;
  border: 1px solid #cfcec6;
  border-radius: 0;
  color: #191915;
  background: #faf9f5;
  font: inherit;
  outline: none;
}

.field textarea {
  resize: vertical;
  line-height: 1.55;
}

.field input:focus,
.field textarea:focus {
  border-color: #171713;
}

.privacy-note {
  margin: 20px 0;
  padding: 13px 14px;
  border-left: 3px solid #e4481d;
  background: #f4f3ef;
  display: flex;
  gap: 10px;
}

.privacy-note > span {
  color: #e4481d;
  font-size: 10px;
}

.status {
  padding: 11px 13px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
}

.status.success {
  color: #176548;
  background: #e7f4ed;
}

.status.error {
  color: #8a2d23;
  background: #fae9e6;
}

.submit-button {
  width: 100%;
  padding: 17px 18px;
  border: 0;
  color: #fff;
  background: #171713;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  display: flex;
  justify-content: space-between;
  cursor: pointer;
}

.submit-button:hover:not(:disabled) {
  background: #e4481d;
}

.submit-button:disabled {
  color: #96958e;
  background: #ddddd7;
  cursor: not-allowed;
}

@media (max-width: 820px) {
  .optional-badge {
    display: none;
  }

  main {
    width: min(100% - 28px, 680px);
    padding-top: 42px;
  }

  .import-layout {
    grid-template-columns: 1fr;
  }

  .topbar {
    padding: 0 16px;
  }
}
</style>
