<template>
  <div class="decision-shell" :class="{ 'dev-replay-readonly': isDevReplay }">
    <header class="decision-header">
      <BrandLockup class="brand-button" suffix="SIMULATION DECISION" theme="dark" />

      <div class="header-actions">
        <div class="run-reference">RUN / {{ shortRunId }}</div>
        <div class="token-badge zero">
          <span class="token-dot"></span>
          <span>{{ researchStatusLabel }}</span>
        </div>
        <button class="icon-button" type="button" aria-label="Refresh decision state" :disabled="loading" @click="loadRun" title="Refresh decision state">↻</button>
      </div>
    </header>

    <div v-if="isDevReplay" class="replay-readonly-banner" role="status">
      DEV REPLAY · SAVED DECISION OUTCOME · EDITING CONTROLS ARE READ-ONLY
    </div>

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
        <section ref="heroRef" class="outcome-hero" :class="{ ready: decisionReady }">
          <div class="outcome-topline">
            <span class="outcome-status"><i></i>{{ decisionStatusLabel }}</span>
            <span>{{ outcomePhaseLabel }}</span>
          </div>

          <div v-if="!internalEvidenceComplete" class="demo-progress">
            <div>
              <span>{{ isDemonstration ? 'DEMO PROGRESS' : 'REFINEMENT PROGRESS' }}</span>
              <strong>{{ answeredQuestionCount }} of {{ questions.length }} approval inputs provided</strong>
            </div>
            <div class="demo-progress-track"><i :style="{ width: `${inputProgressPercent}%` }"></i></div>
            <p>This stage intentionally begins with incomplete internal information. Public simulation gets the decision this far; private organizational facts make it actionable.</p>
          </div>

          <div class="outcome-layout">
            <div class="outcome-copy">
              <p class="outcome-kicker">DECISION REQUESTED</p>
              <p class="decision-request" :title="fullDecisionQuestion">{{ decisionRequest }}</p>
              <h1 :title="recommendedAction">{{ decisionHeadline }}</h1>
              <p class="outcome-summary">{{ decisionSummary }}</p>
              <div class="outcome-actions">
                <button class="outcome-primary" type="button" :disabled="primaryActionDisabled" @click="handlePrimaryAction">
                  {{ primaryActionLabel }}
                </button>
                <button class="outcome-secondary" type="button" :disabled="!briefAvailable" @click="downloadMemo">
                  {{ briefDownloadLabel }}
                </button>
              </div>
            </div>

            <aside class="outcome-snapshot">
              <span class="snapshot-kicker">DECISION STATUS</span>
              <strong>{{ decisionStatusHeadline }}</strong>
              <p>{{ readinessExplanation }}</p>
              <dl>
                <div>
                  <dt>Recommendation basis</dt>
                  <dd>{{ recommendationBasis }}</dd>
                </div>
                <div>
                  <dt>Open approval gates</dt>
                  <dd>{{ decisionBlockers.length }}</dd>
                </div>
                <div>
                  <dt>Evidence posture</dt>
                  <dd>{{ evidencePostureLabel }}</dd>
                </div>
              </dl>
              <small>Qualitative posture only — not a probability or confidence score.</small>
            </aside>
          </div>
        </section>

        <!-- Condensed sticky summary: the full outcome-hero is ~590px tall and
             can't stay pinned, so once it scrolls out of view (IntersectionObserver
             below) this slim bar takes its place at the top, above the sticky
             .completion-ladder. Presentation-only — not demo-gated. -->
        <div class="condensed-hero-bar" :class="{ visible: heroCondensed }" aria-hidden="true">
          <span class="condensed-hero-status">{{ decisionStatusLabel }}</span>
          <span class="condensed-hero-headline" :title="decisionHeadline">{{ decisionHeadline }}</span>
          <span class="condensed-hero-progress">{{ condensedProgressLabel }}</span>
        </div>

        <section class="completion-ladder" :class="{ 'ladder-pinned-below-bar': heroCondensed }" aria-label="Decision completion stages">
          <div v-for="stage in completionStages" :key="stage.id" :class="{ complete: stage.complete, active: stage.active }">
            <span>{{ stage.complete ? '✓' : stage.index }}</span>
            <small>{{ stage.label }}</small>
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

        <section class="executive-summary-grid" :style="sectionStyle('executiveSummary')">
          <article class="executive-card rationale-card">
            <span class="executive-card-kicker">WHY THIS DECISION</span>
            <h2>{{ actionIsExecutable ? 'The case for the recommended path' : 'What prevents a credible recommendation' }}</h2>
            <ol v-if="executiveReasons.length" class="reason-list">
              <li v-for="(reason, index) in executiveReasons" :key="`${index}-${reason}`">
                <span>{{ String(index + 1).padStart(2, '0') }}</span>
                <p>{{ reason }}</p>
              </li>
            </ol>
            <p v-else class="executive-empty">The simulation has not produced enough decision-grade rationale to support an executive commitment.</p>
          </article>

          <article class="executive-card conditions-card">
            <span class="executive-card-kicker">CONDITIONS & GUARDRAILS</span>
            <h2>{{ decisionBlockers.length ? 'Close these before full commitment' : 'Proceed with explicit controls' }}</h2>
            <div v-if="decisionBlockers.length" class="condition-list">
              <div v-for="(blocker, index) in decisionBlockers.slice(0, 4)" :key="`${index}-${blocker.title}`">
                <span>{{ blocker.status }}</span>
                <div>
                  <strong>{{ blocker.title }}</strong>
                  <small>{{ blocker.owner }}</small>
                </div>
              </div>
            </div>
            <div v-else class="guardrail-callout">
              <span>✓</span>
              <p>All ranked approval gates are closed. Release resources in stages and keep the reversal trigger visible to the accountable owner.</p>
            </div>
          </article>
        </section>

        <section id="action-plan" class="action-plan-panel" :style="sectionStyle('actionPlan')">
          <div class="action-plan-heading">
            <div>
              <span class="executive-card-kicker">COMPILED EXECUTION PLAN</span>
              <h2>Turn binding evidence into staged work</h2>
            </div>
            <p>Each stage creates a deliverable, resolves a dependency, tests an assumption, enforces a constraint, evaluates a gate, or executes a reversal.</p>
          </div>

          <div class="plan-quality-strip" :class="{ ready: executionPlanComplete }">
            <div><span>EXECUTABILITY</span><strong>{{ Math.round(executabilityScore) }}/100</strong></div>
            <div><span>EVIDENCE OPERATIONALIZED</span><strong>{{ Math.round(evidenceActionCoverage) }}%</strong></div>
            <div><span>PLAN STATUS</span><strong>{{ executionPlanComplete ? 'Decision-ready' : `${executionHardFailures.length} hard gap${executionHardFailures.length === 1 ? '' : 's'}` }}</strong></div>
          </div>

          <div v-if="executionHardFailures.length" class="plan-gap-panel">
            <span>EXECUTION GAPS</span>
            <p v-for="failure in executionGapMessages" :key="failure">{{ failure }}</p>

            <div v-if="ownerOnlyExecutionBlock" id="execution-owner-assignment" class="owner-assignment-panel">
              <div class="owner-assignment-heading">
                <strong>Assign the two accountable owners</strong>
                <small>This updates the execution plan, memo, and approval state only. The simulation and evidence remain unchanged.</small>
              </div>
              <div class="owner-assignment-grid">
                <label v-for="gap in executionOwnerGaps" :key="gap.actionType">
                  <span>{{ gap.fieldLabel }}</span>
                  <input
                    v-model.trim="executionOwnerForm[gap.actionType]"
                    type="text"
                    maxlength="200"
                    :placeholder="gap.placeholder"
                    :disabled="savingExecutionOwners || isDevReplay"
                  >
                </label>
              </div>
              <button
                class="owner-assignment-button"
                type="button"
                :disabled="!executionOwnerFormComplete || savingExecutionOwners || isDevReplay"
                @click="saveExecutionOwners"
              >
                {{ savingExecutionOwners ? 'Saving owners…' : 'Save owners and recompile plan' }}
              </button>
            </div>
          </div>

          <div class="action-plan-list">
            <article v-for="(step, index) in actionPlan" :key="step.action_id" class="action-step execution-contract">
              <div class="action-step-index">{{ String(index + 1).padStart(2, '0') }}</div>
              <div class="action-step-copy">
                <div class="action-step-meta">
                  <span>{{ step.action_type.replace('_', ' / ') }} · {{ step.stage }}</span>
                  <i>{{ step.status }}</i>
                </div>
                <h3>{{ step.title }}</h3>
                <p>{{ step.purpose }}</p>
                <div class="action-contract-grid">
                  <div><span>OWNER</span><strong>{{ step.owner }}</strong></div>
                  <div><span>ACCOUNTABLE</span><strong>{{ step.accountable_executive }}</strong></div>
                  <div><span>DEADLINE</span><strong>{{ step.deadline }}</strong></div>
                  <div><span>RESOURCE BOUNDARY</span><strong>{{ step.budget_or_capacity }}</strong></div>
                </div>
                <div class="action-deliverable">
                  <span>DELIVERABLE</span>
                  <strong>{{ step.deliverable }}</strong>
                  <small>Starts when: {{ step.start_condition }}</small>
                </div>
                <div class="action-contract-columns">
                  <div>
                    <span>ACCEPTANCE CRITERIA</span>
                    <ul><li v-for="criterion in step.acceptance_criteria" :key="criterion">{{ criterion }}</li></ul>
                  </div>
                  <div>
                    <span>DEPENDENCIES</span>
                    <ul v-if="step.dependencies.length"><li v-for="dependency in step.dependencies" :key="dependency">{{ dependency }}</li></ul>
                    <p v-else>No external dependency recorded.</p>
                  </div>
                </div>
                <div class="failure-response">
                  <span>IF THIS STAGE FAILS</span>
                  <p>{{ step.failure_response }}</p>
                </div>
                <details class="action-provenance">
                  <summary>Why this action exists · {{ step.evidence_source_ids.length }} evidence link{{ step.evidence_source_ids.length === 1 ? '' : 's' }}</summary>
                  <div v-if="step.evidence_source_ids.length">
                    <p v-for="factId in step.evidence_source_ids" :key="factId">
                      <span>{{ executionFactsById.get(factId)?.source_question_category || executionFactsById.get(factId)?.fact_type || 'decision evidence' }}</span>
                      <strong>{{ executionFactsById.get(factId)?.statement || factId }}</strong>
                      <small>Internal answer / source → {{ executionFactsById.get(factId)?.fact_type || 'execution fact' }} → {{ step.action_type }} action</small>
                    </p>
                  </div>
                  <p v-else>This stage is required by the execution contract itself; no private fact was mapped to it.</p>
                </details>
              </div>
            </article>
          </div>
          <div v-if="!actionPlan.length" class="empty-panel">No execution plan can be compiled until a valid management action exists.</div>
        </section>

        <section v-if="false" class="completed-preview-panel" aria-hidden="true">
          <div class="completed-preview-heading">
            <div>
              <span class="executive-card-kicker">COMPLETED DECISION PREVIEW · ILLUSTRATIVE</span>
              <h2>What appears after every approval gate is closed</h2>
            </div>
            <span>PREVIEW — NOT THE CURRENT RESULT</span>
          </div>
          <div class="completed-preview-decision">
            <span>FINAL RECOMMENDATION</span>
            <h3>{{ completedDecisionPreview.recommendation }}</h3>
          </div>
          <div class="completed-preview-grid">
            <div>
              <span>OWNER</span>
              <strong>{{ completedDecisionPreview.owner }}</strong>
            </div>
            <div>
              <span>BUDGET GATE</span>
              <strong>{{ completedDecisionPreview.budgetGate }}</strong>
            </div>
            <div>
              <span>SUCCESS KPIs</span>
              <strong>{{ completedDecisionPreview.kpis }}</strong>
            </div>
            <div>
              <span>PAUSE / REVERSE</span>
              <strong>{{ completedDecisionPreview.trigger }}</strong>
            </div>
          </div>
        </section>

        <details
          id="decision-record"
          class="decision-record"
          :style="sectionStyle('decisionRecord')"
          :open="decisionRecordOpen"
          @toggle="decisionRecordOpen = $event.target.open"
        >
          <summary>
            <span>
              <strong>Decision record & methodology</strong>
              <small>Review the internal fact collection status, action signal, and decision method approval.</small>
            </span>
            <i>{{ decisionRecordOpen ? 'Hide record' : 'Review record' }}</i>
          </summary>
          <div class="decision-record-body">

        <section class="status-grid">
          <article class="status-card" :class="stopEvaluation.should_stop ? 'stop' : 'continue'">
            <div class="card-kicker">INTERNAL FACT COLLECTION</div>
            <div class="stop-heading-row">
              <div>
                <div class="stop-verdict">{{ internalEvidenceComplete ? 'Internal fact collection complete' : 'Continue collecting internal facts' }}</div>
                <p>{{ internalCollectionReason }}</p>
              </div>
              <div class="verdict-icon">{{ stopEvaluation.should_stop ? '■' : '→' }}</div>
            </div>
            <div class="stop-metrics">
              <span>Remaining question priority <strong>{{ formatScore(stopEvaluation.remaining_question_priority) }}</strong></span>
              <span>Leading margin <strong>{{ formatScore(stopEvaluation.leading_margin) }}</strong></span>
            </div>
            <button class="text-button" type="button" :disabled="isDevReplay || evaluatingStop" @click="reevaluateStop">
              {{ evaluatingStop ? 'Evaluating…' : 'Re-evaluate stop condition' }}
            </button>
          </article>

          <article class="status-card recommendation-card">
            <div class="card-kicker">{{ actionSignalKicker }}</div>
            <h2 :title="actionSignalLabel">{{ actionSignalLabel }}</h2>
            <p>{{ actionSignalExplanation }}</p>
            <div class="recommendation-footer">
              <span class="report-status">MEMO / {{ String(report.status || 'draft').toUpperCase() }}</span>
              <span v-if="report.stop_reason">{{ report.stop_reason }}</span>
            </div>
          </article>

          <article id="decision-model-review" class="status-card decision-analysis-card">
            <div class="analysis-card-heading">
              <div>
                <div class="card-kicker">SHADOW DECISION ANALYSIS</div>
                <h2>{{ decisionAnalysisHeading }}</h2>
              </div>
              <span class="analysis-state" :class="decisionModelComplete ? 'calculated' : 'pending'">
                {{ decisionAnalysisStateLabel }}
              </span>
            </div>

            <section v-if="internalEvidenceComplete" id="action-confirmation" class="action-confirmation-panel">
              <div>
                <span>MANAGEMENT ACTION GATE</span>
                <h3>{{ actionsConfirmed ? 'Action alternatives confirmed' : 'Confirm the actions before modeling the decision' }}</h3>
                <p>Stakeholders, market observations, and prompt fragments cannot pass this gate.</p>
              </div>
              <div class="confirmable-actions">
                <span v-for="hypothesis in hypotheses" :key="hypothesis.hypothesis_id">
                  <i>{{ looksLikeExecutableAction(hypothesis.label) ? '✓' : '!' }}</i>
                  {{ hypothesis.label }}
                </span>
              </div>
              <template v-if="!actionsConfirmed">
                <label class="action-confirmation-check">
                  <input v-model="actionConfirmationAccepted" type="checkbox" :disabled="isDevReplay || !actionsValid" />
                  <span>I confirm that every listed path is a real management action considered in this decision, and that any pruned path is correctly marked unavailable.</span>
                </label>
                <button
                  class="analysis-confirm-button"
                  type="button"
                  :disabled="isDevReplay || !actionsValid || !actionConfirmationAccepted || confirmingActions"
                  @click="confirmCurrentActions"
                >
                  {{ confirmingActions ? 'Confirming actions…' : 'Confirm management actions' }}
                </button>
              </template>
              <div v-else class="actions-confirmed-note">✓ Confirmed by {{ actionConfirmation.confirmed_by || 'decision owner' }}</div>
            </section>

            <template v-if="decisionAnalysis.status === 'calculated'">
              <div class="analysis-result-grid">
                <div class="analysis-recommendation">
                  <span>DETERMINISTIC RECOMMENDATION</span>
                  <strong>{{ deterministicActionLabel }}</strong>
                  <small>Shown beside the qualitative recommendation; it does not silently replace it.</small>
                </div>
                <div class="analysis-metric">
                  <span>EVPI</span>
                  <strong>{{ formatDecisionMetric(decisionAnalysis.evpi) }}</strong>
                  <small>{{ decisionModel?.consequence_unit || 'confirmed utility units' }}</small>
                </div>
                <div class="analysis-metric">
                  <span>TOP EVPPI</span>
                  <strong>{{ topEvppi ? formatDecisionMetric(topEvppi.value) : '—' }}</strong>
                  <small>{{ topEvppi?.label || 'No decision-changing variable' }}</small>
                </div>
              </div>
              <div class="analysis-action-table">
                <div v-for="row in expectedUtilityRows" :key="row.id" class="analysis-action-row">
                  <span>{{ row.label }}</span>
                  <span>Expected utility <strong>{{ formatDecisionMetric(row.utility) }}</strong></span>
                  <span>Expected regret <strong>{{ formatDecisionMetric(row.regret) }}</strong></span>
                </div>
              </div>
              <div class="analysis-footer-row">
                <span>MODEL / {{ shortModelHash }} · SEED / {{ decisionAnalysis.seed }} · SAMPLES / {{ decisionAnalysis.sample_count }}</span>
                <button class="text-button" type="button" :disabled="isDevReplay || calculatingAnalysis" @click="recalculateDecisionAnalysis">
                  {{ calculatingAnalysis ? 'Calculating…' : 'Recalculate confirmed model' }}
                </button>
              </div>
            </template>

            <template v-else-if="decisionAnalysisWaived">
              <div class="qualitative-approved-card">
                <span>✓ QUALITATIVE METHOD APPROVED</span>
                <strong>No numeric comparison is claimed.</strong>
                <p>The decision owner finalized the evidence-backed recommendation without expected-utility, probability, EVPI, or EVPPI claims.</p>
              </div>
            </template>

            <template v-else>
              <p class="analysis-unavailable">Decision analysis unavailable until actions, consequences, utilities, and distributions are confirmed.</p>
              <div class="confirmation-checklist">
                <span>Available actions</span>
                <span>Consequence unit</span>
                <span>Probability distributions</span>
                <span>Utility model</span>
              </div>
              <details v-if="decisionModelProposal" class="model-review">
                <summary>Review the proposed decision model</summary>
                <div class="model-review-body">
                  <div class="model-review-grid">
                    <div>
                      <span>ACTIONS</span>
                      <strong v-for="action in proposedModel.actions || []" :key="action.id">{{ action.label }}</strong>
                    </div>
                    <div>
                      <span>UNCERTAIN VARIABLES</span>
                      <strong v-for="variable in proposedModel.uncertain_variables || []" :key="variable.id">
                        {{ variable.label }} · {{ distributionSummary(variable.distribution) }}
                      </strong>
                    </div>
                    <div>
                      <span>CONSEQUENCE UNIT</span>
                      <strong>{{ proposedModel.consequence_unit || 'Not supplied' }}</strong>
                    </div>
                    <div>
                      <span>UTILITY MODEL</span>
                      <strong>{{ proposedModel.utility_model?.type || 'Not supplied' }} · {{ proposedModel.utility_model?.risk_attitude || 'Not supplied' }}</strong>
                    </div>
                  </div>
                  <div class="model-confirmations">
                    <label><input v-model="modelConfirmations.actions" type="checkbox" :disabled="isDevReplay" /> I confirm every listed action is actually available.</label>
                    <label><input v-model="modelConfirmations.consequenceUnit" type="checkbox" :disabled="isDevReplay" /> I confirm the shared consequence and utility unit.</label>
                    <label><input v-model="modelConfirmations.distributions" type="checkbox" :disabled="isDevReplay" /> I confirm every uncertain variable and distribution.</label>
                    <label><input v-model="modelConfirmations.utility" type="checkbox" :disabled="isDevReplay" /> I confirm the payoff definitions and risk-neutral utility model.</label>
                  </div>
                  <button class="analysis-confirm-button" type="button" :disabled="isDevReplay || !allModelConfirmations || confirmingModel" @click="confirmCurrentDecisionModel">
                    {{ confirmingModel ? 'Confirming and calculating…' : 'Confirm model and calculate' }}
                  </button>
                </div>
              </details>
              <p v-else class="model-proposal-note">No model proposal is stored yet. A proposal may describe candidate actions and distributions, but it cannot calculate anything until you review and confirm it here.</p>
              <div v-if="actionsConfirmed" class="qualitative-signoff">
                <span>OR FINALIZE WITHOUT A QUANTITATIVE MODEL</span>
                <p>Use the evidence-backed qualitative recommendation as the final decision. This records an explicit owner sign-off and makes no probability, expected-utility, EVPI, or EVPPI claim.</p>
                <label>
                  <input v-model="qualitativeSignoffAccepted" type="checkbox" :disabled="isDevReplay || waivingAnalysis" />
                  I approve the qualitative decision method and understand that no numeric comparison will be claimed.
                </label>
                <button
                  class="analysis-confirm-button"
                  type="button"
                  :disabled="isDevReplay || !qualitativeSignoffAccepted || waivingAnalysis"
                  @click="finalizeQualitativeDecision"
                >
                  {{ waivingAnalysis ? 'Finalizing decision…' : 'Finalize qualitative decision' }}
                </button>
              </div>
            </template>
          </article>
        </section>

          </div>
        </details>

        <section class="panel knowledge-growth-panel" :style="sectionStyle('knowledgeGrowth')">
          <div class="panel-heading">
            <div>
              <span class="panel-index">KNOWLEDGE GROWTH</span>
              <h2>Decision knowledge tree</h2>
              <p>Every accepted internal fact grows a new private branch and revises the paths it can change.</p>
            </div>
            <div class="tree-revision">REV {{ runState.graph_revision || 0 }} · {{ internalEvidence.length }} INTERNAL FACTS</div>
          </div>
          <div ref="knowledgeScroll" class="knowledge-scroll">
            <div class="knowledge-tree" :style="knowledgeTreeStyle">
              <div class="tree-root-node">
                <span>WHAT IF WHAT IF REPORT</span>
                <strong>{{ caseTitle }}</strong>
                <small>{{ claims.length }} evidence claims</small>
              </div>
              <div class="tree-trunk"></div>
              <div class="tree-paths">
                <div v-for="hypothesis in hypotheses" :key="hypothesis.hypothesis_id" class="tree-path-node" :class="branchTone(hypothesis)">
                  <span>{{ String(hypothesis.status || 'active').toUpperCase() }}</span>
                  <strong>{{ truncate(hypothesis.label, 48) }}</strong>
                  <small>{{ formatScore(hypothesis.support_score) }} support</small>
                </div>
              </div>
              <div class="tree-growth-line"></div>
              <div class="tree-private-branches" :key="runState.graph_revision">
                <div
                  v-for="(evidence, index) in internalEvidence"
                  :key="evidence.evidence_id"
                  class="tree-evidence-node"
                  :class="{
                    newest: index === internalEvidence.length - 1,
                    insufficient: evidence.decision_usable === false
                  }"
                >
                  <span>{{ evidence.decision_usable === false ? 'CLARIFICATION NEEDED' : `PRIVATE FACT ${String(index + 1).padStart(2, '0')}` }}</span>
                  <strong>{{ questionLabel(evidence.question_id) }}</strong>
                  <small>{{ evidence.decision_usable === false ? 'Saved, but not applied to the decision' : String(evidence.interpretation || 'recorded').replaceAll('_', ' ') }}</small>
                </div>
                <div v-if="!internalEvidence.length" class="tree-empty-node">
                  <span>＋</span>
                  <strong>The tree will widen here</strong>
                  <small>Answer a material internal question to grow the first private branch.</small>
                </div>
              </div>
            </div>
          </div>
        </section>

        <div class="workspace-grid" :style="sectionStyle('knowledgeGrowth')">
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
                  <article v-for="claim in visibleClaims" :key="claim.claim_id" class="evidence-item">
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
                    <span v-else class="no-source">
                      {{ claim.kind === 'simulated_stakeholder_reaction' || claim.kind === 'simulation_derived_fact'
                        ? 'Simulation output · not a verified fact or direct quotation'
                        : 'No external citation · generated interpretation' }}
                    </span>
                  </article>
                  <div v-if="!claims.length" class="empty-panel compact">No claims available.</div>
                  <div v-else-if="claims.length > 12" class="disclosure-actions">
                    <button class="disclosure-button" type="button" @click="toggleEvidence">
                      {{ evidenceExpanded ? 'Show summary only' : `Show ${Math.min(12, hiddenClaimCount)} more claims` }}
                    </button>
                    <span>{{ visibleClaims.length }} of {{ claims.length }}</span>
                  </div>
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
                  <article v-for="(contradiction, index) in visibleContradictions" :key="contradiction.contradiction_id || index" class="contradiction-item">
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
                  <p v-if="contradictions.length > visibleContradictions.length" class="preview-note">
                    Showing the four highest-priority conflicts. {{ contradictions.length - visibleContradictions.length }} remain in the audit record.
                  </p>
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

          <aside id="internal-input-panel" class="question-panel panel">
            <div class="question-panel-header">
              <div>
                <span class="panel-index inverse">NEXT BEST QUESTION</span>
                <h2>Internal questions</h2>
                <p>Up to four questions, ranked by expected ability to change the recommendation.</p>
              </div>
              <div class="question-header-actions">
                <div class="queue-count">{{ openQuestions.length }} open</div>
                <button
                  v-if="!stopEvaluation.should_stop && !isDemoBuild"
                  class="add-question-button"
                  type="button"
                  :disabled="isDevReplay"
                  @click="showProposalForm = !showProposalForm"
                >
                  {{ showProposalForm ? 'Cancel' : 'Add missing question' }}
                </button>
              </div>
            </div>

            <div v-if="isDemoBuild && guidedPathChips.length" class="guided-path-strip" aria-label="Guided question path">
              <span class="guided-path-label">Guided path</span>
              <span
                v-for="chip in guidedPathChips"
                :key="chip.id"
                class="guided-path-chip"
                :class="chip.state"
              >
                <i>{{ chip.state === 'answered' ? '✓' : chip.state === 'current' ? '●' : '○' }}</i>
                Q{{ chip.index }} · {{ chip.label }}
              </span>
            </div>

            <form v-if="showProposalForm && !isDemoBuild" class="proposal-form" @submit.prevent="submitQuestionProposal">
              <div>
                <span class="proposal-kicker">USER-PROPOSED INFORMATION</span>
                <h3>What private question is the engine missing?</h3>
                <p>It will be ranked for decision impact. If the four-question budget is full, an accepted proposal replaces the lowest-priority unanswered question.</p>
              </div>
              <label>
                Decision area
                <select v-model="proposalForm.category" :disabled="isDevReplay" required>
                  <option v-for="option in proposalCategories" :key="option.value" :value="option.value">{{ option.label }}</option>
                </select>
              </label>
              <label class="proposal-question-field">
                Internal question
                <textarea v-model="proposalForm.question" :disabled="isDevReplay" maxlength="320" rows="3" placeholder="What internal fact could materially change this decision?" required></textarea>
              </label>
              <label>
                Best owner
                <input v-model="proposalForm.owner_hint" :disabled="isDevReplay" maxlength="200" placeholder="Team or role" />
              </label>
              <button class="proposal-submit" type="submit" :disabled="isDevReplay || proposingQuestion || !proposalForm.question.trim()">
                {{ proposingQuestion ? 'Evaluating priority…' : 'Evaluate and add' }}
              </button>
            </form>

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
                <span class="queue-copy">
                  <small v-if="question.origin === 'user_proposed'">USER PROPOSED</small>
                  {{ question.question }}
                </span>
                <span class="queue-score">{{ formatScore(question.question_priority_score) }}</span>
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
                <span>Question Priority Score</span>
                <strong>{{ formatScore(selectedQuestion.question_priority_score) }}</strong>
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
                  <span v-for="id in selectedQuestion.affected_hypothesis_ids || []" :key="id">{{ truncate(hypothesisName(id), 52) }}</span>
                </div>
              </div>

              <div v-if="selectedQuestionRetainedEvidence" class="clarification-card" role="status">
                <span>CLARIFICATION NEEDED</span>
                <strong>The previous answer was saved but did not resolve this question.</strong>
                <p>{{ retainedEvidenceExplanation }}</p>
              </div>

              <div
                v-if="!stopEvaluation.should_stop && selectedQuestion.status === 'requested' && demoAnswerChoices.length"
                class="answer-choices"
              >
                <span class="answer-choices-label">Select the internal fact to inject</span>
                <button
                  v-for="(option, index) in demoAnswerChoices"
                  :key="option.title"
                  type="button"
                  class="answer-choice"
                  :disabled="submittingAnswer || forkingRun"
                  @click="chooseDemoAnswer(option)"
                >
                  <span class="answer-choice-index">{{ String.fromCharCode(65 + index) }}</span>
                  <span class="answer-choice-body">
                    <strong>{{ option.title }}</strong>
                    <small>{{ option.text }}</small>
                    <em v-if="option.consequence" class="answer-choice-consequence">{{ option.consequence }}</em>
                  </span>
                  <span class="answer-choice-arrow">→</span>
                </button>
                <p class="privacy-note">{{ submittingAnswer ? 'Injecting evidence and updating decision paths…' : 'Pick one — it is recorded as confidential internal evidence and every branch rebalances.' }}</p>
              </div>
              <form
                v-else-if="!stopEvaluation.should_stop && selectedQuestion.status === 'requested'"
                class="answer-form"
                @submit.prevent="submitAnswer"
              >
                <label>
                  Internal answer
                  <textarea
                    v-model="answerForm.answer"
                    :disabled="isDevReplay"
                    rows="5"
                    placeholder="Enter the private fact, decision constraint, or verified internal answer…"
                    required
                  ></textarea>
                </label>
                <div class="answer-form-row">
                  <label>
                    Submitted by
                    <input v-model="answerForm.submitted_by" :disabled="isDevReplay" type="text" placeholder="Role or team" />
                  </label>
                  <label>
                    Answer clarity
                    <select v-model.number="answerForm.confidence" :disabled="isDevReplay">
                      <option :value="0.6">Medium</option>
                      <option :value="0.8">High</option>
                      <option :value="1">Verified</option>
                    </select>
                  </label>
                </div>
                <label class="privacy-check">
                  <input v-model="answerForm.confidential" type="checkbox" :disabled="isDevReplay" />
                  <span>Mark as confidential internal evidence</span>
                </label>
                <button class="answer-button" type="submit" :disabled="isDevReplay || submittingAnswer || forkingRun || !answerForm.answer.trim()">
                  <span>{{ forkingRun ? 'Creating private run…' : submittingAnswer ? 'Updating decision…' : 'Submit evidence and update branches' }}</span>
                  <span>→</span>
                </button>
                <p class="privacy-note">This answer stays in the WHAT IF WHAT IF decision workflow and is not sent back into external research. Answer clarity only controls qualitative question resolution; it never becomes a probability or Bayesian likelihood.</p>
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

        <section class="deliverables-grid" :style="sectionStyle('deliverables')">
          <article class="panel memo-panel">
            <div class="panel-heading">
              <div>
                <span class="panel-index">04</span>
                <h2>Executive decision memo</h2>
                <p>Recommendation, evidence used, rejected alternatives, uncertainty, and stop reason.</p>
              </div>
              <button class="secondary-button" type="button" :disabled="!briefAvailable" @click="downloadMemo">{{ briefExportLabel }}</button>
              <button
                v-if="report.status === 'final' && runState.core_lineage?.initial_report_id"
                class="primary-button"
                type="button"
                @click="router.push({ name: 'Interaction', params: { reportId: runState.core_lineage.initial_report_id } })"
              >
                Optional interaction after final report
              </button>
            </div>
            <div
              v-if="report.markdown"
              class="memo-content"
              :class="{ expanded: memoExpanded }"
              v-html="renderMarkdown(report.markdown)"
            ></div>
            <button v-if="report.markdown" class="memo-toggle" type="button" @click="memoExpanded = !memoExpanded">
              {{ memoExpanded ? 'Collapse memo' : 'Read full memo' }}
            </button>
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

        <footer class="decision-footer" :style="sectionStyle('footer')">
          <span>INGESTION / {{ researchStatusMessage.toUpperCase() }}</span>
          <span>MODE / {{ String(tokenUsage.processing_mode || 'deterministic').toUpperCase() }}</span>
          <span>TOKENS / {{ tokenUsage.total_tokens || 0 }}</span>
          <span v-if="tokenUsage.notes">{{ tokenUsageNote }}</span>
        </footer>
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
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BrandLockup from '../components/BrandLockup.vue'
import {
  assignExecutionOwners,
  confirmDecisionActions,
  confirmDecisionModel,
  evaluateDecisionAnalysis,
  evaluateDecisionStop,
  forkDecisionRun,
  getCoreRefinement,
  getDecisionRun,
  proposeInternalQuestion,
  submitInternalAnswer,
  waiveQuantitativeDecisionAnalysis
} from '../api/v2'
import { renderMarkdown, sanitizeMarkdownUrl } from '../utils/markdown'
import { summarizeCaseTitle } from '../utils/caseTitle'
import {
  branchTone,
  evidencePosture,
  formatDelta,
  formatScore,
  hypothesisDelta,
  looksLikeExecutableAction,
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
const evidenceLimit = ref(12)
const memoExpanded = ref(false)
const decisionRecordOpen = ref(false)
const showProposalForm = ref(false)
const proposingQuestion = ref(false)
const confirmingModel = ref(false)
const calculatingAnalysis = ref(false)
const confirmingActions = ref(false)
const actionConfirmationAccepted = ref(false)
const qualitativeSignoffAccepted = ref(false)
const waivingAnalysis = ref(false)
const savingExecutionOwners = ref(false)
const knowledgeScroll = ref(null)
const forkingRun = ref(false)
let forkPromise = null
let skipNextRouteLoad = false

const answerForm = reactive({
  answer: '',
  submitted_by: '',
  confidential: true,
  confidence: 0.8
})
const proposalForm = reactive({
  question: '',
  category: 'strategic_success',
  owner_hint: ''
})
const executionOwnerForm = reactive({
  VALIDATE: '',
  GATE: ''
})
const modelConfirmations = reactive({
  actions: false,
  consequenceUnit: false,
  distributions: false,
  utility: false
})
const proposalCategories = [
  { value: 'strategic_success', label: 'Success threshold' },
  { value: 'constraints', label: 'Hard constraint' },
  { value: 'financial_capacity', label: 'Budget and economics' },
  { value: 'execution_capacity', label: 'Execution capacity' },
  { value: 'risk_tolerance', label: 'Risk tolerance' },
  { value: 'timing', label: 'Timing and deadline' }
]

const reportId = computed(() => String(route.params.reportId || ''))
const isDevReplay = computed(() => route.query.replay === '1')
// Demo builds hoist the block the user must act on next above the fold and
// swap a handful of copy/interaction details for a game-tutorial feel. This
// flag is resolved at build time, so the branches it guards are dead code
// (and any demo-only imports/strings are tree-shaken) in a normal build.
const isDemoBuild = import.meta.env.VITE_DEMO_MODE === 'true'
const runId = computed(() => String(route.params.runId || runState.value?.run_id || ''))
const routeIdentity = computed(() => reportId.value || String(route.params.runId || ''))
const shortRunId = computed(() => runId.value ? `${runId.value.slice(0, 9)}${runId.value.length > 9 ? '…' : ''}` : '—')
const claims = computed(() => runState.value?.claims || [])
const visibleClaims = computed(() => claims.value.slice(0, evidenceLimit.value))
const hiddenClaimCount = computed(() => Math.max(0, claims.value.length - visibleClaims.value.length))
const evidenceExpanded = computed(() => evidenceLimit.value >= claims.value.length)
const assumptions = computed(() => runState.value?.assumptions || [])
const contradictions = computed(() => runState.value?.contradictions || [])
const visibleContradictions = computed(() => contradictions.value.slice(0, 4))
const hypotheses = computed(() => runState.value?.hypotheses || [])
const MAX_INTERNAL_QUESTIONS = 4
const questions = computed(() => [...(runState.value?.internal_questions || [])]
  .sort((a, b) => numericValue(a.rank, 999) - numericValue(b.rank, 999))
  .slice(0, MAX_INTERNAL_QUESTIONS))
const internalEvidence = computed(() => runState.value?.internal_evidence || runState.value?.internal_answers || [])
const decisionImpacts = computed(() => runState.value?.decision_impacts || [])
const stopEvaluation = computed(() => runState.value?.stop_evaluation || {})
const auditTrail = computed(() => runState.value?.audit_trail || runState.value?.audit_events || [])
const report = computed(() => runState.value?.report || runState.value?.decision_memo || {})
const tokenUsage = computed(() => runState.value?.token_usage || {})
const decisionAnalysis = computed(() => runState.value?.decision_analysis_result || {})
const decisionModelProposal = computed(() => runState.value?.decision_model_proposal || null)
const proposedModel = computed(() => decisionModelProposal.value?.model || {})
const decisionModel = computed(() => runState.value?.decision_model || null)
const actionConfirmation = computed(() => runState.value?.action_confirmation || {})
const decisionCompletion = computed(() => runState.value?.decision_completion || {})
const executionPlan = computed(() => runState.value?.execution_plan || {})
const actionPlan = computed(() => executionPlan.value.actions || [])
const executionFacts = computed(() => executionPlan.value.facts || [])
const executionFactsById = computed(() => new Map(
  executionFacts.value.map(item => [item.fact_id, item])
))
const executionHardFailures = computed(() => executionPlan.value.executability?.hard_failures || [])
const executionOwnerGaps = computed(() => executionHardFailures.value.flatMap((failure) => {
  if (!/replace placeholder ownership/i.test(failure)) return []
  const actionId = String(failure).match(/^(A-\d+)/)?.[1]
  const action = actionPlan.value.find(item => item.action_id === actionId)
  if (!action || !['VALIDATE', 'GATE'].includes(action.action_type)) return []
  return [{
    actionId,
    actionType: action.action_type,
    fieldLabel: action.action_type === 'VALIDATE' ? 'Validation owner' : 'Final expansion approver',
    blockerTitle: action.action_type === 'VALIDATE' ? 'Assign the validation owner' : 'Assign the final expansion approver',
    placeholder: action.action_type === 'VALIDATE'
      ? 'Named analytics or validation leader'
      : 'Named executive or finance approver',
    currentOwner: action.owner
  }]
}))
const executabilityScore = computed(() => numericValue(executionPlan.value.executability?.score))
const evidenceActionCoverage = computed(() => numericValue(executionPlan.value.coverage?.coverage_percent))
const internalEvidenceComplete = computed(() => decisionCompletion.value.internal_evidence_complete ?? Boolean(stopEvaluation.value.should_stop))
const actionsValid = computed(() => decisionCompletion.value.actions_valid ?? (
  hypotheses.value.length > 0 && hypotheses.value.every(item => looksLikeExecutableAction(item.label))
))
const actionsConfirmed = computed(() => decisionCompletion.value.actions_confirmed ?? actionConfirmation.value.status === 'confirmed')
const decisionAnalysisWaived = computed(() => decisionCompletion.value.decision_model_waived ?? (
  runState.value?.decision_analysis_waiver?.status === 'confirmed'
))
const decisionModelComplete = computed(() => decisionCompletion.value.decision_model_complete ?? decisionAnalysis.value.status === 'calculated')
const decisionModelActionsAligned = computed(() => decisionCompletion.value.decision_model_actions_aligned ?? true)
const executionPlanComplete = computed(() => decisionCompletion.value.execution_plan_complete ?? Boolean(executionPlan.value.ready))
const ownerOnlyExecutionBlock = computed(() => (
  decisionModelComplete.value
  && !executionPlanComplete.value
  && executionHardFailures.value.length > 0
  && executionOwnerGaps.value.length === executionHardFailures.value.length
))
const executionGapMessages = computed(() => ownerOnlyExecutionBlock.value
  ? executionOwnerGaps.value.map(gap => gap.blockerTitle)
  : executionHardFailures.value)
const executionOwnerFormComplete = computed(() => executionOwnerGaps.value.every(
  gap => String(executionOwnerForm[gap.actionType] || '').trim().length > 0
))
const decisionAnalysisHeading = computed(() => {
  if (decisionAnalysis.value.status === 'calculated') return 'Confirmed model result'
  if (decisionAnalysisWaived.value) return 'Qualitative decision approved'
  return 'Choose the decision method'
})
const decisionAnalysisStateLabel = computed(() => {
  if (decisionAnalysis.value.status === 'calculated') {
    return String(decisionAnalysis.value.method || 'calculated').replaceAll('_', ' ')
  }
  return decisionAnalysisWaived.value ? 'qualitative approval' : 'approval required'
})
const briefAvailable = computed(() => Boolean(report.value.markdown))
const briefDownloadLabel = computed(() => decisionReady.value ? 'Download final brief' : 'Download current brief')
const briefExportLabel = computed(() => decisionReady.value ? 'Export final decision brief' : 'Export current decision brief')
const approvedActions = computed(() => decisionModel.value?.actions || [])
const deterministicActionLabel = computed(() => {
  const actionId = decisionAnalysis.value.recommended_action
  return approvedActions.value.find(action => action.id === actionId)?.label || actionId || 'Unavailable'
})
const expectedUtilityRows = computed(() => {
  const utilities = decisionAnalysis.value.expected_utility_by_action || {}
  const regrets = decisionAnalysis.value.expected_regret_by_action || {}
  return Object.entries(utilities).map(([id, utility]) => ({
    id,
    label: approvedActions.value.find(action => action.id === id)?.label || id,
    utility,
    regret: regrets[id]
  }))
})
const topEvppi = computed(() => {
  const values = decisionAnalysis.value.evppi_by_variable || {}
  const variables = decisionModel.value?.uncertain_variables || []
  const ranked = Object.entries(values).sort((a, b) => numericValue(b[1]) - numericValue(a[1]))
  if (!ranked.length) return null
  const [id, value] = ranked[0]
  return {
    id,
    value,
    label: variables.find(variable => variable.id === id)?.label || id
  }
})
const shortModelHash = computed(() => {
  const hash = String(decisionAnalysis.value.model_hash || '')
  return hash ? `${hash.slice(0, 12)}…` : '—'
})
const allModelConfirmations = computed(() => Object.values(modelConfirmations).every(Boolean))
const fullRecommendation = computed(() => plainText(report.value.recommendation || leadingHypothesis.value?.label || 'Recommendation pending'))
const recommendationHeadline = computed(() => {
  const recommendation = fullRecommendation.value
    .replace(/^Working recommendation:\s*/i, '')
    .split(/(?<=[.!?])\s+/)[0]
  return truncate(recommendation, 150)
})
const researchStatusLabel = computed(() => {
  if (decisionReady.value) return 'FINAL APPROVAL READY'
  if (internalEvidenceComplete.value) return 'INTERNAL FACTS COMPLETE'
  return `INTERNAL EVIDENCE · ${openQuestions.value.length} FACTS LEFT`
})
const researchStatusMessage = computed(() => String(
  runState.value?.ingestion_status || 'WHAT IF WHAT IF report analyzed; internal facts ranked by question priority.'
)
  .replace(/^Deep Research imported and analyzed\.?$/i, 'Completed WHAT IF WHAT IF report imported and analyzed.')
  .replace(/MiroFish/gi, 'WHAT IF WHAT IF'))
const tokenUsageNote = computed(() => String(tokenUsage.value?.notes || '')
  .replace(
    /Deep Research is treated as the upstream evidence provider/i,
    'The completed WHAT IF WHAT IF report is reused as the evidence base'
  ))
const fullDecisionQuestion = computed(() => plainText(runState.value?.question || ''))
const fullCaseTitle = computed(() => plainText(
  runState.value?.case_title || runState.value?.project_name || fullDecisionQuestion.value || 'Decision refinement'
))
const caseTitle = computed(() => summarizeCaseTitle(fullCaseTitle.value, fullDecisionQuestion.value))
const knowledgeTreeStyle = computed(() => ({
  '--tree-width': `${1020 + internalEvidence.value.length * 190}px`
}))
const selectedCitationUrl = computed(() => sanitizeMarkdownUrl(selectedCitation.value?.url || ''))

const sortedQuestions = computed(() => [...questions.value].sort((a, b) => {
  const aAnswered = a.status === 'answered' ? 1 : 0
  const bAnswered = b.status === 'answered' ? 1 : 0
  if (aAnswered !== bAnswered) return aAnswered - bAnswered
  const rankDifference = numericValue(a.rank, 999) - numericValue(b.rank, 999)
  if (rankDifference !== 0) return rankDifference
  return numericValue(b.question_priority_score) - numericValue(a.question_priority_score)
}))
const openQuestions = computed(() => {
  if (stopEvaluation.value.should_stop) return []
  return sortedQuestions.value.filter(question => !['answered', 'deferred', 'skipped', 'closed'].includes(question.status))
})
const selectedQuestion = computed(() => sortedQuestions.value.find(question => question.question_id === selectedQuestionId.value) || openQuestions.value[0] || sortedQuestions.value[0] || null)
const selectedQuestionRetainedEvidence = computed(() => [...internalEvidence.value]
  .reverse()
  .find(evidence => (
    evidence.question_id === selectedQuestion.value?.question_id
    && evidence.decision_usable === false
    && !evidence.retracted
  )) || null)
const retainedEvidenceExplanation = computed(() => {
  const evidence = selectedQuestionRetainedEvidence.value
  if (!evidence) return ''
  if (evidence.question_relevant === false) {
    return 'State the policy, approval, constraint, threshold, or capacity fact that directly answers the question. The same question remains open until that connection is explicit.'
  }
  if (numericValue(evidence.confidence) < 0.6) {
    return 'Increase the answer clarity or provide a verified internal fact. Low-clarity evidence is retained without moving the decision branches.'
  }
  return 'Clarify the answer with a concrete decision fact. Uncertain evidence is retained without moving the decision branches.'
})
const leadingHypothesis = computed(() => {
  const leadingId = stopEvaluation.value.leading_hypothesis_id
  return hypotheses.value.find(item => item.hypothesis_id === leadingId)
    || hypotheses.value.filter(item => item.status !== 'pruned').sort((a, b) => numericValue(b.support_score) - numericValue(a.support_score))[0]
    || null
})
const recommendedAction = computed(() => {
  if (decisionAnalysis.value.status === 'calculated' && deterministicActionLabel.value !== 'Unavailable') {
    return plainText(deterministicActionLabel.value)
  }
  return plainText(leadingHypothesis.value?.label || recommendationHeadline.value || '')
})
const actionIsExecutable = computed(() => looksLikeExecutableAction(recommendedAction.value))
const isFinalReport = computed(() => report.value.status === 'final')
const sourcedClaimCount = computed(() => claims.value.filter(claim => claim.citations?.length).length)
const openContradictions = computed(() => contradictions.value.filter(item => {
  if (typeof item === 'string') return true
  return !['resolved', 'closed', 'dismissed'].includes(String(item.status || 'open').toLowerCase())
}))
const decisionBlockers = computed(() => {
  const blockers = []
  if (!actionsValid.value || !actionIsExecutable.value) {
    blockers.push({
      status: 'REQUIRED',
      title: 'Reconstruct mutually exclusive, executable management actions',
      owner: 'Decision owner'
    })
  }
  for (const question of openQuestions.value) {
    blockers.push({
      status: 'OPEN',
      title: String(question.question || 'Resolve the remaining approval condition').replace(/\?+$/, ''),
      owner: question.owner_hint || 'Decision owner'
    })
  }
  if (internalEvidenceComplete.value && actionsValid.value && !actionsConfirmed.value) {
    blockers.push({
      status: 'CONFIRM',
      title: 'Confirm that every scored path is an action management can actually take',
      owner: 'Decision owner'
    })
  }
  if (actionsConfirmed.value && !decisionModelComplete.value) {
    blockers.push({
      status: 'METHOD',
      title: 'Approve a quantitative model or explicitly finalize the qualitative decision',
      owner: 'Decision owner'
    })
  }
  if (decisionModelComplete.value && !decisionModelActionsAligned.value) {
    blockers.push({
      status: 'ALIGN',
      title: 'Align the calculated model actions with the confirmed management action set',
      owner: 'Decision owner'
    })
  }
  if (decisionModelComplete.value && !executionPlanComplete.value) {
    for (const failure of executionHardFailures.value.slice(0, 2)) {
      const ownerGap = executionOwnerGaps.value.find(gap => failure.startsWith(gap.actionId))
      blockers.push({
        status: 'EXECUTION',
        title: ownerGap?.blockerTitle || failure,
        owner: ownerGap?.currentOwner || 'Affected execution stage'
      })
    }
  }
  for (const contradiction of openContradictions.value.filter(item => {
    const severity = String(item?.severity || '').toLowerCase()
    return severity === 'high' || severity === 'critical'
  }).slice(0, 2)) {
    blockers.push({
      status: 'REVIEW',
      title: contradictionText(contradiction),
      owner: 'Strategy & risk'
    })
  }
  return blockers
})
const decisionReady = computed(() => decisionCompletion.value.final_approval_ready ?? (
  isFinalReport.value && actionsConfirmed.value && decisionModelComplete.value && executionPlanComplete.value && decisionBlockers.value.length === 0
))
const decisionStatusLabel = computed(() => {
  if (decisionReady.value) return 'DECISION READY'
  if (internalEvidenceComplete.value) return 'EVIDENCE REFINEMENT COMPLETE · DECISION BLOCKED'
  return 'DECISION IN PROGRESS'
})
const decisionStatusHeadline = computed(() => {
  if (decisionReady.value) return 'Ready to act'
  if (internalEvidenceComplete.value) return 'Decision blocked'
  return 'Approval pending'
})
const outcomePhaseLabel = computed(() => {
  if (decisionReady.value) return 'FINAL APPROVAL OUTCOME'
  if (internalEvidenceComplete.value && !actionsConfirmed.value) return 'ACTION CONFIRMATION REQUIRED'
  if (actionsConfirmed.value && !decisionModelComplete.value) return 'DECISION METHOD REQUIRED'
  if (decisionModelComplete.value && !executionPlanComplete.value) return 'EXECUTION PLAN INCOMPLETE'
  if (decisionModelComplete.value && decisionBlockers.value.length) return 'FINAL REVIEW REQUIRED'
  return 'ITERATIVE DECISION REFINEMENT'
})
const decisionRequest = computed(() => truncate(fullDecisionQuestion.value || caseTitle.value, 240))
const decisionHeadline = computed(() => {
  if (!actionsValid.value || !actionIsExecutable.value) return 'Reconstruct the action set before committing resources'
  if (internalEvidenceComplete.value && !actionsConfirmed.value) return 'Internal evidence complete. Confirm the management actions.'
  if (actionsConfirmed.value && !decisionModelComplete.value) return 'Actions confirmed. Choose the final decision method.'
  if (ownerOnlyExecutionBlock.value) return 'Execution plan needs two accountable owners'
  if (decisionModelComplete.value && !executionPlanComplete.value) return 'Decision selected. Close the execution-plan gaps.'
  return recommendedAction.value
})
const recommendationBasis = computed(() => {
  if (decisionAnalysis.value.status === 'calculated') return 'Human-confirmed decision model'
  if (decisionAnalysisWaived.value) return 'Owner-approved qualitative judgment'
  if (actionsConfirmed.value) return 'Confirmed actions · decision method pending'
  if (internalEvidenceComplete.value) return 'Internal evidence complete · actions unconfirmed'
  return 'Working simulation signal'
})
const readinessExplanation = computed(() => {
  if (decisionReady.value) return 'The recommendation is final, executable, and has no open approval gate in this run.'
  if (!actionsValid.value || !actionIsExecutable.value) return 'At least one path is a stakeholder, observation, or prompt fragment—not an action management can approve.'
  if (internalEvidenceComplete.value && !actionsConfirmed.value) return 'Internal questions are resolved, but management has not confirmed the available action set.'
  if (decisionBlockers.value.length) return `${decisionBlockers.value.length} explicit condition${decisionBlockers.value.length === 1 ? '' : 's'} must be resolved before full commitment.`
  return 'The direction is clear, but the refinement loop has not declared the decision final.'
})
const decisionSummary = computed(() => {
  if (!actionsValid.value || !actionIsExecutable.value) {
    return 'The simulation contains useful evidence, but its leading path is not yet a selectable management action. Confirm the alternatives, then return for a final recommendation.'
  }
  const explanation = plainText(leadingHypothesis.value?.description || leadingHypothesis.value?.rationale || '')
  if (decisionReady.value) {
    return explanation
      ? `Proceed with this path. ${truncate(explanation, 260)}`
      : 'Proceed with this path through staged commitments, named ownership, and explicit pause and reversal triggers.'
  }
  if (internalEvidenceComplete.value && !actionsConfirmed.value) {
    return `Public simulation and private fact collection are complete. The current leading action signal is “${recommendedAction.value},” but it cannot become a recommendation until management confirms the full action set.`
  }
  if (actionsConfirmed.value && !decisionModelComplete.value) {
    return 'The available actions are confirmed. Choose either a reviewed quantitative model or an explicit qualitative sign-off; the system will not invent numeric assumptions.'
  }
  if (ownerOnlyExecutionBlock.value) {
    return 'Assign the validation owner and final expansion approver.'
  }
  if (decisionModelComplete.value && !executionPlanComplete.value) {
    return 'The decision method is approved, but the plan still lacks a complete owner, resource boundary, measurable gate, or reversal contract. Close the execution gaps below before release.'
  }
  return `Treat this as the working direction, not a blanket commitment. Close the approval gates below before releasing the full decision.`
})
const evidencePostureLabel = computed(() => evidencePosture({
  sourcedClaims: sourcedClaimCount.value,
  openContradictions: openContradictions.value.length,
  internalEvidenceComplete: internalEvidenceComplete.value,
  isFinal: isFinalReport.value,
  actionIsExecutable: actionsValid.value && actionIsExecutable.value
}))
const executiveReasons = computed(() => {
  if (!actionIsExecutable.value) {
    return [
      'The leading path is descriptive rather than an executable action.',
      openQuestions.value.length
        ? `${openQuestions.value.length} decision-critical internal fact${openQuestions.value.length === 1 ? ' remains' : 's remain'} unresolved.`
        : 'The available alternatives still need explicit management confirmation before they can be compared.',
      'A final decision must state what to approve today, who owns it, and what would pause or reverse it.'
    ]
  }

  const supportingIds = new Set(leadingHypothesis.value?.supporting_claim_ids || [])
  const supportingClaims = claims.value
    .filter(claim => supportingIds.has(claim.claim_id) && claim.citations?.length)
    .map(claim => claim.text)
  const candidates = [
    leadingHypothesis.value?.description,
    leadingHypothesis.value?.rationale,
    ...supportingClaims
  ]
  const seen = new Set()
  return candidates
    .map(item => truncate(plainText(item), 220))
    .filter(item => {
      const key = item.toLowerCase()
      if (!item || key === recommendedAction.value.toLowerCase() || seen.has(key)) return false
      seen.add(key)
      return true
    })
    .slice(0, 3)
})
const answeredQuestionCount = computed(() => questions.value.filter(question => question.status === 'answered').length)
const inputProgressPercent = computed(() => questions.value.length
  ? Math.round((answeredQuestionCount.value / questions.value.length) * 100)
  : 0)
// Progress line shown in the condensed sticky hero bar (see heroCondensed
// below): mirrors the wording used in the full hero's demo-progress block
// while it's incomplete, then falls back to open approval gates once
// internal evidence is done.
const condensedProgressLabel = computed(() => {
  if (!internalEvidenceComplete.value) {
    return `${answeredQuestionCount.value} of ${questions.value.length} approval inputs provided`
  }
  const openGates = decisionBlockers.value.length
  return openGates
    ? `${openGates} open approval gate${openGates === 1 ? '' : 's'}`
    : 'All approval gates closed'
})
const isDemonstration = computed(() => /demo|starbucks|priority pass/i.test(
  `${runState.value?.project_name || ''} ${fullDecisionQuestion.value}`
))
const completionStages = computed(() => {
  const stages = [
    { id: 'research', label: 'Research complete', complete: decisionCompletion.value.research_complete ?? claims.value.length > 0 },
    { id: 'evidence', label: 'Internal evidence complete', complete: internalEvidenceComplete.value },
    { id: 'actions', label: 'Actions confirmed', complete: actionsConfirmed.value },
    { id: 'model', label: 'Decision method approved', complete: decisionModelComplete.value },
    { id: 'execution', label: 'Execution plan complete', complete: executionPlanComplete.value },
    { id: 'approval', label: 'Final approval ready', complete: decisionReady.value }
  ]
  const firstIncomplete = stages.findIndex(stage => !stage.complete)
  return stages.map((stage, index) => ({
    ...stage,
    index: String(index + 1).padStart(2, '0'),
    active: index === firstIncomplete
  }))
})

// Demo-only "pending block" hoisting: reorder the top-level page sections via
// flex `order` so whatever the user must act on next sits directly under the
// (sticky) completion ladder. Hero and ladder are never part of this map, so
// they always render first via the default order:0. Outside demo builds this
// map is empty and every section keeps its natural source order.
const DEMO_STAGE_SECTION_ORDER = {
  internal_evidence_refinement: ['knowledgeGrowth', 'executiveSummary', 'actionPlan', 'decisionRecord', 'deliverables'],
  action_confirmation: ['decisionRecord', 'knowledgeGrowth', 'executiveSummary', 'actionPlan', 'deliverables'],
  decision_model_completion: ['decisionRecord', 'knowledgeGrowth', 'executiveSummary', 'actionPlan', 'deliverables'],
  execution_plan_completion: ['actionPlan', 'executiveSummary', 'decisionRecord', 'knowledgeGrowth', 'deliverables'],
  final_review: ['actionPlan', 'executiveSummary', 'decisionRecord', 'knowledgeGrowth', 'deliverables'],
  final_approval_ready: ['executiveSummary', 'actionPlan', 'decisionRecord', 'knowledgeGrowth', 'deliverables']
}
const demoSectionOrderMap = computed(() => {
  if (!isDemoBuild) return {}
  const keys = DEMO_STAGE_SECTION_ORDER[decisionCompletion.value.stage] || DEMO_STAGE_SECTION_ORDER.final_approval_ready
  const map = {}
  keys.forEach((key, index) => { map[key] = index + 1 })
  map.footer = keys.length + 1
  return map
})
const sectionStyle = (key) => {
  const order = demoSectionOrderMap.value[key]
  return order === undefined ? {} : { order }
}

// The action-confirmation gate and decision-model panel live inside the
// decision-record accordion. When that block is hoisted to the top for the
// action_confirmation / decision_model_completion stages, auto-expand it once
// so the gate is visible without an extra click. This reuses the existing
// decisionRecordOpen toggle state rather than overriding the `open` binding,
// so the native <details> toggle keeps working exactly as before — the user
// can still collapse it again afterward.
const DEMO_AUTO_EXPAND_STAGES = new Set(['action_confirmation', 'decision_model_completion'])
watch(() => decisionCompletion.value.stage, (stage) => {
  if (isDemoBuild && DEMO_AUTO_EXPAND_STAGES.has(stage)) decisionRecordOpen.value = true
}, { immediate: true })

// Demo-only guided-path strip above the internal-questions list: four chips
// (one per ranked internal question) showing answered / current / upcoming.
const QUESTION_CATEGORY_LABELS = {
  constraints: 'Constraints',
  strategic_success: 'Measurable outcome',
  financial_capacity: 'Budget & capacity',
  risk_tolerance: 'Downside tolerance'
}
const guidedPathChips = computed(() => questions.value.map((question, index) => ({
  id: question.question_id || index,
  index: index + 1,
  label: QUESTION_CATEGORY_LABELS[question.category] || `Question ${index + 1}`,
  state: question.status === 'answered'
    ? 'answered'
    : question.question_id === selectedQuestion.value?.question_id
      ? 'current'
      : 'upcoming'
})))
const actionSignalKicker = computed(() => actionsValid.value
  ? 'ACTION SIGNAL · NOT A FINAL RECOMMENDATION'
  : 'IMPORTED SIMULATION SIGNAL · INVALID AS A MANAGEMENT ACTION')
const actionSignalLabel = computed(() => actionsValid.value
  ? (leadingHypothesis.value?.label || 'No leading action signal')
  : 'No valid action recommendation')
const actionSignalExplanation = computed(() => {
  if (!actionsValid.value) return 'Stakeholder names, contextual statements, and prompt fragments are excluded from management recommendations.'
  if (!actionsConfirmed.value) return 'This is the leading reconstructed action signal. Management must confirm the complete action set before it can be modeled or approved.'
  return leadingHypothesis.value?.description || 'The confirmed actions are ready for consequence modeling.'
})
const internalCollectionReason = computed(() => {
  const reason = stopEvaluation.value.reason || 'The decision engine has not recorded an internal-fact collection status yet.'
  return internalEvidenceComplete.value
    ? reason.replace(/^Stop:/i, 'Collection complete:')
    : reason.replace(/^Continue:/i, 'Continue:')
})
const primaryActionLabel = computed(() => {
  if (decisionReady.value) return 'Review final action plan'
  if (!internalEvidenceComplete.value) return 'Provide next internal input'
  if (!actionsValid.value) return 'Review invalid action set'
  if (!actionsConfirmed.value) return 'Confirm management actions'
  if (!decisionModelComplete.value) return 'Choose decision method'
  if (ownerOnlyExecutionBlock.value) return 'Assign accountable owners'
  if (!executionPlanComplete.value) return 'Resolve execution plan gaps'
  return 'Review final action plan'
})
const primaryActionDisabled = computed(() => !runState.value || (
  isDevReplay.value && !decisionReady.value
))
const completedDecisionPreview = computed(() => {
  const starbucks = /starbucks|priority pass/i.test(`${caseTitle.value} ${fullDecisionQuestion.value}`)
  if (starbucks) {
    return {
      recommendation: 'Proceed with a constrained 50-store pilot; do not expand until labor-capacity and service-time safeguards pass the first checkpoint.',
      owner: 'US Operations EVP with one named pilot operator',
      budgetGate: 'Release only the approved pilot tranche; no national rollout spend',
      kpis: 'Pickup-time p95, barista labor minutes, non-member CSAT, conversion and churn',
      trigger: 'Pause if pickup p95 or labor load breaches its limit; reverse if non-member churn remains above the agreed threshold for two reviews'
    }
  }
  return {
    recommendation: `Approve the selected action only through a constrained first tranche: ${recommendedAction.value || 'confirmed management action'}.`,
    owner: 'One named executive sponsor and operating owner',
    budgetGate: 'Release only the approved first tranche',
    kpis: 'Outcome, operating, financial, and stakeholder guardrails',
    trigger: 'Pause on a leading-indicator breach; reverse after the confirmed downside threshold is crossed'
  }
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

const responsePayload = (response) => response?.data || response || {}
const normalizeRunResponse = (response) => {
  const payload = responsePayload(response)
  const candidate = payload.run || payload.child_run || payload.run_state || payload
  return candidate?.run_id ? candidate : null
}
const responseRunId = (response) => {
  const payload = responsePayload(response)
  return payload.run_id || payload.child_run_id || payload.run?.run_id || payload.child_run?.run_id || ''
}

const ensureInternalRun = async ({ force = false } = {}) => {
  if (isDevReplay.value) throw new Error('Dev Replay is read-only.')
  const current = runState.value
  if (!current?.run_id) throw new Error('The current decision run is unavailable.')
  if (current.run_type === 'internal' || current.parent_run_id) return current
  if (!force && current.run_type !== 'public') return current
  if (forkPromise) return forkPromise

  forkPromise = (async () => {
    forkingRun.value = true
    try {
      const response = await forkDecisionRun(current.run_id)
      let child = normalizeRunResponse(response)
      const childRunId = responseRunId(response)
      if (!child && childRunId) child = normalizeRunResponse(await getDecisionRun(childRunId))
      if (!child?.run_id) throw new Error('The backend did not return the private child run.')

      runState.value = child
      chooseNextQuestion()
      if (route.name !== 'DecisionWorkspace' || String(route.params.runId || '') !== child.run_id) {
        skipNextRouteLoad = true
        await router.replace({ name: 'DecisionWorkspace', params: { runId: child.run_id } })
      }
      actionMessage.value = 'Private refinement run created. The sealed public baseline remains unchanged.'
      return child
    } catch (error) {
      // During a rolling upgrade an older backend may not expose the fork route
      // and may still accept answers directly. Preserve that compatibility only
      // for an explicitly missing endpoint; all other failures remain fail-closed.
      if (!force && [404, 405, 410].includes(error.status)) return current
      throw error
    } finally {
      forkingRun.value = false
      forkPromise = null
    }
  })()

  return forkPromise
}

const visibleEvidenceAnswer = (questionId) => {
  const evidence = evidenceForQuestion(questionId)
  if (!evidence || evidence.confidential || evidence.answer === '[REDACTED_INTERNAL_EVIDENCE]') {
    return 'Confidential internal evidence is stored locally and has been incorporated into the decision.'
  }
  return evidence.answer || 'This question has been incorporated into the decision.'
}
const questionLabel = (questionId) => truncate(
  questions.value.find(question => question.question_id === questionId)?.question || 'Internal evidence recorded',
  64
)
const formatDecisionMetric = (value) => {
  const number = Number(value)
  if (!Number.isFinite(number)) return '—'
  return new Intl.NumberFormat(undefined, {
    maximumFractionDigits: 4,
    minimumFractionDigits: 0
  }).format(number)
}
const distributionSummary = (distribution = {}) => {
  const type = String(distribution.type || 'untyped').replaceAll('_', ' ')
  const parameters = distribution.parameters || {}
  if (type === 'categorical' && parameters.probabilities) {
    return Object.entries(parameters.probabilities)
      .map(([label, value]) => `${label} ${Math.round(numericValue(value) * 100)}%`)
      .join(' · ')
  }
  if (type === 'bernoulli') {
    return `Bernoulli · true ${Math.round(numericValue(parameters.probability_true) * 100)}%`
  }
  if (type === 'normal') {
    return `Normal · μ ${formatDecisionMetric(parameters.mean)} · σ ${formatDecisionMetric(parameters.standard_deviation)}`
  }
  if (type === 'triangular') {
    return `Triangular · ${formatDecisionMetric(parameters.minimum)} / ${formatDecisionMetric(parameters.mode)} / ${formatDecisionMetric(parameters.maximum)}`
  }
  if (type === 'uniform') {
    return `Uniform · ${formatDecisionMetric(parameters.minimum)}–${formatDecisionMetric(parameters.maximum)}`
  }
  if (type === 'beta') {
    return `Beta · α ${formatDecisionMetric(parameters.alpha)} · β ${formatDecisionMetric(parameters.beta)}`
  }
  if (type === 'fixed' || type === 'deterministic') {
    return `Fixed · ${String(parameters.value ?? '—')}`
  }
  return type
}

const toggleEvidence = () => {
  evidenceLimit.value = evidenceExpanded.value
    ? 12
    : Math.min(claims.value.length, evidenceLimit.value + 12)
}

const loadRun = async () => {
  if (!routeIdentity.value) return
  loading.value = true
  loadError.value = ''
  try {
    if (isDevReplay.value && reportId.value) {
      throw new Error('Dev Replay requires a saved decision run ID; report-based initialization is disabled.')
    }
    const response = reportId.value
      ? await getCoreRefinement(reportId.value)
      : await getDecisionRun(runId.value)
    const nextState = normalizeRunResponse(response)
    if (!nextState) throw new Error('The backend returned an invalid decision state.')
    const isInitialLoad = !runState.value
    runState.value = nextState
    if (isInitialLoad) decisionRecordOpen.value = nextState.report?.status !== 'final'
    chooseNextQuestion()
  } catch (error) {
    loadError.value = error.message || 'Unable to load the decision run.'
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
  if (isDevReplay.value) return
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
    let targetRun = await ensureInternalRun()
    const payload = {
      question_id: selectedQuestion.value.question_id,
      answer: answerForm.answer.trim(),
      submitted_by: answerForm.submitted_by.trim() || undefined,
      confidential: answerForm.confidential,
      confidence: answerForm.confidence
    }
    let response
    try {
      response = await submitInternalAnswer(targetRun.run_id, payload)
    } catch (error) {
      if (!(error.needsFork || error.status === 409) || targetRun.run_type === 'internal') throw error
      targetRun = await ensureInternalRun({ force: true })
      response = await submitInternalAnswer(targetRun.run_id, payload)
    }
    const nextState = normalizeRunResponse(response)
    if (nextState) runState.value = nextState
    else await loadRun()
    const newestEvidence = nextState?.internal_evidence?.at?.(-1)
    actionMessage.value = newestEvidence?.decision_usable === false
      ? (newestEvidence?.question_relevant === false
          ? 'Evidence saved, but it did not directly answer the selected question. The question remains open for clarification.'
          : 'Evidence saved, but it was too uncertain or low-clarity to resolve the question. The question remains open.')
      : isDemoBuild
        ? 'Recorded. Your choice unlocked the next ranked question.'
        : 'Internal evidence recorded. Decision paths and stop conditions were updated.'
    answerForm.answer = ''
    chooseNextQuestion()
  } catch (error) {
    loadError.value = error.message || 'Unable to submit internal evidence.'
  } finally {
    submittingAnswer.value = false
  }
}

// Demo builds swap the free-text internal-answer form for a three-choice
// picker (game-tutorial style). The options module lives in the demo tree,
// so this dynamic import is dead code in production bundles.
const demoAnswerSets = ref(null)
if (isDemoBuild) {
  import('../demo/fixtures/answerOptions.js')
    .then(module => { demoAnswerSets.value = module })
    .catch(() => { demoAnswerSets.value = null })
}
const demoAnswerChoices = computed(() => {
  if (!demoAnswerSets.value || !selectedQuestion.value) return []
  return demoAnswerSets.value.findAnswerOptions(selectedQuestion.value.question) || []
})
const chooseDemoAnswer = async option => {
  if (submittingAnswer.value || forkingRun.value) return
  answerForm.answer = option.text
  answerForm.submitted_by = option.submitted_by || ''
  answerForm.confidence = option.confidence ?? 0.8
  answerForm.confidential = true
  await submitAnswer()
}

const submitQuestionProposal = async () => {
  if (isDevReplay.value) return
  if (!proposalForm.question.trim() || proposingQuestion.value) return
  proposingQuestion.value = true
  loadError.value = ''
  actionMessage.value = ''
  try {
    const targetRun = await ensureInternalRun()
    const response = await proposeInternalQuestion(targetRun.run_id, {
      question: proposalForm.question.trim(),
      category: proposalForm.category,
      owner_hint: proposalForm.owner_hint.trim() || 'Decision owner'
    })
    const nextState = normalizeRunResponse(response)
    if (nextState) runState.value = nextState
    proposalForm.question = ''
    proposalForm.owner_hint = ''
    showProposalForm.value = false
    chooseNextQuestion()
    actionMessage.value = 'The proposed question passed priority review and entered the bounded queue.'
  } catch (error) {
    loadError.value = error.message || 'Unable to evaluate the proposed question.'
  } finally {
    proposingQuestion.value = false
  }
}

const openDecisionRecordAt = async (targetId) => {
  decisionRecordOpen.value = true
  await nextTick()
  document.getElementById(targetId)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const handlePrimaryAction = async () => {
  if (decisionReady.value) {
    document.getElementById('action-plan')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    return
  }
  if (!internalEvidenceComplete.value) {
    // The internal-questions panel is a top-level section (not nested inside
    // the decision-record accordion), so it never needs decisionRecordOpen.
    document.getElementById('internal-input-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    return
  }
  if (!actionsConfirmed.value) {
    await openDecisionRecordAt('action-confirmation')
    return
  }
  if (decisionModelComplete.value && !executionPlanComplete.value) {
    document.getElementById(ownerOnlyExecutionBlock.value ? 'execution-owner-assignment' : 'action-plan')
      ?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    return
  }
  await openDecisionRecordAt('decision-model-review')
}

const saveExecutionOwners = async () => {
  if (isDevReplay.value || !ownerOnlyExecutionBlock.value || !executionOwnerFormComplete.value || savingExecutionOwners.value) return
  savingExecutionOwners.value = true
  loadError.value = ''
  actionMessage.value = ''
  try {
    const targetRun = await ensureInternalRun()
    const owners = Object.fromEntries(executionOwnerGaps.value.map(gap => [
      gap.actionType,
      executionOwnerForm[gap.actionType].trim()
    ]))
    const response = await assignExecutionOwners(targetRun.run_id, { owners })
    const nextState = normalizeRunResponse(response)
    if (nextState) runState.value = nextState
    else await loadRun()
    executionOwnerForm.VALIDATE = ''
    executionOwnerForm.GATE = ''
    actionMessage.value = 'Accountable owners assigned. The execution plan, memo, and approval state were recompiled without rerunning the simulation.'
    await nextTick()
    document.getElementById('action-plan')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  } catch (error) {
    loadError.value = error.message || 'Unable to assign the execution owners.'
  } finally {
    savingExecutionOwners.value = false
  }
}

const confirmCurrentActions = async () => {
  if (isDevReplay.value || !actionsValid.value || !actionConfirmationAccepted.value || confirmingActions.value) return
  confirmingActions.value = true
  loadError.value = ''
  actionMessage.value = ''
  try {
    const targetRun = await ensureInternalRun()
    const response = await confirmDecisionActions(targetRun.run_id, {
      action_ids: hypotheses.value.map(item => item.hypothesis_id),
      confirmed_by: answerForm.submitted_by.trim() || 'Decision owner'
    })
    const nextState = normalizeRunResponse(response)
    if (nextState) runState.value = nextState
    else await loadRun()
    actionConfirmationAccepted.value = false
    actionMessage.value = 'Management actions confirmed. The decision now advances to consequence and uncertainty modeling.'
  } catch (error) {
    loadError.value = error.message || 'Unable to confirm the management actions.'
  } finally {
    confirmingActions.value = false
  }
}

const confirmCurrentDecisionModel = async () => {
  if (isDevReplay.value) return
  if (!decisionModelProposal.value || !allModelConfirmations.value || confirmingModel.value) return
  confirmingModel.value = true
  loadError.value = ''
  actionMessage.value = ''
  try {
    const targetRun = await ensureInternalRun()
    const response = await confirmDecisionModel(targetRun.run_id, {
      proposal_id: decisionModelProposal.value.proposal_id,
      confirm_actions: modelConfirmations.actions,
      confirm_consequence_unit: modelConfirmations.consequenceUnit,
      confirm_distributions: modelConfirmations.distributions,
      confirm_utility_model: modelConfirmations.utility,
      seed: 0,
      sample_count: 10000
    })
    const nextState = normalizeRunResponse(response)
    if (nextState) runState.value = nextState
    else await loadRun()
    Object.keys(modelConfirmations).forEach(key => { modelConfirmations[key] = false })
    actionMessage.value = 'Decision model confirmed. Expected utility, regret, EVPI, and EVPPI were calculated locally.'
  } catch (error) {
    loadError.value = error.message || 'Unable to confirm the decision model.'
  } finally {
    confirmingModel.value = false
  }
}

const finalizeQualitativeDecision = async () => {
  if (isDevReplay.value || !qualitativeSignoffAccepted.value || waivingAnalysis.value) return
  waivingAnalysis.value = true
  loadError.value = ''
  actionMessage.value = ''
  try {
    const targetRun = await ensureInternalRun()
    const response = await waiveQuantitativeDecisionAnalysis(targetRun.run_id, {
      confirm_qualitative_decision: true,
      confirmed_by: answerForm.submitted_by.trim() || 'Decision owner',
      reason: 'The decision owner approved the evidence-backed qualitative recommendation without a quantitative utility model.'
    })
    const nextState = normalizeRunResponse(response)
    if (nextState) runState.value = nextState
    else await loadRun()
    qualitativeSignoffAccepted.value = false
    actionMessage.value = 'Qualitative decision approved. The final brief is ready with no numeric comparison claims.'
  } catch (error) {
    loadError.value = error.message || 'Unable to finalize the qualitative decision.'
  } finally {
    waivingAnalysis.value = false
  }
}

const recalculateDecisionAnalysis = async () => {
  if (isDevReplay.value) return
  if (calculatingAnalysis.value || !decisionModel.value) return
  calculatingAnalysis.value = true
  loadError.value = ''
  try {
    const response = await evaluateDecisionAnalysis(runId.value, {
      seed: decisionAnalysis.value.seed ?? 0,
      sample_count: runState.value?.decision_analysis_options?.sample_count || 10000
    })
    const nextState = normalizeRunResponse(response)
    if (nextState) runState.value = nextState
    else await loadRun()
    actionMessage.value = 'The confirmed decision model was recalculated reproducibly.'
  } catch (error) {
    loadError.value = error.message || 'Unable to recalculate decision analysis.'
  } finally {
    calculatingAnalysis.value = false
  }
}

const reevaluateStop = async () => {
  if (isDevReplay.value) return
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
    if (!briefAvailable.value) throw new Error('The decision brief is not available yet.')
    const cleanLine = value => plainText(value).replace(/\s+/g, ' ').trim()
    const briefStatus = decisionReady.value
      ? 'FINAL DECISION — APPROVED'
      : 'CURRENT DECISION BRIEF — NOT FINAL'
    const lines = [
      `# ${cleanLine(caseTitle.value)} — Executive Decision Brief`,
      '',
      `**Status:** ${briefStatus}`,
      ...(!decisionReady.value ? [
        `**Current stage:** ${decisionStatusLabel.value}`,
        '**Use:** Working decision record; open approval gates are listed below.'
      ] : []),
      `**Decision requested:** ${cleanLine(fullDecisionQuestion.value || caseTitle.value)}`,
      '',
      '## Decision',
      decisionHeadline.value,
      '',
      decisionSummary.value,
      '',
      '## Why this decision',
      ...(executiveReasons.value.length
        ? executiveReasons.value.map(reason => `- ${cleanLine(reason)}`)
        : ['- No decision-grade rationale is available yet.']),
      '',
      '## Conditions and guardrails',
      ...(decisionBlockers.value.length
        ? decisionBlockers.value.map(blocker => `- **${blocker.status}:** ${cleanLine(blocker.title)} — Owner: ${cleanLine(blocker.owner)}`)
        : ['- All ranked approval gates are closed. Use staged release, a named owner, and explicit pause and reversal triggers.']),
      '',
      '## Compiled execution plan',
      `- Executability: ${Math.round(executabilityScore.value)}/100`,
      `- Evidence-to-action coverage: ${Math.round(evidenceActionCoverage.value)}%`,
      `- Plan status: ${executionPlanComplete.value ? 'Decision-ready' : 'Execution gaps remain'}`,
      ...(executionHardFailures.value.length
        ? executionHardFailures.value.map(item => `- **Execution gap:** ${cleanLine(item)}`)
        : []),
      '',
      ...actionPlan.value.flatMap(step => [
        `### ${cleanLine(step.action_id)} · ${cleanLine(step.action_type.replace('_', ' / '))} · ${cleanLine(step.stage)}`,
        `**${cleanLine(step.title)}**`,
        `- Purpose: ${cleanLine(step.purpose)}`,
        `- Owner: ${cleanLine(step.owner)}`,
        `- Accountable executive: ${cleanLine(step.accountable_executive)}`,
        `- Deliverable: ${cleanLine(step.deliverable)}`,
        `- Timing: starts when ${cleanLine(step.start_condition)}; due ${cleanLine(step.deadline)}`,
        `- Resource boundary: ${cleanLine(step.budget_or_capacity)}`,
        '- Acceptance criteria:',
        ...step.acceptance_criteria.map(item => `  - ${cleanLine(item)}`),
        '- Dependencies:',
        ...(step.dependencies.length ? step.dependencies.map(item => `  - ${cleanLine(item)}`) : ['  - None recorded.']),
        `- Failure response: ${cleanLine(step.failure_response)}`,
        `- Evidence provenance: ${step.evidence_source_ids.join(', ') || 'Execution contract requirement'}`,
        ''
      ]),
      '',
      '## Decision record',
      `- Recommendation basis: ${recommendationBasis.value}`,
      `- Evidence posture: ${evidencePostureLabel.value} (qualitative, not a probability or confidence score)`,
      `- Open approval gates: ${decisionBlockers.value.length}`,
      `- Run: ${runId.value}`,
      ''
    ]
    const markdown = `${lines.join('\n')}\n`
    const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    const suffix = decisionReady.value ? 'final-decision-brief' : 'current-decision-brief'
    link.download = `${runState.value?.project_name || runId.value}-${suffix}.md`.replace(/[^a-z0-9._-]+/gi, '-')
    document.body.appendChild(link)
    link.click()
    link.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch (error) {
    loadError.value = error.message || 'Unable to export the memo.'
  }
}

const claimKind = (claim) => {
  if (claim.kind === 'simulated_stakeholder_reaction' || claim.kind === 'simulation_derived_fact') {
    return 'Simulated reaction · not verified fact'
  }
  const status = String(claim.provenance_status || '').toLowerCase()
  if (status.includes('source') || status.includes('cited')) return 'Sourced fact'
  if (status.includes('unsupported')) return 'Unsupported'
  return claim.kind ? String(claim.kind).replaceAll('_', ' ') : 'Interpretation'
}
const claimTone = (claim) => claim.kind === 'simulated_stakeholder_reaction' || claim.kind === 'simulation_derived_fact'
  ? 'simulated_reaction'
  : claimKind(claim).toLowerCase().replaceAll(' ', '_')
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

watch(routeIdentity, () => {
  if (skipNextRouteLoad) {
    skipNextRouteLoad = false
    return
  }
  loadRun()
})
watch(() => internalEvidence.value.length, async (nextLength, previousLength) => {
  if (nextLength <= previousLength) return
  await nextTick()
  const scroller = knowledgeScroll.value
  if (!scroller) return
  const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  const revealLatestBranch = () => {
    if (!scroller.isConnected) return
    scroller.scrollTo({ left: scroller.scrollWidth, behavior: reducedMotion ? 'auto' : 'smooth' })
  }
  revealLatestBranch()
  if (!reducedMotion) window.setTimeout(revealLatestBranch, 780)
})
onMounted(loadRun)

// Condensed sticky hero bar (see .condensed-hero-bar in <style>): the full
// outcome-hero is too tall to pin, so instead we watch it with an
// IntersectionObserver and show a slim summary bar once it scrolls out of
// view. heroRef is only populated once runState loads and the hero section
// renders, so the observer is (re)attached via a watcher rather than at
// onMounted — and torn down whenever the element changes or unmounts.
const heroRef = ref(null)
const heroCondensed = ref(false)
let heroObserver = null
function teardownHeroObserver () {
  heroObserver?.disconnect()
  heroObserver = null
}
watch(heroRef, (el) => {
  teardownHeroObserver()
  if (!el || typeof IntersectionObserver === 'undefined') {
    heroCondensed.value = false
    return
  }
  heroObserver = new IntersectionObserver(([entry]) => {
    heroCondensed.value = !entry.isIntersecting
  }, {
    threshold: 0,
    // Shrinks the effective viewport by the sticky header's height so the
    // bar appears as soon as the hero is actually hidden behind it, rather
    // than waiting until the hero clears the raw (unobstructed) viewport.
    rootMargin: '-58px 0px 0px 0px'
  })
  heroObserver.observe(el)
})
onBeforeUnmount(teardownHeroObserver)
</script>

<style scoped>
:global(body) {
  background: #ffffff;
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

.replay-readonly-banner {
  position: sticky;
  top: 58px;
  z-index: 39;
  padding: 8px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.14);
  color: #d8f4ff;
  background: #0d4a66;
  text-align: center;
  font: 700 10px/1.35 'JetBrains Mono', monospace;
  letter-spacing: 0.08em;
}

.dev-replay-readonly button:disabled,
.dev-replay-readonly input:disabled,
.dev-replay-readonly select:disabled,
.dev-replay-readonly textarea:disabled {
  cursor: not-allowed;
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
  --brand-icon-size: 36px;
  --brand-name-size: 13px;
  font-family: 'JetBrains Mono', monospace;
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
.recommendation-footer { display: flex; flex-wrap: wrap; gap: 16px; align-items: center; margin-top: 22px; color: var(--muted); font-size: 11px; line-height: 1.5; }
.report-status { display: inline-flex; align-items: center; flex: 0 0 auto; padding: 7px 14px; line-height: 1; color: white; background: var(--ink); font: 10px 'JetBrains Mono', monospace; letter-spacing: .04em; }

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
.answer-choices { margin-top: 20px; display: grid; gap: 9px; }
.answer-choices-label { color: #aaa8a1; font-size: 10px; }
.answer-choice { display: grid; grid-template-columns: 24px 1fr 16px; align-items: center; gap: 10px; padding: 12px; border: 1px solid #4a4944; background: #20201d; color: white; text-align: left; cursor: pointer; transition: border-color 140ms ease, background 140ms ease; }
.answer-choice:hover:not(:disabled) { border-color: var(--orange); background: #262521; }
.answer-choice:disabled { opacity: 0.45; cursor: wait; }
.answer-choice-index { display: inline-flex; align-items: center; justify-content: center; width: 22px; height: 22px; border: 1px solid #4a4944; color: #aaa8a1; font: 700 10px 'JetBrains Mono', monospace; }
.answer-choice:hover:not(:disabled) .answer-choice-index { border-color: var(--orange); color: var(--orange); }
.answer-choice-body { display: grid; gap: 4px; min-width: 0; }
.answer-choice-body strong { font-size: 11px; font-weight: 650; }
.answer-choice-body small { color: #aaa8a1; font-size: 10px; line-height: 1.45; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.answer-choice-consequence { display: block; margin-top: 2px; color: #ff9c7f; font-size: 9px; font-style: normal; line-height: 1.35; }
.answer-choice-arrow { color: #77756f; font-size: 11px; }
.answer-choice:hover:not(:disabled) .answer-choice-arrow { color: var(--orange); }
/* Own grid row spanning both .question-panel columns (like
   .question-panel-header and .proposal-form) — without this, the strip is
   auto-placed into column 1 alongside .question-queue in column 2, which
   both (a) drags the strip's height up to match the queue's row height via
   grid's default item stretch (producing the oversized pill/"oval") and (b)
   pushes .selected-question into column 1 below the strip, leaving column
   2's next row empty. See DecisionWorkspaceView.vue task notes. */
.guided-path-strip {
  grid-column: 1 / -1;
  align-self: start;
  margin: 14px 26px 22px;
  padding: 8px 14px;
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 10px;
  min-height: 0;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: #f5f5f4;
  overflow-x: auto;
}
.guided-path-label { flex: 0 0 auto; color: var(--muted); font: 700 9px 'JetBrains Mono', monospace; letter-spacing: .05em; text-transform: uppercase; }
.guided-path-chip { flex: 0 0 auto; display: inline-flex; align-items: center; gap: 5px; padding: 4px 9px; border: 1px solid var(--line); border-radius: 999px; color: var(--muted); background: #fff; font-size: 10px; white-space: nowrap; }
.guided-path-chip i { font-style: normal; font-size: 10px; line-height: 1; }
.guided-path-chip.answered { border-color: rgba(19,121,91,.35); color: var(--green); background: #eefaf4; }
.guided-path-chip.current { border-color: var(--orange); color: var(--orange); background: rgba(255,75,31,.08); }
.guided-path-chip.upcoming { opacity: .6; }
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

/* Calm, content-first refinement UI inspired by Apple's layered system surfaces. */
:global(*) { box-sizing: border-box; }
:global(body) { background: #ffffff; }
.decision-shell {
  --ink: #1d1d1f;
  --paper: #ffffff;
  --muted: #6e6e73;
  --line: rgba(29, 29, 31, 0.10);
  --orange: #ff5a2f;
  --green: #248a5a;
  --red: #c9342f;
  --amber: #a15c00;
  background: #ffffff;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", sans-serif;
  letter-spacing: -0.01em;
}
.decision-header {
  min-height: 54px;
  padding: 0 28px;
  background: rgba(20, 20, 22, 0.88);
  border-bottom: 1px solid rgba(255,255,255,0.09);
  backdrop-filter: saturate(180%) blur(22px);
}
.brand-button { font-family: inherit; letter-spacing: 0.05em; }
.run-reference, .token-badge { font-family: ui-monospace, "SFMono-Regular", Menlo, monospace; }
.token-badge { border-radius: 999px; border-color: rgba(255,255,255,0.16); }
.token-badge.zero { color: #aef0d0; background: rgba(36,138,90,0.16); }
.icon-button { border-radius: 50%; border-color: rgba(255,255,255,0.18); }
.decision-main {
  max-width: 1240px;
  padding: 34px 28px 72px;
  display: flex;
  flex-direction: column;
  /* Every top-level section carries its own margin-top for spacing, so no
     gap is set here — that keeps this visually identical to plain block
     stacking. Demo builds bind :style="{ order }" per section (see
     sectionStyle() in <script setup>) to hoist the pending block above the
     fold; non-demo builds bind no order at all, so source order applies. */
}
.decision-hero {
  grid-template-columns: minmax(0, 1.45fr) minmax(320px, 0.55fr);
  gap: 36px;
  padding: 42px;
  border-radius: 28px;
  background: linear-gradient(145deg, #202023 0%, #111113 100%);
  box-shadow: 0 20px 60px rgba(0,0,0,0.16);
}
.decision-hero::after { opacity: 0.55; }
.ingestion-status { border-radius: 999px; font-family: ui-monospace, "SFMono-Regular", Menlo, monospace; }
.eyebrow { margin-top: 24px; font-family: ui-monospace, "SFMono-Regular", Menlo, monospace; }
.decision-hero h1 { max-width: 700px; font-size: clamp(38px, 5vw, 64px); line-height: 0.98; font-weight: 650; }
.hero-description { max-width: 680px; margin-top: 20px; color: #a1a1a6; font-size: 15px; line-height: 1.55; }
.question-disclosure { max-width: 680px; margin-top: 18px; color: #a1a1a6; }
.question-disclosure summary {
  min-height: 38px;
  width: fit-content;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #e5e5e7;
  font-size: 12px;
  font-weight: 620;
  cursor: pointer;
  list-style: none;
}
.question-disclosure summary::-webkit-details-marker { display: none; }
.question-disclosure summary::after { content: '›'; color: #ff9c7f; font-size: 18px; transition: transform 180ms ease; }
.question-disclosure[open] summary::after { transform: rotate(90deg); }
.question-disclosure p { max-height: 150px; margin-top: 8px; padding: 14px; overflow-y: auto; border-radius: 12px; color: #b4b4b8; background: rgba(255,255,255,.06); font-size: 12px; line-height: 1.55; }
.hero-metrics { overflow: hidden; border-radius: 18px; border-color: rgba(255,255,255,0.12); }
.hero-metric { min-height: 104px; padding: 18px; border-color: rgba(255,255,255,0.12); }
.hero-metric.accent { background: rgba(255,90,47,0.92); }
.metric-value { font-family: ui-monospace, "SFMono-Regular", Menlo, monospace; font-size: 28px; }
.status-grid { gap: 22px; margin-top: 16px; }
.status-card, .panel {
  border: 1px solid var(--line);
  border-radius: 22px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.03), 0 12px 32px rgba(0,0,0,0.035);
}
.status-card { padding: 25px 26px; }
.status-card.stop, .status-card.continue, .recommendation-card { border-top-width: 1px; }
.status-card.continue { background: linear-gradient(145deg, #fff 72%, #fff6f1 100%); }
.status-card.stop { background: linear-gradient(145deg, #fff 72%, #f2fbf6 100%); }
.stop-verdict { font-size: 26px; letter-spacing: -0.035em; }
.verdict-icon { border-radius: 14px; }
.recommendation-card h2 { font-size: 23px; letter-spacing: -0.025em; }
.report-status, .evidence-kind, .assumption-status, .evidence-counts span, .audit-count { border-radius: 999px; }
.decision-analysis-card { grid-column: 1 / -1; background: linear-gradient(145deg, #fff 75%, #f1f6ff 100%); }
.analysis-card-heading { display: flex; justify-content: space-between; align-items: flex-start; gap: 20px; }
.analysis-card-heading h2 { margin-top: 8px; font-size: 25px; letter-spacing: -.03em; }
.analysis-state { min-height: 30px; padding: 0 10px; display: inline-flex; align-items: center; border-radius: 999px; font: 650 10px ui-monospace, "SFMono-Regular", Menlo, monospace; text-transform: uppercase; }
.analysis-state.calculated { color: #176b45; background: #e5f6ec; }
.analysis-state.pending { color: #8a4d00; background: #fff1dc; }
.analysis-result-grid { margin-top: 22px; display: grid; grid-template-columns: minmax(260px, 1.5fr) minmax(150px, .55fr) minmax(180px, .75fr); gap: 10px; }
.analysis-recommendation, .analysis-metric { min-height: 116px; padding: 18px; display: flex; flex-direction: column; justify-content: flex-end; border: 1px solid var(--line); border-radius: 15px; background: rgba(255,255,255,.8); }
.analysis-recommendation span, .analysis-metric span, .model-review-grid span { color: #86868b; font: 650 9px ui-monospace, "SFMono-Regular", Menlo, monospace; letter-spacing: .08em; }
.analysis-recommendation strong { margin-top: 8px; font-size: 23px; letter-spacing: -.025em; }
.analysis-recommendation small, .analysis-metric small { margin-top: 7px; color: #86868b; font-size: 11px; line-height: 1.35; }
.analysis-metric strong { margin-top: 8px; font: 620 24px ui-monospace, "SFMono-Regular", Menlo, monospace; }
.analysis-action-table { margin-top: 12px; overflow: hidden; border: 1px solid var(--line); border-radius: 14px; background: #fff; }
.analysis-action-row { min-height: 46px; padding: 10px 14px; display: grid; grid-template-columns: minmax(180px, 1fr) auto auto; align-items: center; gap: 24px; border-bottom: 1px solid var(--line); color: #6e6e73; font-size: 11px; }
.analysis-action-row:last-child { border-bottom: 0; }
.analysis-action-row > span:first-child { color: #1d1d1f; font-size: 13px; font-weight: 620; }
.analysis-action-row strong { color: #1d1d1f; font-family: ui-monospace, "SFMono-Regular", Menlo, monospace; }
.analysis-footer-row { margin-top: 14px; display: flex; align-items: center; justify-content: space-between; gap: 20px; color: #86868b; font: 600 9px ui-monospace, "SFMono-Regular", Menlo, monospace; }
.analysis-footer-row .text-button { min-height: 40px; margin: 0; font-family: inherit; }
.analysis-unavailable { max-width: 760px; margin-top: 18px; color: #3a3a3c; font-size: 15px; line-height: 1.5; }
.action-confirmation-panel {
  margin-top: 18px;
  padding: 18px;
  border: 1px solid #efc9bb;
  border-radius: 15px;
  background: #fff7f3;
  scroll-margin-top: 90px;
}
.action-confirmation-panel > div:first-child > span { color: #ba4828; font: 700 8px ui-monospace, "SFMono-Regular", Menlo, monospace; letter-spacing: .09em; }
.action-confirmation-panel h3 { margin-top: 5px; font-size: 18px; }
.action-confirmation-panel p { margin-top: 5px; color: #746b67; font-size: 11px; line-height: 1.45; }
.confirmable-actions { margin-top: 14px; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 7px; }
.confirmable-actions > span { padding: 9px 10px; display: flex; align-items: flex-start; gap: 8px; border-radius: 10px; color: #3c3a38; background: #fff; font-size: 11px; line-height: 1.4; }
.confirmable-actions i { color: #248a5a; font-style: normal; font-weight: 800; }
.action-confirmation-check { margin-top: 14px; display: flex; align-items: flex-start; gap: 9px; color: #554f4c; font-size: 11px; line-height: 1.45; }
.action-confirmation-check input { margin-top: 2px; }
.actions-confirmed-note { margin-top: 14px; color: #176544; font-size: 12px; font-weight: 650; }
.confirmation-checklist { margin-top: 16px; display: flex; flex-wrap: wrap; gap: 8px; }
.confirmation-checklist span { padding: 7px 10px; border-radius: 999px; color: #805000; background: #fff2dc; font-size: 11px; }
.model-proposal-note { max-width: 820px; margin-top: 14px; color: #86868b; font-size: 12px; line-height: 1.5; }
.qualitative-signoff, .qualitative-approved-card { margin-top: 18px; padding: 16px; border: 1px solid #b8d8c6; border-radius: 14px; background: #f2fbf6; }
.qualitative-signoff > span, .qualitative-approved-card > span { color: #176544; font: 700 9px ui-monospace, "SFMono-Regular", Menlo, monospace; letter-spacing: .08em; }
.qualitative-signoff p, .qualitative-approved-card p { max-width: 780px; margin-top: 7px; color: #50645a; font-size: 12px; line-height: 1.5; }
.qualitative-signoff label { margin-top: 13px; display: flex; align-items: flex-start; gap: 9px; color: #33463c; font-size: 12px; line-height: 1.45; }
.qualitative-signoff input { flex: 0 0 auto; width: 16px; height: 16px; margin-top: 1px; accent-color: #176544; }
.qualitative-approved-card strong { margin-top: 8px; display: block; font-size: 18px; }
.model-review { margin-top: 18px; overflow: hidden; border: 1px solid var(--line); border-radius: 15px; background: rgba(255,255,255,.82); }
.model-review summary { min-height: 48px; padding: 0 16px; display: flex; align-items: center; justify-content: space-between; cursor: pointer; list-style: none; font-size: 13px; font-weight: 620; }
.model-review summary::-webkit-details-marker { display: none; }
.model-review summary::after { content: '›'; font-size: 19px; transition: transform 180ms ease; }
.model-review[open] summary::after { transform: rotate(90deg); }
.model-review-body { padding: 0 16px 18px; border-top: 1px solid var(--line); }
.model-review-grid { padding: 16px 0; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.model-review-grid > div { display: grid; align-content: start; gap: 6px; }
.model-review-grid strong { font-size: 12px; line-height: 1.45; }
.model-confirmations { padding: 14px; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px 18px; border-radius: 12px; background: #f5f5f7; }
.model-confirmations label { display: flex; align-items: flex-start; gap: 9px; color: #3a3a3c; font-size: 12px; line-height: 1.4; }
.model-confirmations input { flex: 0 0 auto; width: 16px; height: 16px; margin-top: 1px; accent-color: #0071e3; }
.analysis-confirm-button { min-height: 44px; margin-top: 14px; padding: 0 17px; border: 0; border-radius: 12px; color: #fff; background: #0071e3; font-size: 12px; font-weight: 620; cursor: pointer; }
.analysis-confirm-button:disabled { opacity: .42; cursor: not-allowed; }
.knowledge-growth-panel { margin-top: 16px; overflow: hidden; }
.tree-revision { padding: 7px 11px; border-radius: 999px; color: #6e6e73; background: #f1f1f3; font: 600 10px ui-monospace, "SFMono-Regular", Menlo, monospace; }
.knowledge-scroll { margin: 0 -30px -30px; padding: 26px 30px 30px; overflow-x: auto; overscroll-behavior-x: contain; }
.knowledge-tree {
  --node-line: #c7c7cc;
  width: var(--tree-width);
  min-height: 310px;
  display: grid;
  grid-template-columns: 210px 54px 300px 64px minmax(290px, 1fr);
  align-items: center;
  transition: width 760ms cubic-bezier(.2,.8,.2,1);
}
.tree-root-node, .tree-path-node, .tree-evidence-node, .tree-empty-node { position: relative; display: flex; flex-direction: column; justify-content: center; border-radius: 16px; }
.tree-root-node { min-height: 128px; padding: 20px; color: white; background: linear-gradient(145deg, #2b2b2f, #151517); box-shadow: 0 14px 30px rgba(0,0,0,.13); }
.tree-root-node span, .tree-path-node span, .tree-evidence-node span { font: 700 9px ui-monospace, "SFMono-Regular", Menlo, monospace; letter-spacing: .08em; }
.tree-root-node span { color: #ff9c7f; }
.tree-root-node strong { margin-top: 8px; font-size: 17px; line-height: 1.2; }
.tree-root-node small, .tree-path-node small, .tree-evidence-node small { margin-top: 8px; color: #8e8e93; font-size: 11px; }
.tree-trunk, .tree-growth-line { height: 2px; background: var(--node-line); transform-origin: left; animation: growLine 700ms cubic-bezier(.2,.8,.2,1) both; }
.tree-paths { position: relative; display: grid; gap: 9px; }
.tree-paths::before { content: ''; position: absolute; left: -1px; top: 24px; bottom: 24px; width: 2px; background: var(--node-line); }
.tree-path-node { min-height: 60px; margin-left: 18px; padding: 11px 14px; border: 1px solid var(--line); background: white; box-shadow: 0 4px 14px rgba(0,0,0,.04); }
.tree-path-node::before { content: ''; position: absolute; left: -19px; top: 50%; width: 18px; height: 2px; background: var(--node-line); }
.tree-path-node span { color: #86868b; }
.tree-path-node strong { margin-top: 3px; font-size: 12px; line-height: 1.25; }
.tree-path-node.strengthened { border-left: 4px solid var(--green); }
.tree-path-node.weakened { border-left: 4px solid var(--amber); }
.tree-path-node.pruned { border-left: 4px solid var(--red); opacity: .58; }
.tree-private-branches { display: flex; gap: 14px; align-items: center; min-width: 0; }
.tree-evidence-node, .tree-empty-node { flex: 0 0 172px; min-height: 116px; padding: 16px; border: 1px solid rgba(36,138,90,.22); background: #f1faf5; }
.tree-evidence-node::before, .tree-empty-node::before { content: ''; position: absolute; left: -15px; top: 50%; width: 14px; height: 2px; background: var(--node-line); }
.tree-evidence-node span { color: var(--green); }
.tree-evidence-node strong, .tree-empty-node strong { margin-top: 7px; font-size: 12px; line-height: 1.35; }
.tree-evidence-node.newest { animation: knowledgeBloom 760ms cubic-bezier(.16,1,.3,1) both; box-shadow: 0 0 0 5px rgba(36,138,90,.07), 0 12px 28px rgba(36,138,90,.10); }
.tree-evidence-node.insufficient { border-color: rgba(171,108,0,.28); background: #fff8e8; }
.tree-evidence-node.insufficient span { color: #9a6200; }
.tree-evidence-node.insufficient.newest { box-shadow: 0 0 0 5px rgba(171,108,0,.06), 0 12px 28px rgba(171,108,0,.09); }
.tree-empty-node { border-style: dashed; color: #6e6e73; background: #fafafa; }
.tree-empty-node > span { font-size: 24px; color: #b0b0b5; }
.tree-empty-node small { margin-top: 7px; line-height: 1.35; }
@keyframes growLine { from { transform: scaleX(0); opacity: 0; } to { transform: scaleX(1); opacity: 1; } }
@keyframes knowledgeBloom { from { opacity: 0; transform: translateX(-24px) scale(.88); } to { opacity: 1; transform: translateX(0) scale(1); } }
.workspace-grid {
  grid-template-columns: minmax(0, 1fr);
  gap: 16px;
  margin-top: 16px;
}
.workspace-primary { grid-row: 2; gap: 16px; }
.question-panel {
  grid-row: 1;
  position: static;
  display: grid;
  grid-template-columns: minmax(300px, .78fr) minmax(0, 1.22fr);
  padding: 0;
  color: var(--ink);
  background: #fff;
  border-color: var(--line);
}
.question-panel-header { grid-column: 1 / -1; padding: 25px 28px 20px; border-color: var(--line); }
.question-header-actions { display: flex; align-items: center; gap: 9px; }
.panel-index.inverse { color: var(--orange); }
.question-panel-header h2 { font-size: 28px; letter-spacing: -0.035em; }
.question-panel-header p { color: var(--muted); font-size: 13px; }
.queue-count { color: #b33b1a; background: #fff3ee; border: 0; border-radius: 999px; }
.add-question-button { padding: 8px 12px; border: 0; border-radius: 999px; color: white; background: #1d1d1f; font: 600 11px inherit; cursor: pointer; }
.proposal-form { grid-column: 1 / -1; display: grid; grid-template-columns: 1.1fr .7fr 1.2fr .8fr auto; gap: 12px; align-items: end; padding: 20px 28px; border-bottom: 1px solid var(--line); background: #f8f8fa; }
.proposal-form h3 { margin-top: 5px; font-size: 18px; }
.proposal-form p { max-width: 420px; margin-top: 5px; color: var(--muted); font-size: 11px; line-height: 1.4; }
.proposal-kicker { color: var(--orange); font: 700 9px ui-monospace, "SFMono-Regular", Menlo, monospace; letter-spacing: .08em; }
.proposal-form label { color: #6e6e73; font-size: 10px; }
.proposal-form input, .proposal-form select, .proposal-form textarea { width: 100%; margin-top: 6px; padding: 10px 11px; border: 1px solid #d2d2d7; border-radius: 10px; color: var(--ink); background: white; font: 12px inherit; outline: 0; resize: vertical; }
.proposal-form input:focus, .proposal-form select:focus, .proposal-form textarea:focus { border-color: #0071e3; box-shadow: 0 0 0 3px rgba(0,113,227,.12); }
.proposal-submit { min-height: 44px; padding: 0 15px; border: 0; border-radius: 999px; color: white; background: #1d1d1f; font: 600 12px inherit; cursor: pointer; }
.proposal-submit:disabled { opacity: .42; cursor: not-allowed; }
.question-queue { max-height: none; overflow: visible; border-right: 1px solid var(--line); border-bottom: 0; }
.queue-item { padding: 16px 18px; color: var(--ink); border-color: var(--line); }
.queue-item:hover { background: #f7f7f9; }
.queue-item.active { background: #f3f3f5; box-shadow: inset 4px 0 var(--orange); }
.queue-rank { color: #86868b; }
.queue-score { color: #b33b1a; }
.queue-copy { font-size: 12px; line-height: 1.45; }
.queue-copy small { display: block; margin-bottom: 4px; color: var(--orange); font: 700 8px ui-monospace, "SFMono-Regular", Menlo, monospace; letter-spacing: .08em; }
.selected-question { padding: 28px 30px 30px; max-height: none; overflow: visible; }
.question-meta { color: #86868b; }
.selected-question h3 { max-width: 760px; font-size: 24px; letter-spacing: -0.025em; }
.question-rationale { color: var(--muted); font-size: 13px; }
.value-score-heading { border-color: var(--line); }
.value-score-heading strong { color: #b33b1a; }
.value-components div { border-radius: 12px; background: #f5f5f7; }
.value-components span, .score-formula { color: #86868b; }
.expected-change { border: 0; border-radius: 14px; background: #fff5f0; }
.expected-change p { color: #5d4037; }
.clarification-card { margin-top: 14px; padding: 14px 15px; border: 1px solid #ead39e; border-radius: 14px; background: #fff9e9; }
.clarification-card > span { color: #966000; font: 700 9px ui-monospace, "SFMono-Regular", Menlo, monospace; letter-spacing: .08em; }
.clarification-card strong { display: block; margin-top: 6px; color: #4f3b14; font-size: 12px; }
.clarification-card p { margin-top: 6px; color: #75633e; font-size: 11px; line-height: 1.5; }
.affected-branches span { border-radius: 999px; color: #5d4037; background: #ffe4d8; }
.answer-form textarea, .answer-form input, .answer-form select {
  border-color: #d2d2d7;
  border-radius: 12px;
  color: var(--ink);
  background: #fff;
  font-family: inherit;
}
.answer-form textarea:focus, .answer-form input:focus, .answer-form select:focus { border-color: #0071e3; box-shadow: 0 0 0 3px rgba(0,113,227,.12); }
.answer-button { border-radius: 12px; background: #1d1d1f; font-size: 13px; }
.privacy-note { color: #86868b; }
.answered-card { border-radius: 14px; }
.panel { padding: 30px; }
.panel-heading h2 { font-size: 27px; }
.branch-map { grid-template-columns: 170px 28px 1fr; }
.decision-root, .branch-card { border-radius: 15px; }
.branch-card { margin-left: 16px; box-shadow: 0 5px 18px rgba(0,0,0,0.035); }
.score-track { border-radius: 999px; }
.evidence-layout { grid-template-columns: minmax(0, 1.35fr) minmax(260px, .65fr); gap: 34px; }
.evidence-item { padding: 18px 0; }
.evidence-item p, .assumption-item p { font-size: 14px; line-height: 1.55; }
.citation-chip { border-radius: 999px; }
.contradiction-item { border: 0; border-radius: 14px; }
.preview-note { margin-top: 12px; color: var(--muted); font-size: 12px; line-height: 1.45; }
.disclosure-actions { display: flex; align-items: center; justify-content: space-between; gap: 14px; padding-top: 18px; border-top: 1px solid var(--line); }
.disclosure-actions span { color: var(--muted); font-size: 12px; }
.disclosure-button, .memo-toggle {
  padding: 10px 16px;
  border: 0;
  border-radius: 999px;
  color: #fff;
  background: #1d1d1f;
  font: 600 13px inherit;
  cursor: pointer;
}
.deliverables-grid { grid-template-columns: minmax(0, 1.35fr) minmax(320px, .65fr); gap: 16px; margin-top: 16px; }
.memo-panel, .audit-panel { min-width: 0; }
.memo-content { position: relative; max-height: 720px; overflow: hidden; }
.memo-content :deep(.md-table-wrap) { max-width: 100%; overflow-x: auto; }
.memo-content :deep(pre), .memo-content :deep(code) { max-width: 100%; overflow-wrap: anywhere; }
.memo-content:not(.expanded) { mask-image: linear-gradient(to bottom, #000 0%, #000 86%, transparent 100%); }
.memo-content.expanded { max-height: none; mask-image: none; }
.memo-toggle { display: block; margin: 18px auto 0; background: #f0f0f2; color: #1d1d1f; }
.secondary-button, .primary-button { border-radius: 999px; font-size: 12px; font-weight: 600; }
.decision-footer { border-radius: 14px; background: rgba(255,255,255,.7); }
.state-card { border-radius: 22px; box-shadow: 0 14px 42px rgba(0,0,0,.06); }
.citation-drawer { background: #fff; }
.citation-drawer-header { background: rgba(20,20,22,.96); }

@media (max-width: 1120px) {
  .decision-hero, .workspace-grid, .deliverables-grid { grid-template-columns: minmax(0, 1fr); }
  .question-panel { grid-template-columns: 1fr; }
  .question-panel-header { grid-column: 1; }
  .question-queue { border-right: 0; border-bottom: 1px solid var(--line); }
  .proposal-form { grid-template-columns: 1fr 1fr; }
  .proposal-form > div, .proposal-question-field { grid-column: 1 / -1; }
  .selected-question { max-height: none; }
}

@media (max-width: 760px) {
  .decision-header { padding: 10px 16px; align-items: flex-start; }
  .brand-button :deep(.brand-suffix), .run-reference { display: none; }
  .header-actions { flex-wrap: wrap; justify-content: flex-end; }
  .token-badge { font-size: 8px; }
  .decision-main { padding: 18px 12px 40px; }
  .decision-hero { padding: 27px 22px; gap: 30px; }
  .knowledge-growth-panel { padding: 21px; }
  .knowledge-scroll { margin: 0 -21px -21px; padding: 22px 21px 24px; }
  .question-panel-header { flex-direction: column; }
  .question-header-actions { justify-content: space-between; }
  .proposal-form { grid-template-columns: 1fr; padding: 18px 20px; }
  .proposal-form > *, .proposal-question-field { grid-column: 1; }
  .hero-metrics { grid-template-columns: 1fr; }
  .hero-metric { min-height: 76px; border-right: 0; border-bottom: 1px solid #3a3935; }
  .status-grid, .evidence-layout { grid-template-columns: 1fr; }
  .analysis-card-heading, .analysis-footer-row { align-items: flex-start; flex-direction: column; }
  .analysis-result-grid, .model-review-grid, .model-confirmations { grid-template-columns: 1fr; }
  .analysis-action-row { grid-template-columns: 1fr; gap: 5px; }
  .evidence-column.secondary { padding: 22px 0 0; border-left: 0; border-top: 1px solid var(--line); }
  .branch-map { grid-template-columns: 1fr; gap: 14px; }
  .branch-connector, .branch-list::before, .branch-card::before { display: none; }
  .branch-card { margin-left: 0; }
  .panel-heading { flex-direction: column; }
  .panel { padding: 21px; }
}

@media (max-width: 480px) {
  .decision-header {
    min-height: 58px;
    padding: 7px 12px;
    align-items: center;
    flex-wrap: nowrap;
    gap: 8px;
  }
  .brand-button { flex: 0 0 38px; min-width: 38px; min-height: 44px; }
  .brand-button :deep(.brand-name),
  .brand-button :deep(.brand-suffix) { display: none; }
  .header-actions { min-width: 0; flex: 1; flex-wrap: nowrap; justify-content: flex-end; gap: 6px; }
  .token-badge { min-width: 0; padding: 7px 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .icon-button { flex: 0 0 40px; width: 40px; height: 40px; }
  .decision-hero { border-radius: 24px; }
  .decision-hero h1 { font-size: 37px; line-height: 1; }
  .hero-metrics { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .hero-metric {
    min-height: 94px;
    padding: 13px 10px;
    border-right: 1px solid rgba(255,255,255,0.12);
    border-bottom: 0;
  }
  .hero-metric:last-child { border-right: 0; }
  .metric-value { font-size: 24px; }
  .metric-label { font-size: 9px; }
}

/* Executive outcome layer — the primary customer-facing simulation result. */
.outcome-hero {
  position: relative;
  overflow: hidden;
  padding: 34px 36px 36px;
  border-radius: 28px;
  color: #fff;
  background:
    radial-gradient(circle at 88% 12%, rgba(255, 104, 63, .18), transparent 30rem),
    linear-gradient(145deg, #202023 0%, #0f0f11 100%);
  box-shadow: 0 24px 64px rgba(0, 0, 0, .17);
}
.outcome-hero::after {
  content: '';
  position: absolute;
  width: 360px;
  height: 360px;
  top: -250px;
  right: -150px;
  border: 1px solid rgba(255,255,255,.1);
  border-radius: 50%;
  box-shadow: 0 0 0 64px rgba(255,255,255,.018), 0 0 0 128px rgba(255,255,255,.012);
}
.outcome-topline,
.outcome-layout { position: relative; z-index: 1; }
.outcome-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  color: #85858b;
  font: 700 9px ui-monospace, "SFMono-Regular", Menlo, monospace;
  letter-spacing: .12em;
}
.demo-progress {
  position: relative;
  z-index: 1;
  margin-top: 20px;
  padding: 14px 16px;
  display: grid;
  grid-template-columns: minmax(220px, .65fr) minmax(180px, .35fr) minmax(300px, 1fr);
  gap: 18px;
  align-items: center;
  border: 1px solid rgba(255,255,255,.1);
  border-radius: 15px;
  background: rgba(255,255,255,.04);
}
.demo-progress > div:first-child { display: grid; gap: 4px; }
.demo-progress > div:first-child span {
  color: #ff9b7e;
  font: 700 8px ui-monospace, "SFMono-Regular", Menlo, monospace;
  letter-spacing: .1em;
}
.demo-progress > div:first-child strong { font-size: 12px; }
.demo-progress-track { height: 5px; overflow: hidden; border-radius: 999px; background: rgba(255,255,255,.12); }
.demo-progress-track i { display: block; height: 100%; border-radius: inherit; background: #ff744e; transition: width 300ms ease; }
.demo-progress p { color: #99999f; font-size: 10px; line-height: 1.45; }
.outcome-status {
  min-height: 30px;
  padding: 0 11px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid rgba(255, 173, 145, .34);
  border-radius: 999px;
  color: #ffd0c2;
  background: rgba(255, 75, 31, .1);
}
.outcome-status i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #ff744e;
  box-shadow: 0 0 0 4px rgba(255, 116, 78, .12);
}
.outcome-hero.ready .outcome-status {
  color: #bff3dd;
  border-color: rgba(70, 215, 161, .34);
  background: rgba(36, 138, 90, .13);
}
.outcome-hero.ready .outcome-status i { background: #42d49f; box-shadow: 0 0 0 4px rgba(66,212,159,.12); }
.outcome-layout {
  margin-top: 34px;
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(300px, .55fr);
  gap: 52px;
  align-items: end;
}
.outcome-kicker,
.snapshot-kicker,
.executive-card-kicker {
  color: #ff8f70;
  font: 700 9px ui-monospace, "SFMono-Regular", Menlo, monospace;
  letter-spacing: .12em;
}
.decision-request {
  max-width: 750px;
  margin-top: 9px;
  color: #a9a9ae;
  font-size: 13px;
  line-height: 1.45;
}
.outcome-copy h1 {
  max-width: 810px;
  margin-top: 24px;
  font-size: clamp(40px, 5vw, 68px);
  line-height: .98;
  letter-spacing: -.052em;
  font-weight: 630;
  text-wrap: balance;
}
.outcome-summary {
  max-width: 780px;
  margin-top: 20px;
  color: #c2c2c7;
  font-size: 15px;
  line-height: 1.6;
}
.outcome-actions {
  margin-top: 27px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 22px;
}
.outcome-primary {
  min-height: 46px;
  padding: 0 19px;
  border: 0;
  border-radius: 999px;
  color: #171719;
  background: #fff;
  font: 650 12px inherit;
  cursor: pointer;
}
.outcome-primary:disabled { opacity: .4; cursor: not-allowed; }
.outcome-secondary {
  min-height: 42px;
  padding: 0 2px;
  border: 0;
  border-bottom: 1px solid rgba(255,255,255,.4);
  color: #ededf0;
  background: transparent;
  font: 620 12px inherit;
  cursor: pointer;
}
.outcome-secondary:disabled { opacity: .35; cursor: not-allowed; }
.outcome-actions a {
  min-height: 40px;
  display: inline-flex;
  align-items: center;
  gap: 9px;
  color: #ededf0;
  font-size: 12px;
  font-weight: 620;
  text-decoration: none;
}
.outcome-actions a span { color: #ff8f70; font-size: 16px; }
.outcome-snapshot {
  padding: 22px;
  border: 1px solid rgba(255,255,255,.12);
  border-radius: 19px;
  background: rgba(255,255,255,.055);
  backdrop-filter: blur(12px);
}
.outcome-snapshot > strong {
  display: block;
  margin-top: 9px;
  font-size: 28px;
  letter-spacing: -.035em;
}
.outcome-snapshot > p {
  margin-top: 9px;
  color: #aaaab0;
  font-size: 12px;
  line-height: 1.5;
}
.outcome-snapshot dl { margin-top: 20px; border-top: 1px solid rgba(255,255,255,.12); }
.outcome-snapshot dl div {
  min-height: 47px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  border-bottom: 1px solid rgba(255,255,255,.1);
}
.outcome-snapshot dt { color: #8d8d93; font-size: 10px; }
.outcome-snapshot dd { color: #f3f3f5; font-size: 11px; font-weight: 620; text-align: right; }
.outcome-snapshot > small { display: block; margin-top: 13px; color: #77777d; font-size: 9px; line-height: 1.45; }

.completion-ladder {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: #fff;
  /* Compact page-progress element the designer wants pinned while scrolling.
     Sits below the sticky header (54-64px tall); dev-replay mode also shows
     a sticky banner below the header, so that variant pushes the top offset
     down further (see .dev-replay-readonly .completion-ladder below). */
  position: sticky;
  top: 58px;
  z-index: 35;
  box-shadow: 0 10px 24px rgba(17,17,15,.06);
  transition: top 220ms ease;
}
.dev-replay-readonly .completion-ladder { top: 90px; }
/* Condensed hero bar (see .condensed-hero-bar) sits above the ladder once
   the real outcome-hero scrolls out of view; push the ladder down by the
   bar's own height (56px) so the two stack without overlapping. */
.completion-ladder.ladder-pinned-below-bar { top: 114px; }
.dev-replay-readonly .completion-ladder.ladder-pinned-below-bar { top: 146px; }

.condensed-hero-bar {
  position: fixed;
  top: 58px;
  left: 0;
  right: 0;
  z-index: 38;
  height: 56px;
  padding: 0 32px;
  display: flex;
  align-items: center;
  gap: 16px;
  color: #fff;
  background: linear-gradient(145deg, #202023 0%, #111113 100%);
  border-bottom: 1px solid rgba(255,255,255,.08);
  box-shadow: 0 12px 30px rgba(0,0,0,.18);
  opacity: 0;
  transform: translateY(-10px);
  pointer-events: none;
  transition: opacity 220ms ease, transform 220ms ease;
}
.dev-replay-readonly .condensed-hero-bar { top: 90px; }
.condensed-hero-bar.visible { opacity: 1; transform: translateY(0); }
.condensed-hero-status {
  flex: 0 0 auto;
  padding: 5px 10px;
  border: 1px solid rgba(255,173,145,.34);
  border-radius: 999px;
  color: #ffd0c2;
  background: rgba(255,75,31,.14);
  font: 700 9px ui-monospace, "SFMono-Regular", Menlo, monospace;
  letter-spacing: .08em;
  white-space: nowrap;
}
.condensed-hero-headline {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  font-weight: 620;
  letter-spacing: -.01em;
}
.condensed-hero-progress {
  flex: 0 0 auto;
  color: #b5b3ac;
  font-size: 11px;
  white-space: nowrap;
}
@media (max-width: 760px) {
  .condensed-hero-bar { padding: 0 16px; gap: 10px; }
  .condensed-hero-progress { display: none; }
}
.completion-ladder > div {
  min-height: 58px;
  padding: 10px 10px;
  display: flex;
  align-items: center;
  gap: 7px;
  border-right: 1px solid var(--line);
  color: #8a8983;
}
.completion-ladder > div:last-child { border-right: 0; }
.completion-ladder span {
  width: 20px;
  height: 20px;
  flex: 0 0 20px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: #77777d;
  background: #efeff1;
  font: 700 7px ui-monospace, "SFMono-Regular", Menlo, monospace;
}
.completion-ladder small { font-size: 9px; line-height: 1.22; }
.completion-ladder > div.complete { color: #226a51; background: #f4fbf8; }
.completion-ladder > div.complete span { color: #fff; background: #248a5a; }
.completion-ladder > div.active { color: #9d371a; box-shadow: inset 0 -3px #ff744e; }
.completion-ladder > div.active span { color: #9d371a; background: #ffe5dc; }

.executive-summary-grid {
  margin-top: 16px;
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(320px, .8fr);
  gap: 16px;
}
.executive-card,
.action-plan-panel,
.decision-record > summary {
  border: 1px solid var(--line);
  border-radius: 22px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(0,0,0,.03), 0 12px 32px rgba(0,0,0,.035);
}
.executive-card { padding: 28px; }
.executive-card h2 {
  margin-top: 8px;
  font-size: 24px;
  line-height: 1.14;
  letter-spacing: -.035em;
}
.reason-list { margin-top: 21px; display: grid; gap: 0; list-style: none; }
.reason-list li {
  min-height: 64px;
  display: grid;
  grid-template-columns: 35px 1fr;
  gap: 12px;
  align-items: start;
  padding: 15px 0;
  border-top: 1px solid var(--line);
}
.reason-list li > span { color: #9b9992; font: 650 10px ui-monospace, "SFMono-Regular", Menlo, monospace; }
.reason-list p { color: #454447; font-size: 13px; line-height: 1.52; }
.executive-empty { margin-top: 20px; color: var(--muted); font-size: 13px; line-height: 1.55; }
.conditions-card { color: #fff; background: #242426; border-color: #242426; }
.conditions-card h2 { max-width: 380px; }
.condition-list { margin-top: 20px; display: grid; gap: 8px; }
.condition-list > div {
  min-height: 62px;
  padding: 12px;
  display: grid;
  grid-template-columns: auto 1fr;
  align-items: start;
  gap: 12px;
  border: 1px solid rgba(255,255,255,.09);
  border-radius: 13px;
  background: rgba(255,255,255,.04);
}
.condition-list > div > span {
  padding: 4px 6px;
  border-radius: 999px;
  color: #ffc2b0;
  background: rgba(255, 116, 78, .12);
  font: 700 8px ui-monospace, "SFMono-Regular", Menlo, monospace;
}
.condition-list strong { display: block; font-size: 12px; line-height: 1.4; }
.condition-list small { display: block; margin-top: 5px; color: #939399; font-size: 9px; }
.guardrail-callout { margin-top: 24px; display: flex; gap: 13px; align-items: flex-start; color: #b9e9d6; }
.guardrail-callout > span { width: 26px; height: 26px; flex: 0 0 26px; display: grid; place-items: center; border-radius: 50%; background: rgba(66,212,159,.15); }
.guardrail-callout p { color: #b8b8bd; font-size: 13px; line-height: 1.55; }

.action-plan-panel { margin-top: 16px; padding: 28px; scroll-margin-top: 84px; }
.action-plan-heading { display: flex; align-items: end; justify-content: space-between; gap: 30px; }
.action-plan-heading h2 { margin-top: 8px; font-size: 29px; line-height: 1.05; letter-spacing: -.04em; }
.action-plan-heading > p { max-width: 300px; color: var(--muted); font-size: 12px; line-height: 1.45; text-align: right; }
.plan-quality-strip { margin-top: 22px; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); overflow: hidden; border: 1px solid #edcbbd; border-radius: 14px; background: #fff7f3; }
.plan-quality-strip.ready { border-color: #b9ddc8; background: #f2fbf6; }
.plan-quality-strip > div { min-height: 76px; padding: 15px; display: flex; flex-direction: column; justify-content: flex-end; border-right: 1px solid rgba(90,70,60,.12); }
.plan-quality-strip > div:last-child { border-right: 0; }
.plan-quality-strip span, .plan-gap-panel > span, .action-contract-grid span, .action-deliverable > span, .action-contract-columns > div > span, .failure-response > span { color: #8b7770; font: 700 8px ui-monospace, "SFMono-Regular", Menlo, monospace; letter-spacing: .08em; }
.plan-quality-strip strong { margin-top: 7px; font-size: 19px; }
.plan-gap-panel { margin-top: 10px; padding: 15px 17px; border-radius: 12px; color: #7b321f; background: #fff0e9; }
.plan-gap-panel p { margin-top: 7px; font-size: 12px; line-height: 1.45; }
.owner-assignment-panel { margin-top: 16px; padding: 16px; border: 1px solid rgba(123,50,31,.18); border-radius: 12px; background: rgba(255,255,255,.72); scroll-margin-top: 110px; }
.owner-assignment-heading { display: grid; gap: 5px; }
.owner-assignment-heading strong { color: #312724; font-size: 14px; }
.owner-assignment-heading small { color: #806d67; font-size: 10px; line-height: 1.45; }
.owner-assignment-grid { margin-top: 14px; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.owner-assignment-grid label { display: grid; gap: 6px; }
.owner-assignment-grid label > span { color: #7b321f; font: 700 9px ui-monospace, "SFMono-Regular", Menlo, monospace; letter-spacing: .06em; text-transform: uppercase; }
.owner-assignment-grid input { width: 100%; min-height: 42px; padding: 0 12px; border: 1px solid #dfc5ba; border-radius: 9px; color: #292326; background: #fff; font: inherit; font-size: 12px; outline: none; }
.owner-assignment-grid input:focus { border-color: #ff744e; box-shadow: 0 0 0 3px rgba(255,116,78,.12); }
.owner-assignment-button { margin-top: 12px; min-height: 42px; padding: 0 16px; border: 0; border-radius: 999px; color: #fff; background: #242426; font-size: 11px; font-weight: 700; cursor: pointer; }
.owner-assignment-button:disabled { opacity: .45; cursor: not-allowed; }
.action-plan-list { margin-top: 18px; display: grid; grid-template-columns: 1fr; gap: 12px; }
.action-step {
  min-height: 0;
  padding: 22px;
  display: grid;
  grid-template-columns: 34px 1fr;
  gap: 14px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: #fbfbfc;
}
.action-step-index { color: #aaa8a1; font: 650 10px ui-monospace, "SFMono-Regular", Menlo, monospace; }
.action-step-copy { min-width: 0; display: flex; flex-direction: column; }
.action-step-meta { min-height: 22px; display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.action-step-meta span { color: #e54c25; font: 700 9px ui-monospace, "SFMono-Regular", Menlo, monospace; letter-spacing: .08em; text-transform: uppercase; }
.action-step-meta i { padding: 4px 6px; border-radius: 999px; color: #68686d; background: #ececef; font: 650 8px ui-monospace, "SFMono-Regular", Menlo, monospace; font-style: normal; text-transform: uppercase; }
.action-step h3 { margin-top: 22px; font-size: 17px; line-height: 1.23; letter-spacing: -.02em; overflow-wrap: anywhere; }
.action-step p { margin-top: 9px; color: #6e6e73; font-size: 12px; line-height: 1.5; }
.action-contract-grid { margin-top: 17px; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.action-contract-grid > div { min-height: 78px; padding: 12px; border: 1px solid var(--line); border-radius: 10px; background: #fff; }
.action-contract-grid strong { margin-top: 7px; display: block; font-size: 12px; line-height: 1.42; }
.action-deliverable { margin-top: 10px; padding: 14px; border-radius: 11px; color: #fff; background: #242426; }
.action-deliverable > span { color: #ff9b7e; }
.action-deliverable strong { margin-top: 7px; display: block; font-size: 13px; line-height: 1.45; }
.action-deliverable small { margin-top: 9px; display: block; color: #bdbdc2; font-size: 10px; }
.action-contract-columns { margin-top: 10px; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.action-contract-columns > div { padding: 14px; border-radius: 11px; background: #f0f0f2; }
.action-contract-columns ul { margin: 9px 0 0 17px; }
.action-contract-columns li { margin-top: 6px; color: #48484c; font-size: 11px; line-height: 1.45; }
.failure-response { margin-top: 10px; padding: 13px 14px; border-left: 3px solid #dd4b2a; border-radius: 4px 10px 10px 4px; background: #fff2ed; }
.failure-response p { margin-top: 6px; color: #663224; }
.action-provenance { margin-top: 10px; overflow: hidden; border: 1px solid #cfdbe8; border-radius: 11px; background: #f4f8fc; }
.action-provenance summary { min-height: 43px; padding: 0 13px; display: flex; align-items: center; cursor: pointer; color: #315b7c; font-size: 11px; font-weight: 650; }
.action-provenance > div { padding: 0 13px 13px; }
.action-provenance p { padding: 10px; border-radius: 9px; background: #fff; }
.action-provenance p span, .action-provenance p small { display: block; color: #6d8aa0; font: 650 8px ui-monospace, "SFMono-Regular", Menlo, monospace; text-transform: uppercase; }
.action-provenance p strong { margin: 6px 0; display: block; color: #243849; font-size: 11px; line-height: 1.4; }

.completed-preview-panel {
  margin-top: 16px;
  padding: 28px;
  border: 1px dashed #b8b5ad;
  border-radius: 22px;
  background: rgba(255,255,255,.68);
}
.completed-preview-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; }
.completed-preview-heading h2 { margin-top: 8px; font-size: 25px; letter-spacing: -.035em; }
.completed-preview-heading > span { padding: 6px 9px; border-radius: 999px; color: #766d59; background: #eee8dc; font: 700 8px ui-monospace, "SFMono-Regular", Menlo, monospace; }
.completed-preview-decision { margin-top: 23px; padding: 20px; border-radius: 15px; color: #fff; background: #1d1d1f; }
.completed-preview-decision span,
.completed-preview-grid span { color: #ff9b7e; font: 700 8px ui-monospace, "SFMono-Regular", Menlo, monospace; letter-spacing: .09em; }
.completed-preview-decision h3 { max-width: 980px; margin-top: 8px; font-size: 21px; line-height: 1.32; }
.completed-preview-grid { margin-top: 12px; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
.completed-preview-grid > div { min-height: 116px; padding: 15px; border: 1px solid var(--line); border-radius: 13px; background: #fff; }
.completed-preview-grid strong { display: block; margin-top: 10px; font-size: 11px; line-height: 1.5; }

.decision-record { margin-top: 16px; scroll-margin-top: 82px; }
.decision-record > summary {
  min-height: 78px;
  padding: 18px 22px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  cursor: pointer;
  list-style: none;
}
.decision-record > summary::-webkit-details-marker { display: none; }
.decision-record > summary strong { display: block; font-size: 15px; }
.decision-record > summary small { display: block; margin-top: 5px; color: var(--muted); font-size: 11px; line-height: 1.4; }
.decision-record > summary > i {
  flex: 0 0 auto;
  padding: 9px 12px;
  border-radius: 999px;
  color: #fff;
  background: #1d1d1f;
  font-size: 10px;
  font-style: normal;
}
.decision-record-body { padding-top: 1px; }
.decision-record-body > .status-grid { margin-top: 16px; }

@media (max-width: 980px) {
  .outcome-layout,
  .executive-summary-grid { grid-template-columns: 1fr; }
  .outcome-layout { gap: 28px; }
  .outcome-snapshot { max-width: none; }
  .action-plan-list { grid-template-columns: 1fr; }
  .action-step { min-height: 0; }
  .demo-progress { grid-template-columns: 1fr 1fr; }
  .demo-progress p { grid-column: 1 / -1; }
  .completion-ladder { grid-template-columns: 1fr; }
  .completion-ladder > div { min-height: 52px; border-right: 0; border-bottom: 1px solid var(--line); }
  .completion-ladder > div:last-child { border-bottom: 0; }
  .completed-preview-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 620px) {
  .outcome-hero { padding: 24px 20px 25px; border-radius: 24px; }
  .outcome-topline { align-items: flex-start; flex-direction: column; }
  .outcome-topline > span:last-child { display: none; }
  .outcome-layout { margin-top: 26px; }
  .outcome-copy h1 { margin-top: 19px; font-size: 39px; }
  .outcome-summary { font-size: 14px; }
  .outcome-actions { align-items: flex-start; flex-direction: column; gap: 8px; }
  .outcome-primary { width: 100%; }
  .executive-card,
  .action-plan-panel { padding: 21px; }
  .action-plan-heading { align-items: flex-start; flex-direction: column; gap: 9px; }
  .action-plan-heading > p { text-align: left; }
  .action-step { padding: 17px 15px; grid-template-columns: 28px 1fr; }
  .plan-quality-strip,
  .action-contract-grid,
  .action-contract-columns { grid-template-columns: 1fr; }
  .plan-quality-strip > div { border-right: 0; border-bottom: 1px solid rgba(90,70,60,.12); }
  .plan-quality-strip > div:last-child { border-bottom: 0; }
  .decision-record > summary { align-items: flex-start; }
  .decision-record > summary small { max-width: 245px; }
  .demo-progress { grid-template-columns: 1fr; }
  .demo-progress p { grid-column: auto; }
  .owner-assignment-grid { grid-template-columns: 1fr; }
  .completed-preview-panel { padding: 21px; }
  .completed-preview-heading { flex-direction: column; }
  .completed-preview-grid,
  .confirmable-actions { grid-template-columns: 1fr; }
}
</style>
