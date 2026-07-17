<template>
  <div class="decision-shell">
    <header class="decision-header">
      <button class="brand-button" type="button" @click="router.push('/')">
        <span class="brand-mark">M</span>
        <span>MIROFISH</span>
        <span class="brand-suffix">RESEARCH &amp; DECISION REFINEMENT</span>
      </button>

      <div class="header-actions">
        <div class="run-reference">RUN / {{ shortRunId }}</div>
        <div class="token-badge" :class="{ zero: researchReady }">
          <span class="token-dot"></span>
          <span>{{ researchStatusLabel }}</span>
        </div>
        <button class="icon-button" type="button" :disabled="loading" @click="loadRun" title="Refresh decision state">↻</button>
      </div>
    </header>

    <main class="decision-main">
      <div v-if="loading && !runState" class="state-card loading-state">
        <div class="loading-ring"></div>
        <h2>Loading decision state</h2>
        <p>Reconstructing evidence, branches, and the audit trail.</p>
      </div>

      <div v-else-if="loadError && !runState" class="state-card error-state">
        <span class="state-kicker">DECISION STATE UNAVAILABLE</span>
        <h2>We could not load this run.</h2>
        <p>{{ loadError }}</p>
        <button class="primary-button" type="button" @click="loadRun">Try again</button>
      </div>

      <template v-else-if="runState">
        <section class="decision-hero">
          <div class="hero-copy">
            <div class="ingestion-status" :class="{ researching: !researchReady }">
              <span class="status-check">✓</span>
              {{ researchStatusMessage }}
            </div>
            <p class="eyebrow">{{ runState.project_name || 'Decision case' }}</p>
            <h1>{{ runState.question || 'Decision intelligence workspace' }}</h1>
            <p class="hero-description">
              Public evidence is preserved below. MiroFish is now isolating the private facts most likely to change the recommendation.
            </p>
          </div>
          <div class="hero-metrics">
            <div class="hero-metric">
              <span class="metric-value">{{ claims.length }}</span>
              <span class="metric-label">evidence claims</span>
            </div>
            <div class="hero-metric">
              <span class="metric-value">{{ hypotheses.length }}</span>
              <span class="metric-label">decision paths</span>
            </div>
            <div class="hero-metric accent">
              <span class="metric-value">{{ openQuestions.length }}</span>
              <span class="metric-label">facts still needed</span>
            </div>
          </div>
        </section>

        <div v-if="loadError" class="inline-alert error-alert">
          <span>Refresh failed: {{ loadError }}</span>
          <button type="button" @click="loadError = ''">Dismiss</button>
        </div>
        <div v-if="actionMessage" class="inline-alert success-alert">
          <span>{{ actionMessage }}</span>
          <button type="button" @click="actionMessage = ''">Dismiss</button>
        </div>

        <section v-if="!researchReady" class="state-card research-state">
          <div v-if="researchActive" class="loading-ring"></div>
          <span class="state-kicker">PUBLIC DEEP RESEARCH</span>
          <h2>{{ researchJob.message || 'Preparing cited external research.' }}</h2>
          <p>
            The provider job ID and progress are saved durably. Only the initial simulation report and public context are used;
            confidential answers never enter web search.
          </p>
          <div class="research-progress"><span :style="{ width: `${researchProgress}%` }"></span></div>
          <div class="research-actions">
            <button v-if="researchFailed" class="primary-button" type="button" @click="retryResearch">Retry research</button>
            <button v-if="researchActive" class="secondary-button" type="button" @click="cancelResearch">Cancel safely</button>
            <button class="secondary-button" type="button" @click="loadRun">Refresh status</button>
          </div>
        </section>

        <template v-else>
        <section class="status-grid">
          <article class="status-card" :class="stopEvaluation.should_stop ? 'stop' : 'continue'">
            <div class="card-kicker">CONTINUE-OR-STOP EVALUATION</div>
            <div class="stop-heading-row">
              <div>
                <div class="stop-verdict">{{ stopEvaluation.should_stop ? 'Stop asking' : 'Keep learning' }}</div>
                <p>{{ stopEvaluation.reason || 'The decision engine has not recorded a stop reason yet.' }}</p>
              </div>
              <div class="verdict-icon">{{ stopEvaluation.should_stop ? '■' : '→' }}</div>
            </div>
            <div class="stop-metrics">
              <span>Remaining information value <strong>{{ formatScore(stopEvaluation.remaining_information_value) }}</strong></span>
              <span>Leading margin <strong>{{ formatScore(stopEvaluation.leading_margin) }}</strong></span>
            </div>
            <button class="text-button" type="button" :disabled="evaluatingStop" @click="reevaluateStop">
              {{ evaluatingStop ? 'Evaluating…' : 'Re-evaluate stop condition' }}
            </button>
          </article>

          <article class="status-card recommendation-card">
            <div class="card-kicker">CURRENT RECOMMENDATION</div>
            <h2>{{ plainText(report.recommendation || leadingHypothesis?.label || 'Recommendation pending') }}</h2>
            <p v-if="leadingHypothesis">Leading path: {{ leadingHypothesis.description || leadingHypothesis.label }}</p>
            <p v-else>The recommendation will appear after competing paths have enough support.</p>
            <div class="recommendation-footer">
              <span class="report-status">MEMO / {{ String(report.status || 'draft').toUpperCase() }}</span>
              <span v-if="report.stop_reason">{{ report.stop_reason }}</span>
            </div>
          </article>
        </section>

        <div class="workspace-grid">
          <div class="workspace-primary">
            <section class="panel branch-panel">
              <div class="panel-heading">
                <div>
                  <span class="panel-index">01</span>
                  <h2>Competing decision paths</h2>
                  <p>Each internal answer changes support visibly; paths can strengthen, weaken, or be pruned.</p>
                </div>
                <div class="branch-legend">
                  <span><i class="legend-dot strengthened"></i>Strengthened</span>
                  <span><i class="legend-dot weakened"></i>Weakened</span>
                  <span><i class="legend-dot pruned"></i>Pruned</span>
                </div>
              </div>

              <div v-if="hypotheses.length" class="branch-map">
                <div class="decision-root">
                  <span>DECISION</span>
                  <strong>{{ truncate(runState.question, 92) }}</strong>
                </div>
                <div class="branch-connector"></div>
                <div class="branch-list">
                  <article
                    v-for="hypothesis in hypotheses"
                    :key="hypothesis.hypothesis_id"
                    class="branch-card"
                    :class="branchTone(hypothesis)"
                  >
                    <div class="branch-card-top">
                      <div>
                        <span class="branch-state">{{ branchLabel(hypothesis) }}</span>
                        <h3>{{ hypothesis.label }}</h3>
                      </div>
                      <div class="branch-score">{{ formatScore(hypothesis.support_score) }}</div>
                    </div>
                    <p>{{ hypothesis.description }}</p>
                    <div class="score-track"><span :style="{ width: `${scorePercent(hypothesis.support_score)}%` }"></span></div>
                    <div class="branch-delta-row">
                      <span>{{ formatDelta(hypothesisDelta(hypothesis)) }}</span>
                      <span>{{ String(hypothesis.status || 'active').toUpperCase() }}</span>
                    </div>
                    <div v-if="hypothesis.prune_reason" class="prune-reason">Pruned because: {{ hypothesis.prune_reason }}</div>
                  </article>
                </div>
              </div>
              <div v-else class="empty-panel">No competing paths have been extracted yet.</div>
            </section>

            <section class="panel evidence-panel">
              <div class="panel-heading">
                <div>
                  <span class="panel-index">02</span>
                  <h2>Evidence and provenance</h2>
                  <p>Sourced facts remain distinct from generated interpretations and assumptions.</p>
                </div>
                <div class="evidence-counts">
                  <span>{{ claims.length }} claims</span>
                  <span>{{ assumptions.length }} assumptions</span>
                  <span>{{ contradictions.length }} contradictions</span>
                </div>
              </div>

              <div class="evidence-layout">
                <div class="evidence-column">
                  <h3 class="column-title">Claims</h3>
                  <article v-for="claim in claims" :key="claim.claim_id" class="evidence-item">
                    <div class="evidence-item-meta">
                      <span class="evidence-kind" :class="claimTone(claim)">
                        {{ claimKind(claim) }}
                      </span>
                      <span class="evidence-id">{{ claim.claim_id }}</span>
                    </div>
                    <p>{{ claim.text }}</p>
                    <div v-if="claim.citations?.length" class="citation-list">
                      <button
                        v-for="(citation, index) in claim.citations"
                        :key="citationKey(citation, index)"
                        type="button"
                        class="citation-chip"
                        @click="openCitation(citation, claim)"
                      >
                        ↗ {{ citation.label || citation.source_id || `Source ${index + 1}` }}
                      </button>
                    </div>
                    <span v-else class="no-source">No external citation · generated interpretation</span>
                  </article>
                  <div v-if="!claims.length" class="empty-panel compact">No claims available.</div>
                </div>

                <div class="evidence-column secondary">
                  <h3 class="column-title">Assumptions to test</h3>
                  <article v-for="assumption in assumptions" :key="assumption.assumption_id" class="assumption-item">
                    <div class="assumption-topline">
                      <span>{{ assumption.category || 'Decision assumption' }}</span>
                      <span :class="`assumption-status ${assumption.status || 'open'}`">{{ assumption.status || 'open' }}</span>
                    </div>
                    <p>{{ assumption.text }}</p>
                    <small v-if="assumption.rationale">{{ assumption.rationale }}</small>
                    <div v-if="assumption.citations?.length" class="citation-list">
                      <button
                        v-for="(citation, index) in assumption.citations"
                        :key="citationKey(citation, index)"
                        type="button"
                        class="citation-chip"
                        @click="openCitation(citation, assumption)"
                      >
                        ↗ {{ citation.label || citation.source_id || `Source ${index + 1}` }}
                      </button>
                    </div>
                  </article>
                  <div v-if="!assumptions.length" class="empty-panel compact">No explicit assumptions recorded.</div>

                  <h3 class="column-title contradiction-title">Contradictions</h3>
                  <article v-for="(contradiction, index) in contradictions" :key="contradiction.contradiction_id || index" class="contradiction-item">
                    <span>!</span>
                    <div>
                      <strong>{{ contradiction.title || contradiction.severity || 'Evidence conflict' }}</strong>
                      <p>{{ contradictionText(contradiction) }}</p>
                      <div v-if="contradiction.citations?.length" class="citation-list">
                        <button
                          v-for="(citation, citationIndex) in contradiction.citations"
                          :key="citationKey(citation, citationIndex)"
                          type="button"
                          class="citation-chip"
                          @click="openCitation(citation, contradiction)"
                        >
                          ↗ {{ citation.label || citation.source_id || `Source ${citationIndex + 1}` }}
                        </button>
                      </div>
                    </div>
                  </article>
                  <div v-if="!contradictions.length" class="empty-panel compact">No unresolved contradictions detected.</div>
                </div>
              </div>
            </section>

            <section class="panel impact-panel">
              <div class="panel-heading">
                <div>
                  <span class="panel-index">03</span>
                  <h2>How answers changed the decision</h2>
                  <p>A before-and-after trail for every material branch update.</p>
                </div>
              </div>
              <div v-if="decisionImpacts.length" class="impact-list">
                <article v-for="(impact, index) in decisionImpacts" :key="impact.impact_id || index" class="impact-item">
                  <div class="impact-index">{{ String(index + 1).padStart(2, '0') }}</div>
                  <div class="impact-content">
                    <h3>{{ impact.summary || impact.title || 'Decision state updated' }}</h3>
                    <p v-if="impact.answer_summary">Evidence received: {{ impact.answer_summary }}</p>
                    <div class="change-list">
                      <div v-for="(change, changeIndex) in impact.hypothesis_changes || []" :key="change.hypothesis_id || changeIndex" class="change-row">
                        <span>{{ hypothesisName(change.hypothesis_id) }}</span>
                        <strong :class="changeTone(change)">{{ changeLabel(change) }}</strong>
                      </div>
                    </div>
                  </div>
                </article>
              </div>
              <div v-else class="empty-panel">Answer a ranked internal question to see its decision impact here.</div>
            </section>
          </div>

          <aside class="question-panel panel">
            <div class="question-panel-header">
              <div>
                <span class="panel-index inverse">NEXT BEST INFORMATION</span>
                <h2>Internal questions</h2>
                <p>Ranked by expected ability to change the recommendation.</p>
              </div>
              <div class="queue-count">{{ openQuestions.length }} open</div>
            </div>

            <div class="question-queue">
              <button
                v-for="question in sortedQuestions"
                :key="question.question_id"
                type="button"
                class="queue-item"
                :class="{ active: selectedQuestion?.question_id === question.question_id, answered: question.status === 'answered' }"
                :disabled="stopEvaluation.should_stop && question.status !== 'answered'"
                @click="selectedQuestionId = question.question_id"
              >
                <span class="queue-rank">#{{ question.rank || '—' }}</span>
                <span class="queue-copy">{{ question.question }}</span>
                <span class="queue-score">{{ formatScore(question.information_value_score) }}</span>
              </button>
            </div>

            <div v-if="selectedQuestion" class="selected-question">
              <div class="question-meta">
                <span>{{ selectedQuestion.category || 'Internal evidence' }}</span>
                <span>{{ selectedQuestion.owner_hint || 'Owner not assigned' }}</span>
              </div>
              <h3>{{ selectedQuestion.question }}</h3>
              <p class="question-rationale">{{ selectedQuestion.rationale }}</p>

              <div class="value-score-heading">
                <span>Information Value Score</span>
                <strong>{{ formatScore(selectedQuestion.information_value_score) }}</strong>
              </div>
              <div class="value-components">
                <div v-for="component in valueComponentRows" :key="component.key">
                  <span>{{ component.label }}</span>
                  <strong>{{ formatScore(component.value) }}</strong>
                </div>
              </div>
              <p v-if="selectedQuestion.value_components?.formula" class="score-formula">
                Formula: {{ selectedQuestion.value_components.formula }}
              </p>

              <div class="expected-change">
                <span>WHAT THIS COULD CHANGE</span>
                <p>{{ selectedQuestion.expected_change || 'The affected recommendation path will be recalculated after an answer.' }}</p>
                <div class="affected-branches">
                  <span v-for="id in selectedQuestion.affected_hypothesis_ids || []" :key="id">{{ hypothesisName(id) }}</span>
                </div>
              </div>

              <form
                v-if="!stopEvaluation.should_stop && selectedQuestion.status === 'requested'"
                class="answer-form"
                @submit.prevent="submitAnswer"
              >
                <label>
                  Internal answer
                  <textarea
                    v-model="answerForm.answer"
                    rows="5"
                    placeholder="Enter the private fact, decision constraint, or verified internal answer…"
                    required
                  ></textarea>
                </label>
                <div class="answer-form-row">
                  <label>
                    Submitted by
                    <input v-model="answerForm.submitted_by" type="text" placeholder="Role or team" />
                  </label>
                  <label>
                    Confidence
                    <select v-model.number="answerForm.confidence">
                      <option :value="0.6">Medium</option>
                      <option :value="0.8">High</option>
                      <option :value="1">Verified</option>
                    </select>
                  </label>
                </div>
                <label class="privacy-check">
                  <input v-model="answerForm.confidential" type="checkbox" />
                  <span>Mark as confidential internal evidence</span>
                </label>
                <button class="answer-button" type="submit" :disabled="submittingAnswer || !answerForm.answer.trim()">
                  <span>{{ submittingAnswer ? 'Updating decision…' : 'Submit evidence and update branches' }}</span>
                  <span>→</span>
                </button>
                <p class="privacy-note">This answer stays in the MiroFish decision workflow and is not sent back into external research.</p>
              </form>

              <div v-else-if="selectedQuestion.status === 'answered'" class="answered-card">
                <span>✓ ANSWER RECORDED</span>
                <p>{{ visibleEvidenceAnswer(selectedQuestion.question_id) }}</p>
              </div>
              <div v-else-if="selectedQuestion.status === 'deferred' || stopEvaluation.should_stop" class="answered-card deferred-card">
                <span>■ QUESTION DEFERRED</span>
                <p>Question deferred because stop condition was met. Additional internal information is unlikely to materially change the recommendation.</p>
              </div>
              <div v-else class="answered-card deferred-card">
                <span>◇ WAITING IN RANKED QUEUE</span>
                <p>Answer the currently requested highest-value question first. This question will become available if it still matters afterward.</p>
              </div>
            </div>
            <div v-else class="empty-panel inverse-empty">No internal questions remain.</div>
          </aside>
        </div>

        <section class="deliverables-grid">
          <article class="panel memo-panel">
            <div class="panel-heading">
              <div>
                <span class="panel-index">04</span>
                <h2>Executive decision memo</h2>
                <p>Recommendation, evidence used, rejected alternatives, uncertainty, and stop reason.</p>
              </div>
              <button class="secondary-button" type="button" :disabled="!report.markdown" @click="downloadMemo">Export Markdown</button>
              <button
                v-if="report.status === 'final' && runState.core_lineage?.initial_report_id"
                class="primary-button"
                type="button"
                @click="router.push({ name: 'Interaction', params: { reportId: runState.core_lineage.initial_report_id } })"
              >
                Optional interaction after final report
              </button>
            </div>
            <div v-if="report.markdown" class="memo-content" v-html="renderMarkdown(report.markdown)"></div>
            <div v-else class="empty-panel">The executive memo will appear as the decision converges.</div>
          </article>

          <article class="panel audit-panel">
            <div class="panel-heading">
              <div>
                <span class="panel-index">05</span>
                <h2>Decision audit trail</h2>
                <p>Every evidence, question, answer, branch, and stop event in order.</p>
              </div>
              <span class="audit-count">{{ auditTrail.length }} events</span>
            </div>
            <div v-if="auditTrail.length" class="audit-list">
              <div v-for="(event, index) in auditTrail" :key="event.event_id || index" class="audit-event">
                <div class="audit-rail"><span></span></div>
                <div class="audit-event-copy">
                  <div class="audit-event-topline">
                    <strong>{{ auditType(event) }}</strong>
                    <time>{{ formatTimestamp(event.timestamp || event.created_at) }}</time>
                  </div>
                  <p>{{ auditSummary(event) }}</p>
                </div>
              </div>
            </div>
            <div v-else class="empty-panel">No audit events have been recorded.</div>
          </article>
        </section>

        <footer class="decision-footer">
          <span>INGESTION / {{ String(runState.ingestion_status || 'complete').toUpperCase() }}</span>
          <span>MODE / {{ String(tokenUsage.processing_mode || 'deterministic').toUpperCase() }}</span>
          <span>TOKENS / {{ tokenUsage.total_tokens || 0 }}</span>
          <span v-if="tokenUsage.notes">{{ tokenUsage.notes }}</span>
        </footer>
        </template>
      </template>
    </main>

    <Teleport to="body">
      <Transition name="drawer">
        <div v-if="selectedCitation" class="citation-overlay" @click.self="closeCitation">
          <aside class="citation-drawer">
            <div class="citation-drawer-header">
              <div>
                <span>SOURCE PROVENANCE</span>
                <h2>{{ selectedCitation.label || selectedCitation.source_id || 'Imported source' }}</h2>
              </div>
              <button type="button" @click="closeCitation">×</button>
            </div>
            <div class="citation-body">
              <div class="citation-field">
                <span>Supports claim</span>
                <p>{{ selectedCitationClaim?.text || selectedCitationClaim?.summary || selectedCitationClaim?.description }}</p>
              </div>
              <div class="citation-meta-grid">
                <div><span>Source ID</span><strong>{{ selectedCitation.source_id || '—' }}</strong></div>
                <div><span>Chunk ID</span><strong>{{ selectedCitation.chunk_id || '—' }}</strong></div>
              </div>
              <blockquote v-if="selectedCitation.quote">{{ selectedCitation.quote }}</blockquote>
              <a v-if="selectedCitationUrl" :href="selectedCitationUrl" target="_blank" rel="noopener noreferrer" class="source-link">
                Open original source <span>↗</span>
              </a>
              <div v-else class="source-unavailable">Original URL was not included in the imported report.</div>
            </div>
          </aside>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  cancelCoreResearch,
  evaluateDecisionStop,
  getCoreRefinement,
  getDecisionMemo,
  getDecisionRun,
  startCoreResearch,
  submitInternalAnswer
} from '../api/v2'
import { renderMarkdown, sanitizeMarkdownUrl } from '../utils/markdown'
import {
  branchTone,
  formatDelta,
  formatScore,
  hypothesisDelta,
  numericValue,
  scorePercent
} from '../utils/decision'

const route = useRoute()
const router = useRouter()

const runState = ref(null)
const loading = ref(false)
const loadError = ref('')
const actionMessage = ref('')
const selectedQuestionId = ref('')
const submittingAnswer = ref(false)
const evaluatingStop = ref(false)
const selectedCitation = ref(null)
const selectedCitationClaim = ref(null)
let researchPollTimer = null

const answerForm = reactive({
  answer: '',
  submitted_by: '',
  confidential: true,
  confidence: 0.8
})

const reportId = computed(() => String(route.params.reportId || ''))
const runId = computed(() => String(route.params.runId || runState.value?.run_id || ''))
const routeIdentity = computed(() => reportId.value || String(route.params.runId || ''))
const shortRunId = computed(() => runId.value ? `${runId.value.slice(0, 9)}${runId.value.length > 9 ? '…' : ''}` : '—')
const claims = computed(() => runState.value?.claims || [])
const assumptions = computed(() => runState.value?.assumptions || [])
const contradictions = computed(() => runState.value?.contradictions || [])
const hypotheses = computed(() => runState.value?.hypotheses || [])
const questions = computed(() => runState.value?.internal_questions || [])
const internalEvidence = computed(() => runState.value?.internal_evidence || runState.value?.internal_answers || [])
const decisionImpacts = computed(() => runState.value?.decision_impacts || [])
const stopEvaluation = computed(() => runState.value?.stop_evaluation || {})
const auditTrail = computed(() => runState.value?.audit_trail || runState.value?.audit_events || [])
const report = computed(() => runState.value?.report || runState.value?.decision_memo || {})
const tokenUsage = computed(() => runState.value?.token_usage || {})
const researchJob = computed(() => runState.value?.research_job || {})
const researchStatus = computed(() => String(researchJob.value.status || (route.params.runId ? 'completed' : 'pending')).toLowerCase())
const researchActive = computed(() => ['queued', 'in_progress'].includes(researchStatus.value))
const researchFailed = computed(() => ['failed', 'cancelled'].includes(researchStatus.value))
const researchReady = computed(() => researchStatus.value === 'completed' || !reportId.value)
const researchProgress = computed(() => Math.max(0, Math.min(100, numericValue(researchJob.value.progress))))
const researchStatusLabel = computed(() => {
  if (researchReady.value) return `RESEARCH COMPLETE · ${researchJob.value.citation_count || 0} CITATIONS`
  if (researchFailed.value) return `RESEARCH ${researchStatus.value.toUpperCase()}`
  return `DEEP RESEARCH · ${Math.round(researchProgress.value)}%`
})
const researchStatusMessage = computed(() => {
  if (researchReady.value) return 'Cited external research linked; private-fact refinement is ready.'
  return researchJob.value.message || 'Cited public Deep Research is running in the background.'
})
const selectedCitationUrl = computed(() => sanitizeMarkdownUrl(selectedCitation.value?.url || ''))

const sortedQuestions = computed(() => [...questions.value].sort((a, b) => {
  const aAnswered = a.status === 'answered' ? 1 : 0
  const bAnswered = b.status === 'answered' ? 1 : 0
  if (aAnswered !== bAnswered) return aAnswered - bAnswered
  const rankDifference = numericValue(a.rank, 999) - numericValue(b.rank, 999)
  if (rankDifference !== 0) return rankDifference
  return numericValue(b.information_value_score) - numericValue(a.information_value_score)
}))
const openQuestions = computed(() => {
  if (stopEvaluation.value.should_stop) return []
  return sortedQuestions.value.filter(question => !['answered', 'deferred', 'skipped', 'closed'].includes(question.status))
})
const selectedQuestion = computed(() => sortedQuestions.value.find(question => question.question_id === selectedQuestionId.value) || openQuestions.value[0] || sortedQuestions.value[0] || null)
const leadingHypothesis = computed(() => {
  const leadingId = stopEvaluation.value.leading_hypothesis_id
  return hypotheses.value.find(item => item.hypothesis_id === leadingId)
    || hypotheses.value.filter(item => item.status !== 'pruned').sort((a, b) => numericValue(b.support_score) - numericValue(a.support_score))[0]
    || null
})
const valueComponentRows = computed(() => {
  const components = selectedQuestion.value?.value_components || {}
  return [
    { key: 'decision_sensitivity', label: 'Decision sensitivity', value: components.decision_sensitivity },
    { key: 'uncertainty', label: 'Current uncertainty', value: components.uncertainty },
    { key: 'answerability', label: 'Answerability', value: components.answerability },
    { key: 'urgency', label: 'Urgency', value: components.urgency }
  ]
})

const normalizeRunResponse = (response) => response?.data?.run_id ? response.data : response?.run_id ? response : null

const visibleEvidenceAnswer = (questionId) => {
  const evidence = evidenceForQuestion(questionId)
  if (!evidence || evidence.confidential || evidence.answer === '[REDACTED_INTERNAL_EVIDENCE]') {
    return 'Confidential internal evidence is stored locally and has been incorporated into the decision.'
  }
  return evidence.answer || 'This question has been incorporated into the decision.'
}

const loadRun = async () => {
  if (!routeIdentity.value) return
  if (researchPollTimer) {
    clearTimeout(researchPollTimer)
    researchPollTimer = null
  }
  loading.value = true
  loadError.value = ''
  try {
    const response = reportId.value
      ? await getCoreRefinement(reportId.value)
      : await getDecisionRun(runId.value)
    const nextState = normalizeRunResponse(response)
    if (!nextState) throw new Error('The backend returned an invalid decision state.')
    runState.value = nextState
    chooseNextQuestion()
    if (['queued', 'in_progress'].includes(String(nextState.research_job?.status || '').toLowerCase())) {
      researchPollTimer = setTimeout(loadRun, 4000)
    }
  } catch (error) {
    loadError.value = error.message || 'Unable to load the decision run.'
  } finally {
    loading.value = false
  }
}

const retryResearch = async () => {
  if (!reportId.value || loading.value) return
  loading.value = true
  loadError.value = ''
  try {
    const response = await startCoreResearch(reportId.value, true)
    const nextState = normalizeRunResponse(response)
    if (nextState) runState.value = nextState
    actionMessage.value = 'Public Deep Research restarted. The durable job will continue in the background.'
  } catch (error) {
    loadError.value = error.message || 'Unable to restart public research.'
  } finally {
    loading.value = false
    researchPollTimer = setTimeout(loadRun, 1500)
  }
}

const cancelResearch = async () => {
  if (!reportId.value || loading.value) return
  loading.value = true
  loadError.value = ''
  try {
    const response = await cancelCoreResearch(reportId.value)
    const nextState = normalizeRunResponse(response)
    if (nextState) runState.value = nextState
    actionMessage.value = 'Research cancellation was recorded safely. You can retry from the preserved report state.'
  } catch (error) {
    loadError.value = error.message || 'Unable to cancel public research.'
  } finally {
    loading.value = false
  }
}

const chooseNextQuestion = () => {
  const currentStillExists = questions.value.some(question => question.question_id === selectedQuestionId.value)
  if (!currentStillExists || questions.value.find(question => question.question_id === selectedQuestionId.value)?.status === 'answered') {
    selectedQuestionId.value = openQuestions.value[0]?.question_id || sortedQuestions.value[0]?.question_id || ''
  }
}

const submitAnswer = async () => {
  if (
    !selectedQuestion.value ||
    stopEvaluation.value.should_stop ||
    selectedQuestion.value.status !== 'requested' ||
    !answerForm.answer.trim() ||
    submittingAnswer.value
  ) return
  submittingAnswer.value = true
  loadError.value = ''
  actionMessage.value = ''
  try {
    const response = await submitInternalAnswer(runId.value, {
      question_id: selectedQuestion.value.question_id,
      answer: answerForm.answer.trim(),
      submitted_by: answerForm.submitted_by.trim() || undefined,
      confidential: answerForm.confidential,
      confidence: answerForm.confidence
    })
    const nextState = normalizeRunResponse(response)
    if (nextState) runState.value = nextState
    else await loadRun()
    const newestEvidence = nextState?.internal_evidence?.at?.(-1)
    actionMessage.value = newestEvidence?.decision_usable === false
      ? 'Evidence retained, but the answer was too uncertain or low-confidence to resolve the question.'
      : 'Internal evidence recorded. Decision paths and stop conditions were updated.'
    answerForm.answer = ''
    chooseNextQuestion()
  } catch (error) {
    loadError.value = error.message || 'Unable to submit internal evidence.'
  } finally {
    submittingAnswer.value = false
  }
}

const reevaluateStop = async () => {
  if (evaluatingStop.value) return
  evaluatingStop.value = true
  loadError.value = ''
  try {
    const response = await evaluateDecisionStop(runId.value)
    const nextState = normalizeRunResponse(response)
    if (nextState) runState.value = nextState
    else await loadRun()
    actionMessage.value = 'Continue-or-stop evaluation refreshed.'
  } catch (error) {
    loadError.value = error.message || 'Unable to evaluate the stop condition.'
  } finally {
    evaluatingStop.value = false
  }
}

const downloadMemo = async () => {
  try {
    let markdown = report.value.markdown || ''
    if (!markdown) markdown = await getDecisionMemo(runId.value)
    const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${runState.value?.project_name || runId.value}-decision-memo.md`.replace(/[^a-z0-9._-]+/gi, '-')
    document.body.appendChild(link)
    link.click()
    link.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch (error) {
    loadError.value = error.message || 'Unable to export the memo.'
  }
}

const claimKind = (claim) => {
  const status = String(claim.provenance_status || '').toLowerCase()
  if (status.includes('source') || status.includes('cited')) return 'Sourced fact'
  if (status.includes('unsupported')) return 'Unsupported'
  return claim.kind ? String(claim.kind).replaceAll('_', ' ') : 'Interpretation'
}
const claimTone = (claim) => claimKind(claim).toLowerCase().replaceAll(' ', '_')
const branchLabel = (hypothesis) => branchTone(hypothesis) === 'unchanged' ? 'UNCHANGED' : branchTone(hypothesis).toUpperCase()
const branchLabelFromChange = (change) => {
  if (change.status === 'pruned' || change.new_status === 'pruned' || change.after_status === 'pruned') return 'PRUNED'
  const delta = Number.isFinite(Number(change.delta))
    ? Number(change.delta)
    : numericValue(change.new_score ?? change.after_score) - numericValue(change.previous_score ?? change.old_score ?? change.before_score)
  if (delta > 0.0001) return 'STRENGTHENED'
  if (delta < -0.0001) return 'WEAKENED'
  return 'UNCHANGED'
}
const changeTone = (change) => branchLabelFromChange(change).toLowerCase()
const changeLabel = (change) => {
  const delta = Number.isFinite(Number(change.delta))
    ? Number(change.delta)
    : numericValue(change.new_score ?? change.after_score) - numericValue(change.previous_score ?? change.old_score ?? change.before_score)
  return `${branchLabelFromChange(change)} · ${formatDelta(delta)}`
}
const hypothesisName = (id) => hypotheses.value.find(item => item.hypothesis_id === id)?.label || id || 'Decision path'
const evidenceForQuestion = (questionId) => internalEvidence.value.find(item => item.question_id === questionId)
const contradictionText = (item) => typeof item === 'string' ? item : item.summary || item.description || item.text || item.rationale || 'Conflicting evidence requires review.'
const citationKey = (citation, index) => citation.citation_id || `${citation.source_id || 'source'}-${citation.chunk_id || index}`
const openCitation = (citation, claim) => {
  selectedCitation.value = citation
  selectedCitationClaim.value = claim
}
const closeCitation = () => {
  selectedCitation.value = null
  selectedCitationClaim.value = null
}
const truncate = (value, maxLength) => {
  const text = String(value || '')
  return text.length > maxLength ? `${text.slice(0, maxLength)}…` : text
}
const plainText = (value) => String(value || '')
  .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
  .replace(/[*_`#>]/g, '')
  .trim()
const auditType = (event) => String(event.event_type || event.action || event.type || 'Decision event').replaceAll('_', ' ').toUpperCase()
const auditSummary = (event) => {
  if (event.summary || event.message || event.reason) return event.summary || event.message || event.reason
  if (typeof event.details === 'string') return event.details
  if (event.details && Object.keys(event.details).length) return JSON.stringify(event.details)
  return 'Decision state updated.'
}
const formatTimestamp = (timestamp) => {
  if (!timestamp) return 'Time not recorded'
  const date = new Date(timestamp)
  return Number.isNaN(date.getTime()) ? timestamp : date.toLocaleString()
}

watch(routeIdentity, loadRun)
onMounted(loadRun)
onUnmounted(() => {
  if (researchPollTimer) clearTimeout(researchPollTimer)
})
</script>

<style scoped>
:global(body) {
  background: #f3f1ed;
}

.decision-shell {
  --ink: #11110f;
  --paper: #fbfaf7;
  --muted: #716f68;
  --line: #d9d5cc;
  --orange: #ff4b1f;
  --green: #13795b;
  --red: #b7352d;
  --amber: #9b6400;
  min-height: 100vh;
  color: var(--ink);
  background:
    radial-gradient(circle at 8% 7%, rgba(255, 75, 31, 0.08), transparent 24rem),
    linear-gradient(180deg, #f8f6f1 0, #efede8 100%);
  font-family: 'Space Grotesk', 'Noto Sans SC', system-ui, sans-serif;
}

.decision-header {
  position: sticky;
  top: 0;
  z-index: 40;
  min-height: 64px;
  padding: 0 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  background: rgba(17, 17, 15, 0.96);
  color: white;
  backdrop-filter: blur(16px);
}

.brand-button {
  border: 0;
  background: transparent;
  color: inherit;
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 15px;
  font-weight: 800;
  letter-spacing: 0.08em;
  cursor: pointer;
}

.brand-mark {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  background: var(--orange);
  color: white;
  font-size: 13px;
}

.brand-suffix {
  padding-left: 10px;
  border-left: 1px solid #484843;
  color: #aaa9a3;
  font-size: 10px;
  font-weight: 500;
}

.header-actions,
.token-badge {
  display: flex;
  align-items: center;
}

.header-actions { gap: 12px; }
.new-decision-button {
  min-height: 34px;
  padding: 0 11px;
  border: 1px solid #4c4b46;
  color: #d9d7cf;
  background: transparent;
  font: 9px 'JetBrains Mono', monospace;
  letter-spacing: 0.05em;
  cursor: pointer;
}
.new-decision-button:hover { border-color: var(--orange); color: white; }
.run-reference { color: #898981; font: 10px 'JetBrains Mono', monospace; }
.token-badge {
  gap: 8px;
  padding: 8px 10px;
  border: 1px solid #4c4b46;
  font: 10px 'JetBrains Mono', monospace;
  color: #d9d7cf;
}
.token-badge.zero { color: #a9ebd2; border-color: rgba(42, 176, 127, 0.5); background: rgba(19, 121, 91, 0.18); }
.token-dot { width: 7px; height: 7px; background: #aaa; border-radius: 50%; }
.token-badge.zero .token-dot { background: #3bd69d; box-shadow: 0 0 0 4px rgba(59, 214, 157, 0.1); }
.icon-button { width: 34px; height: 34px; border: 1px solid #4c4b46; background: transparent; color: white; cursor: pointer; font-size: 18px; }
.icon-button:disabled { opacity: 0.5; }

.decision-main { max-width: 1540px; margin: 0 auto; padding: 36px 32px 60px; }
.decision-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(340px, 0.7fr);
  gap: 50px;
  padding: 44px;
  color: white;
  background: var(--ink);
  position: relative;
  overflow: hidden;
}
.decision-hero::after { content: ''; position: absolute; width: 290px; height: 290px; right: -100px; top: -160px; border: 1px solid #3a3935; border-radius: 50%; box-shadow: 0 0 0 58px rgba(255,255,255,0.018), 0 0 0 116px rgba(255,255,255,0.012); }
.hero-copy, .hero-metrics { position: relative; z-index: 1; }
.ingestion-status { display: inline-flex; align-items: center; gap: 9px; padding: 8px 11px; background: rgba(50, 202, 146, 0.12); border: 1px solid rgba(79, 224, 171, 0.35); color: #b9f6df; font: 11px 'JetBrains Mono', monospace; letter-spacing: 0.02em; }
.status-check { width: 17px; height: 17px; display: grid; place-items: center; border-radius: 50%; background: #2cc791; color: #071b14; font-weight: 900; }
.eyebrow { margin: 28px 0 10px; color: var(--orange); font: 700 11px 'JetBrains Mono', monospace; letter-spacing: 0.12em; text-transform: uppercase; }
.decision-hero h1 { max-width: 920px; font-size: clamp(34px, 4vw, 62px); line-height: 1.03; letter-spacing: -0.045em; font-weight: 540; }
.hero-description { max-width: 760px; margin-top: 22px; color: #b5b3ac; font-size: 16px; line-height: 1.65; }
.hero-metrics { display: grid; grid-template-columns: repeat(3, 1fr); align-self: end; border: 1px solid #3a3935; }
.hero-metric { min-height: 118px; padding: 20px; display: flex; flex-direction: column; justify-content: flex-end; border-right: 1px solid #3a3935; }
.hero-metric:last-child { border-right: 0; }
.hero-metric.accent { background: var(--orange); }
.metric-value { font: 500 32px 'JetBrains Mono', monospace; }
.metric-label { margin-top: 8px; color: #aaa8a0; font-size: 11px; line-height: 1.3; }
.hero-metric.accent .metric-label { color: rgba(255,255,255,0.78); }

.inline-alert { margin-top: 14px; padding: 12px 16px; display: flex; justify-content: space-between; gap: 20px; font-size: 13px; }
.inline-alert button { border: 0; background: transparent; text-decoration: underline; cursor: pointer; }
.error-alert { color: #78231f; background: #f8d8d5; }
.success-alert { color: #0d5f46; background: #d7f2e8; }

.status-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-top: 18px; }
.status-card, .panel { background: var(--paper); border: 1px solid var(--line); }
.status-card { padding: 26px 28px; }
.status-card.stop { border-top: 4px solid var(--green); }
.status-card.continue { border-top: 4px solid var(--orange); }
.recommendation-card { border-top: 4px solid var(--ink); }
.card-kicker, .panel-index { color: var(--muted); font: 700 10px 'JetBrains Mono', monospace; letter-spacing: 0.12em; }
.stop-heading-row { display: flex; justify-content: space-between; gap: 24px; margin-top: 16px; }
.stop-verdict { font-size: 28px; font-weight: 620; }
.stop-heading-row p, .recommendation-card p { margin-top: 9px; color: var(--muted); line-height: 1.5; }
.verdict-icon { flex: 0 0 auto; width: 48px; height: 48px; display: grid; place-items: center; background: var(--ink); color: white; font-size: 19px; }
.status-card.stop .verdict-icon { background: var(--green); }
.stop-metrics { display: flex; flex-wrap: wrap; gap: 22px; margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--line); color: var(--muted); font-size: 12px; }
.stop-metrics strong { color: var(--ink); font-family: 'JetBrains Mono', monospace; }
.text-button { margin-top: 16px; padding: 0; border: 0; background: transparent; color: var(--ink); text-decoration: underline; cursor: pointer; font-size: 12px; }
.recommendation-card h2 { margin-top: 16px; font-size: 26px; line-height: 1.2; }
.recommendation-footer { display: flex; gap: 14px; align-items: center; margin-top: 20px; color: var(--muted); font-size: 11px; }
.report-status { padding: 5px 7px; color: white; background: var(--ink); font: 10px 'JetBrains Mono', monospace; }

.workspace-grid { display: grid; grid-template-columns: minmax(0, 1.55fr) minmax(370px, 0.65fr); gap: 18px; margin-top: 18px; align-items: start; }
.workspace-primary { display: grid; gap: 18px; }
.panel { padding: 28px; }
.panel-heading { display: flex; justify-content: space-between; gap: 30px; align-items: flex-start; padding-bottom: 22px; border-bottom: 1px solid var(--line); }
.panel-heading h2 { margin-top: 8px; font-size: 25px; letter-spacing: -0.025em; }
.panel-heading p { margin-top: 6px; max-width: 690px; color: var(--muted); font-size: 13px; line-height: 1.5; }
.branch-legend { display: flex; flex-wrap: wrap; gap: 12px; color: var(--muted); font-size: 10px; }
.branch-legend span { display: flex; align-items: center; gap: 5px; }
.legend-dot { width: 7px; height: 7px; border-radius: 50%; background: #999; }
.legend-dot.strengthened { background: var(--green); }
.legend-dot.weakened { background: var(--amber); }
.legend-dot.pruned { background: var(--red); }

.branch-map { display: grid; grid-template-columns: 190px 36px 1fr; align-items: center; padding-top: 24px; }
.decision-root { min-height: 104px; padding: 18px; display: flex; flex-direction: column; justify-content: center; color: white; background: var(--ink); }
.decision-root span { color: var(--orange); font: 10px 'JetBrains Mono', monospace; letter-spacing: 0.1em; }
.decision-root strong { margin-top: 9px; font-size: 13px; line-height: 1.4; }
.branch-connector { height: 1px; background: #aaa79e; }
.branch-list { display: grid; gap: 10px; position: relative; }
.branch-list::before { content: ''; position: absolute; left: 0; top: 22px; bottom: 22px; width: 1px; background: #aaa79e; }
.branch-card { position: relative; margin-left: 18px; padding: 17px 18px; border: 1px solid var(--line); background: white; }
.branch-card::before { content: ''; position: absolute; width: 18px; height: 1px; left: -19px; top: 50%; background: #aaa79e; }
.branch-card.strengthened { border-left: 4px solid var(--green); }
.branch-card.weakened { border-left: 4px solid var(--amber); }
.branch-card.pruned { opacity: 0.64; border-left: 4px solid var(--red); background: repeating-linear-gradient(-45deg, #faf8f5, #faf8f5 7px, #f1eee8 7px, #f1eee8 8px); }
.branch-card-top, .branch-delta-row { display: flex; justify-content: space-between; gap: 20px; align-items: center; }
.branch-state { font: 700 9px 'JetBrains Mono', monospace; color: var(--muted); }
.branch-card.strengthened .branch-state { color: var(--green); }
.branch-card.weakened .branch-state { color: var(--amber); }
.branch-card.pruned .branch-state { color: var(--red); }
.branch-card h3 { margin-top: 4px; font-size: 17px; }
.branch-score { font: 600 22px 'JetBrains Mono', monospace; }
.branch-card p { margin-top: 8px; color: var(--muted); font-size: 12px; line-height: 1.45; }
.score-track { height: 5px; margin-top: 14px; background: #ece9e3; overflow: hidden; }
.score-track span { display: block; height: 100%; background: var(--ink); transition: width 450ms ease; }
.branch-card.strengthened .score-track span { background: var(--green); }
.branch-card.weakened .score-track span { background: var(--amber); }
.branch-card.pruned .score-track span { background: var(--red); }
.branch-delta-row { margin-top: 8px; color: var(--muted); font: 9px 'JetBrains Mono', monospace; }
.prune-reason { margin-top: 10px; padding: 8px; color: #77231e; background: rgba(183, 53, 45, 0.08); font-size: 11px; }

.evidence-counts { display: flex; gap: 8px; flex-wrap: wrap; }
.evidence-counts span, .audit-count { padding: 6px 8px; border: 1px solid var(--line); color: var(--muted); font: 9px 'JetBrains Mono', monospace; }
.evidence-layout { display: grid; grid-template-columns: 1.15fr 0.85fr; gap: 26px; padding-top: 24px; }
.evidence-column.secondary { padding-left: 26px; border-left: 1px solid var(--line); }
.column-title { margin-bottom: 12px; font-size: 14px; }
.evidence-item, .assumption-item { padding: 15px 0; border-top: 1px solid var(--line); }
.evidence-item:first-of-type, .assumption-item:first-of-type { border-top: 0; padding-top: 0; }
.evidence-item-meta, .assumption-topline { display: flex; justify-content: space-between; gap: 12px; align-items: center; }
.evidence-kind, .assumption-status { padding: 4px 6px; background: #e8e4dc; color: #4d4b46; font: 700 9px 'JetBrains Mono', monospace; text-transform: uppercase; }
.evidence-kind.sourced, .evidence-kind.cited, .evidence-kind.source_fact { color: #0b6247; background: #d9f0e7; }
.evidence-kind.unsupported { color: #77231e; background: #f5ddd9; }
.evidence-id { color: #a09d95; font: 9px 'JetBrains Mono', monospace; }
.evidence-item p, .assumption-item p { margin-top: 9px; font-size: 13px; line-height: 1.55; }
.assumption-topline { color: var(--muted); font: 9px 'JetBrains Mono', monospace; text-transform: uppercase; }
.assumption-status.confirmed { color: #0b6247; background: #d9f0e7; }
.assumption-status.rejected { color: #77231e; background: #f5ddd9; }
.assumption-item small { display: block; margin-top: 7px; color: var(--muted); line-height: 1.45; }
.citation-list { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 11px; }
.citation-chip { padding: 5px 7px; border: 1px solid #bbb7ad; background: transparent; color: #4e4c46; font: 9px 'JetBrains Mono', monospace; cursor: pointer; }
.citation-chip:hover { border-color: var(--orange); color: var(--orange); }
.no-source { display: block; margin-top: 10px; color: #9b6400; font-size: 10px; }
.contradiction-title { margin-top: 26px; }
.contradiction-item { display: flex; gap: 10px; padding: 12px; margin-top: 8px; color: #742620; background: #f7e4e1; border-left: 3px solid var(--red); }
.contradiction-item > span { flex: 0 0 auto; width: 19px; height: 19px; display: grid; place-items: center; border-radius: 50%; color: white; background: var(--red); font: 700 11px 'JetBrains Mono', monospace; }
.contradiction-item strong { font-size: 11px; }
.contradiction-item p { margin-top: 4px; font-size: 11px; line-height: 1.45; }

.impact-list { padding-top: 22px; }
.impact-item { display: grid; grid-template-columns: 42px 1fr; gap: 15px; padding: 15px 0; border-top: 1px solid var(--line); }
.impact-item:first-child { padding-top: 0; border-top: 0; }
.impact-index { width: 36px; height: 36px; display: grid; place-items: center; background: var(--ink); color: white; font: 10px 'JetBrains Mono', monospace; }
.impact-content h3 { font-size: 15px; }
.impact-content > p { margin-top: 5px; color: var(--muted); font-size: 12px; }
.change-list { margin-top: 9px; }
.change-row { display: flex; justify-content: space-between; gap: 15px; padding: 7px 0; border-top: 1px dashed var(--line); font-size: 11px; }
.change-row strong { font: 700 9px 'JetBrains Mono', monospace; }
.change-row strong.strengthened { color: var(--green); }
.change-row strong.weakened { color: var(--amber); }
.change-row strong.pruned { color: var(--red); }

.question-panel { position: sticky; top: 82px; padding: 0; overflow: hidden; background: #171715; border-color: #171715; color: white; }
.question-panel-header { padding: 26px; display: flex; justify-content: space-between; gap: 18px; border-bottom: 1px solid #3a3935; }
.panel-index.inverse { color: var(--orange); }
.question-panel-header h2 { margin-top: 7px; font-size: 26px; }
.question-panel-header p { margin-top: 6px; color: #9e9c95; font-size: 12px; line-height: 1.4; }
.queue-count { flex: 0 0 auto; height: fit-content; padding: 5px 7px; color: #ffb8a4; border: 1px solid rgba(255, 75, 31, 0.5); font: 9px 'JetBrains Mono', monospace; }
.question-queue { max-height: 230px; overflow-y: auto; border-bottom: 1px solid #3a3935; }
.queue-item { width: 100%; padding: 13px 18px; display: grid; grid-template-columns: 32px 1fr 42px; gap: 9px; align-items: start; border: 0; border-bottom: 1px solid #2f2e2b; background: transparent; color: white; text-align: left; cursor: pointer; }
.queue-item:hover, .queue-item.active { background: #262622; }
.queue-item.active { box-shadow: inset 3px 0 var(--orange); }
.queue-item.answered { opacity: 0.48; }
.queue-item:disabled { opacity: 0.45; cursor: not-allowed; }
.queue-rank, .queue-score { font: 9px 'JetBrains Mono', monospace; color: #8f8d86; }
.queue-score { color: #ff9f83; text-align: right; }
.queue-copy { font-size: 11px; line-height: 1.45; }
.selected-question { padding: 24px 26px 27px; max-height: calc(100vh - 390px); overflow-y: auto; }
.question-meta { display: flex; justify-content: space-between; gap: 12px; color: #96948d; font: 9px 'JetBrains Mono', monospace; text-transform: uppercase; }
.selected-question h3 { margin-top: 14px; font-size: 21px; line-height: 1.3; }
.question-rationale { margin-top: 9px; color: #aaa8a1; font-size: 12px; line-height: 1.55; }
.value-score-heading { display: flex; justify-content: space-between; align-items: center; margin-top: 20px; padding-top: 16px; border-top: 1px solid #3a3935; font-size: 11px; }
.value-score-heading strong { color: #ff9f83; font: 600 22px 'JetBrains Mono', monospace; }
.value-components { display: grid; grid-template-columns: 1fr 1fr; gap: 7px; margin-top: 10px; }
.value-components div { padding: 9px; background: #22221f; }
.value-components span { display: block; color: #8f8d86; font-size: 9px; }
.value-components strong { display: block; margin-top: 5px; font: 11px 'JetBrains Mono', monospace; }
.score-formula { margin-top: 9px; color: #77756f; font: 9px 'JetBrains Mono', monospace; line-height: 1.45; }
.expected-change { margin-top: 17px; padding: 13px; border: 1px solid #43423d; }
.expected-change > span { color: var(--orange); font: 700 9px 'JetBrains Mono', monospace; }
.expected-change p { margin-top: 7px; color: #c1bfb8; font-size: 11px; line-height: 1.45; }
.affected-branches { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 9px; }
.affected-branches span { padding: 4px 6px; background: #30302c; color: #bdbbb4; font-size: 9px; }
.answer-form { margin-top: 20px; }
.answer-form label { display: block; color: #aaa8a1; font-size: 10px; }
.answer-form textarea, .answer-form input, .answer-form select { width: 100%; margin-top: 6px; padding: 10px; border: 1px solid #4a4944; border-radius: 0; outline: 0; color: white; background: #20201d; font: 12px inherit; }
.answer-form textarea:focus, .answer-form input:focus, .answer-form select:focus { border-color: var(--orange); }
.answer-form-row { display: grid; grid-template-columns: 1fr 120px; gap: 9px; margin-top: 10px; }
.privacy-check { margin-top: 11px; display: flex !important; align-items: center; gap: 8px; cursor: pointer; }
.privacy-check input { width: auto; margin: 0; accent-color: var(--orange); }
.answer-button { width: 100%; margin-top: 14px; padding: 13px; display: flex; justify-content: space-between; border: 0; background: var(--orange); color: white; font-size: 11px; font-weight: 650; cursor: pointer; }
.answer-button:disabled { opacity: 0.45; cursor: not-allowed; }
.privacy-note { margin-top: 9px; color: #77756f; font-size: 9px; line-height: 1.4; }
.answered-card { margin-top: 18px; padding: 14px; border: 1px solid rgba(58, 214, 157, 0.35); background: rgba(19, 121, 91, 0.13); }
.answered-card span { color: #75e4ba; font: 700 9px 'JetBrains Mono', monospace; }
.answered-card p { margin-top: 8px; color: #c0d8cf; font-size: 11px; line-height: 1.45; }
.deferred-card { border-color: rgba(255, 159, 131, 0.4); background: rgba(255, 75, 31, 0.1); }
.deferred-card span { color: #ff9f83; }
.deferred-card p { color: #dec5bd; }

.deliverables-grid { display: grid; grid-template-columns: 1.25fr 0.75fr; gap: 18px; margin-top: 18px; }
.secondary-button, .primary-button { padding: 10px 13px; border: 1px solid var(--ink); background: transparent; color: var(--ink); cursor: pointer; font-size: 11px; }
.primary-button { color: white; background: var(--ink); }
.secondary-button:disabled { opacity: 0.4; cursor: not-allowed; }
.memo-content { padding-top: 24px; color: #292824; line-height: 1.62; }
.memo-content :deep(h2), .memo-content :deep(h3), .memo-content :deep(h4) { margin: 22px 0 9px; }
.memo-content :deep(p), .memo-content :deep(li) { font-size: 13px; }
.memo-content :deep(.md-table) { width: 100%; border-collapse: collapse; font-size: 11px; }
.memo-content :deep(th), .memo-content :deep(td) { padding: 8px; border: 1px solid var(--line); }
.memo-content :deep(.md-link) { color: var(--orange); }
.audit-list { padding-top: 21px; max-height: 620px; overflow-y: auto; }
.audit-event { display: grid; grid-template-columns: 18px 1fr; gap: 10px; min-height: 64px; }
.audit-rail { position: relative; display: flex; justify-content: center; }
.audit-rail::after { content: ''; position: absolute; top: 14px; bottom: 0; width: 1px; background: var(--line); }
.audit-event:last-child .audit-rail::after { display: none; }
.audit-rail span { position: relative; z-index: 1; width: 9px; height: 9px; margin-top: 3px; border: 2px solid var(--paper); border-radius: 50%; background: var(--orange); box-shadow: 0 0 0 1px var(--orange); }
.audit-event-copy { padding-bottom: 16px; }
.audit-event-topline { display: flex; justify-content: space-between; gap: 12px; }
.audit-event-topline strong { font: 700 9px 'JetBrains Mono', monospace; }
.audit-event-topline time { color: #99968e; font-size: 9px; }
.audit-event-copy p { margin-top: 6px; color: var(--muted); font-size: 11px; line-height: 1.45; overflow-wrap: anywhere; }
.empty-panel { padding: 28px 0 8px; color: #99968e; font-size: 12px; }
.empty-panel.compact { padding: 12px 0; }
.inverse-empty { padding: 25px; color: #8f8d86; }

.decision-footer { margin-top: 18px; padding: 14px 16px; display: flex; flex-wrap: wrap; gap: 20px; color: #77746d; border: 1px solid var(--line); font: 9px 'JetBrains Mono', monospace; }
.state-card { max-width: 660px; margin: 100px auto; padding: 50px; text-align: center; background: var(--paper); border: 1px solid var(--line); }
.state-card h2 { margin-top: 16px; }
.state-card p { margin: 10px 0 20px; color: var(--muted); }
.state-kicker { color: var(--red); font: 700 10px 'JetBrains Mono', monospace; }
.research-state { margin: 18px auto 0; text-align: left; }
.research-state .loading-ring { margin: 0 0 18px; }
.research-state .state-kicker { color: var(--orange); }
.research-progress { height: 7px; overflow: hidden; background: #e4e0d8; }
.research-progress span { display: block; height: 100%; background: var(--orange); transition: width 350ms ease; }
.research-actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }
.ingestion-status.researching { color: #ffe2d7; border-color: rgba(255, 159, 131, 0.45); background: rgba(255, 75, 31, 0.12); }
.loading-ring { width: 34px; height: 34px; margin: auto; border: 3px solid #ddd8cf; border-top-color: var(--orange); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.citation-overlay { position: fixed; inset: 0; z-index: 200; display: flex; justify-content: flex-end; background: rgba(9,9,8,0.55); backdrop-filter: blur(3px); }
.citation-drawer { width: min(520px, 92vw); height: 100%; background: var(--paper); box-shadow: -20px 0 70px rgba(0,0,0,0.22); }
.citation-drawer-header { padding: 26px; display: flex; justify-content: space-between; gap: 20px; color: white; background: var(--ink); }
.citation-drawer-header span { color: var(--orange); font: 700 9px 'JetBrains Mono', monospace; }
.citation-drawer-header h2 { margin-top: 8px; font-size: 21px; }
.citation-drawer-header button { width: 34px; height: 34px; border: 1px solid #55544f; background: transparent; color: white; cursor: pointer; font-size: 22px; }
.citation-body { padding: 28px; }
.citation-field span, .citation-meta-grid span { color: #8b8880; font: 9px 'JetBrains Mono', monospace; text-transform: uppercase; }
.citation-field p { margin-top: 9px; font-size: 14px; line-height: 1.5; }
.citation-meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 24px; }
.citation-meta-grid div { padding: 13px; border: 1px solid var(--line); }
.citation-meta-grid strong { display: block; margin-top: 7px; font: 10px 'JetBrains Mono', monospace; overflow-wrap: anywhere; }
.citation-body blockquote { margin-top: 24px; padding: 20px; border-left: 4px solid var(--orange); background: #eeebe4; font-family: Georgia, serif; font-size: 15px; line-height: 1.65; }
.source-link, .source-unavailable { margin-top: 22px; padding: 13px; display: flex; justify-content: space-between; border: 1px solid var(--ink); color: var(--ink); text-decoration: none; font-size: 12px; }
.source-link:hover { color: white; background: var(--ink); }
.source-unavailable { color: #89867e; border-color: var(--line); }
.drawer-enter-active, .drawer-leave-active { transition: opacity 0.2s ease; }
.drawer-enter-active .citation-drawer, .drawer-leave-active .citation-drawer { transition: transform 0.25s ease; }
.drawer-enter-from, .drawer-leave-to { opacity: 0; }
.drawer-enter-from .citation-drawer, .drawer-leave-to .citation-drawer { transform: translateX(100%); }

@media (max-width: 1120px) {
  .decision-hero, .workspace-grid, .deliverables-grid { grid-template-columns: 1fr; }
  .question-panel { position: static; }
  .selected-question { max-height: none; }
}

@media (max-width: 760px) {
  .decision-header { padding: 10px 16px; align-items: flex-start; }
  .brand-suffix, .run-reference { display: none; }
  .header-actions { flex-wrap: wrap; justify-content: flex-end; }
  .token-badge { font-size: 8px; }
  .decision-main { padding: 18px 12px 40px; }
  .decision-hero { padding: 27px 22px; gap: 30px; }
  .hero-metrics { grid-template-columns: 1fr; }
  .hero-metric { min-height: 76px; border-right: 0; border-bottom: 1px solid #3a3935; }
  .status-grid, .evidence-layout { grid-template-columns: 1fr; }
  .evidence-column.secondary { padding: 22px 0 0; border-left: 0; border-top: 1px solid var(--line); }
  .branch-map { grid-template-columns: 1fr; gap: 14px; }
  .branch-connector, .branch-list::before, .branch-card::before { display: none; }
  .branch-card { margin-left: 0; }
  .panel-heading { flex-direction: column; }
  .panel { padding: 21px; }
}
</style>
