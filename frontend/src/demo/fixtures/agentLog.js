// Phase 4 (report generation) fixture: the scripted agent-log timeline for
// the "Y Combinator in the AGI era" report run. Consumed by
// src/demo/handlers/phase345.js for GET /api/report/:id/agent-log.
//
// `at` is the entry's position as a fraction (0..1, strictly increasing) of
// REPORT_SECONDS — the handler compares it against
// jobFraction('reportGen', REPORT_SECONDS) to decide which entries are
// "visible" yet, and derives `elapsed_seconds` from it.
//
// IMPORTANT: several tool_result strings below are anchored on the exact
// Chinese-language markers src/components/Step4Report.vue's parseInsightForge
// / parsePanorama / parseInterview / parseQuickSearch regexes look for
// (e.g. "分析问题:", "### 【关键事实】", "### 采访摘要与核心观点",
// "#### 采访 #1:", "【Twitter平台回答】"). The markers themselves are never
// displayed — only the English payload text they wrap is. Do not reword or
// drop them; re-check src/components/Step4Report.vue ~565-980 before editing.

import { ts, IDS, REQUIREMENT } from './scenario.js'
import { REPORT_SECONDS } from '../timings.js'
import { OUTLINE, SECTIONS } from './report.js'

const INSIGHT_FORGE_RESULT = `分析问题: How will YC stakeholders react if Y Combinator commits to an AGI-native selection and batch model versus keeping the classic batch playbook?
预测场景: ${REQUIREMENT}
相关预测事实: 8条
涉及实体: 6
关系链: 5

### 分析的子问题
1. What share of the current batch is already agent-native, and how has that shifted over time?
2. Do the telemetry study and the post-batch quality audit agree on the productivity gain from agent leverage?
3. What applicant profile should the AGI-Native Track prioritize?
4. What guardrails would let a staged pilot be reversed if it underperforms?

### 【关键事实】
1. "41% of the most recent YC batch used agent fleets for the majority of engineering work, up from 9% two batches earlier."
2. "Median founding-team size in the latest batch is 1.8 people, down from 3.1 in 2023."
3. "A telemetry study found agent-native teams shipped 3.2x more weekly releases in their first 12 weeks."
4. "A post-batch quality audit found the real gap is only 1.4x once senior oversight and ownership are controlled for, with 2.4x more critical production incidents in agent-heavy teams lacking oversight."
5. "The proposed AGI-Native Track pilot would admit roughly 60 companies (about 15% of the batch), evaluated over two batch cycles before any wider commitment."

### 【核心实体】
- **Elena Voss** (Person)
  摘要: "YC Group Partner leading the AGI-Native Track proposal, weighing a staged pilot against a full batch-model overhaul."
  相关事实: 4
- **Y Combinator** (Organization)
  摘要: "Accelerator deciding how to prepare its Winter 2027 batch for the AGI era."
  相关事实: 5
- **Velocity Program** (Organization)
  摘要: "Rival accelerator running an all-in AGI track with no staged pilot."
  相关事实: 2

### 【关系链】
- Y Combinator --[considers]--> Staged AGI-Native Track
- Helios Research --[publishes]--> Agent Leverage Telemetry Study
- Post-Batch Quality Audit --[contradicts]--> Agent Leverage Telemetry Study`

const PANORAMA_RESULT = `查询: How is founder, partner, and LP sentiment trending across YC's AGI-native batch strategy options?
总节点数: 42
总边数: 71
当前有效事实: 9
历史/过期事实: 3

### 【当前有效事实】
1. "Y Combinator has confirmed it is scoping a staged AGI-Native Track for roughly 60 companies over two batch cycles."
2. "Enterprise procurement teams, per Hana Sato, already screen vendors on agent-leverage ratio ahead of headcount."
3. "Velocity Program has publicly mocked YC's staged evaluation approach in favor of an immediate full commitment."
4. "The post-batch quality audit's 2.4x incident-rate finding shifted discourse from raw velocity toward oversight competence."

### 【历史/过期事实】
1. "An early leaked draft considered an immediate, full batch-model overhaul with no staged pilot."
2. "Early estimates citing a flat 3.2x productivity gain were superseded once the post-batch quality audit's 1.4x oversight-adjusted figure was published."

### 【涉及实体】
- **Elena Voss** (Person)
- **Marcus Oyelaran** (Person)
- **Rachel Adeyemi** (Person)
- **Kai Nakamura** (Person)
- **Velocity Program** (Organization)`

const INTERVIEW_RESULT = `**采访主题:** How are key Y Combinator stakeholders weighing a full AGI-native batch overhaul against a staged, reversible AGI-Native Track?
**采访人数:** 3 / 16

### 采访对象选择理由
1. **Elena Voss (index=0)**: As the Group Partner leading the AGI-Native Track proposal, she can speak directly to the tradeoffs the partnership is weighing.
2. **Rachel Adeyemi (index=7)**: As an LP at a university endowment, she represents the institutional-capital perspective on accelerator returns in the AGI era.
3. **Kai Nakamura (index=3)**: As the solo founder of Loomfield running a 40-agent fleet, he represents the agent-native archetype the new applicant profile is built around.

---

#### 采访 #1: Group Partner
**Elena Voss** (Group Partner, AGI-Native Track Lead, Y Combinator)
_简介: Leading YC's proposal for a staged, reversible AGI-Native Track ahead of the Winter 2027 batch._

**Q:** 1. Why propose a staged pilot instead of a full batch-model overhaul?
2. What would make you pause or reverse the pilot?

**A:** 【Twitter平台回答】
A full overhaul bets the entire batch on data that's still contested — 3.2x from the telemetry study against 1.4x from the post-batch audit. A staged pilot lets us resolve that question with our own cohort's numbers before we bet the brand on it. I'd pause immediately if incident rates crossed 1.5x baseline, and I'd revisit the whole track if LPs weren't aligned by the cohort 1 exit.

【Reddit平台回答】
Honestly, moving slower than Velocity Program looks worse in the news cycle than it feels internally. Sixty companies and two batch cycles is enough to tell whether agent leverage translates into real founder judgment, not just faster demos. If the incident numbers get away from us, we pause — no exceptions.

**关键引言:**
> "A staged pilot lets us resolve that question with our own cohort's numbers before we bet the brand on it."
> "If the incident numbers get away from us, we pause — no exceptions."

---

#### 采访 #2: LP
**Rachel Adeyemi** (LP, University Endowment)
_简介: Skeptical of accelerator returns in the AGI era; wants bounded risk and measurable guardrails before committing further capital._

**Q:** 1. What would satisfy your committee's concerns about the AGI-Native Track?
2. Do you trust the 3.2x productivity figure?

**A:** 【Twitter平台回答】
A bounded pilot with a named evaluation window is something my committee can actually underwrite. An open-ended policy change based on one telemetry study is not. On the 3.2x number — I trust it as a ceiling, not a forecast; the 1.4x oversight-adjusted figure is closer to what I'd underwrite capital against.

【Reddit平台回答】
Anecdotes aren't a portfolio strategy, and a single 40-agent founder's ARR isn't a batch-level result. What moves me is the pause trigger and the LP alignment checkpoint at cohort 1's exit — those are the two things that turn this from a bet into a controlled experiment.

**关键引言:**
> "Anecdotes aren't a portfolio strategy."
> "The pause trigger and the LP alignment checkpoint are what turn this from a bet into a controlled experiment."

---

#### 采访 #3: Founder
**Kai Nakamura** (Solo Founder, Loomfield)
_简介: Runs a 40-agent fleet solo at $2.1M ARR; the agent-native archetype the new applicant profile is built to identify._

**Q:** 1. What does your day-to-day supervision of the agent fleet actually look like?
2. How should YC measure agent leverage without rewarding demo-only fleets?

**A:** 【Twitter平台回答】
People see the ARR and assume it runs itself. It doesn't — I spend more hours reviewing agent output than most nine-person teams spend writing code. If YC wants to measure leverage honestly, it should ask for the supervision-weighted ratio, not the raw one. Mine is closer to 12:1 once you weight for real review time, not 40:1.

【Reddit平台回答】
The raw ratio is a vanity number. Ask any agent-native founder for one specific example of catching or correcting their fleet's output this week — the ones with a real answer are the ones worth funding. The ones without one are running a demo, not a company.

**关键引言:**
> "I spend more hours reviewing agent output than most nine-person teams spend writing code."
> "The raw ratio is a vanity number."

### 采访摘要与核心观点
Across all three interviews, a consistent picture emerges: stakeholders prefer the staged, reversible AGI-Native Track over either a full overhaul or the status quo, provided the guardrails hold. Elena Voss frames the pilot as a way to resolve the 3.2x-vs-1.4x dispute with YC's own data rather than betting the batch on someone else's. Rachel Adeyemi treats the pause trigger and LP alignment checkpoint as the non-negotiable conditions for her committee's continued confidence. Kai Nakamura, the agent-native archetype the profile is built around, is the most emphatic that the raw agent-leverage ratio is the wrong metric — supervision-weighted leverage and demonstrated judgment are what should actually drive admissions. None of the three interviewees supported an unbounded full overhaul.`

const QUICK_SEARCH_RESULT = `搜索查询: What reversibility and pause conditions have applied to past YC pilot programs before a full batch-model rollout?
找到 6 条相关事实。

### 相关事实:
1. "The proposed AGI-Native Track pilot covers roughly 60 companies, about 15% of the Winter 2027 batch."
2. "The pilot is evaluated over two full batch cycles before any wider rollout is considered."
3. "A pause trigger applies if incident rates exceed 1.5x baseline at any point during the pilot."
4. "An LP alignment checkpoint is scheduled at cohort 1's exit to review results directly with endowment and fund committees."
5. "The telemetry study found a 3.2x weekly-release multiple for agent-native teams in their first 12 weeks."
6. "The post-batch quality audit found a 1.4x oversight-adjusted multiple, with 2.4x more critical incidents in agent-heavy teams lacking senior oversight."`

const GRAPH_STATS_RESULT = `Graph snapshot for ${IDS.simulationId}: 42 nodes, 71 edges. Entity types: Founder (8), Partner (3), StartupCompany (8), ResearchLab (2), InvestorLP (2), AcceleratorProgram (2). Most connected entities: Y Combinator (26 edges), AGI-Native Track (11 edges), Helios Research (7 edges).`

const ENTITIES_BY_TYPE_RESULT = `Entities of type AcceleratorProgram: Y Combinator, AGI-Native Track (program), Velocity Program.`

const section = (index) => ({ section_index: index, section_title: OUTLINE.sections[index - 1].title })

// [at, action, section_index|null, section_title|null, details]
const RAW = [
  { at: 0.00, action: 'report_start', section_index: null, section_title: null, details: { simulation_id: IDS.simulationId, simulation_requirement: REQUIREMENT } },
  { at: 0.02, action: 'planning_start', section_index: null, section_title: null, details: { message: `Planning report structure for simulation ${IDS.simulationId}...` } },
  { at: 0.05, action: 'planning_complete', section_index: null, section_title: null, details: { message: `Report outline finalized: ${OUTLINE.sections.length} sections.`, outline: OUTLINE } },

  // Section 1 — Coverage View (insight_forge)
  { at: 0.08, action: 'section_start', ...section(1), details: {} },
  { at: 0.10, action: 'tool_call', ...section(1), details: { tool_name: 'insight_forge', parameters: { query: 'How will YC stakeholders react if Y Combinator commits to an AGI-native selection and batch model versus keeping the classic batch playbook?', simulation_requirement: REQUIREMENT } } },
  { at: 0.12, action: 'tool_result', ...section(1), details: { tool_name: 'insight_forge', result: INSIGHT_FORGE_RESULT, result_length: INSIGHT_FORGE_RESULT.length } },
  { at: 0.14, action: 'llm_response', ...section(1), details: { iteration: 1, has_tool_calls: false, has_final_answer: true, response: `Final Answer:\n\n${SECTIONS[1]}` } },
  { at: 0.16, action: 'section_complete', ...section(1), details: { content: SECTIONS[1] } },

  // Section 2 — Discourse & Sentiment Arc (panorama_search)
  { at: 0.19, action: 'section_start', ...section(2), details: {} },
  { at: 0.21, action: 'tool_call', ...section(2), details: { tool_name: 'panorama_search', parameters: { query: "How is founder, partner, and LP sentiment trending across YC's AGI-native batch strategy options?" } } },
  { at: 0.23, action: 'tool_result', ...section(2), details: { tool_name: 'panorama_search', result: PANORAMA_RESULT, result_length: PANORAMA_RESULT.length } },
  { at: 0.25, action: 'llm_response', ...section(2), details: { iteration: 1, has_tool_calls: false, has_final_answer: true, response: `Final Answer:\n\n${SECTIONS[2]}` } },
  { at: 0.27, action: 'section_complete', ...section(2), details: { content: SECTIONS[2] } },

  // Section 3 — Stakeholder Book (interview_agents)
  { at: 0.30, action: 'section_start', ...section(3), details: {} },
  {
    at: 0.33,
    action: 'tool_call',
    ...section(3),
    details: {
      tool_name: 'interview_agents',
      parameters: {
        simulation_id: IDS.simulationId,
        interviews: [
          { agent_id: 0, prompt: 'Why propose a staged pilot instead of a full batch-model overhaul?' },
          { agent_id: 7, prompt: "What would satisfy your committee's concerns about the AGI-Native Track?" },
          { agent_id: 3, prompt: 'What does your day-to-day supervision of the agent fleet actually look like?' }
        ]
      }
    }
  },
  { at: 0.38, action: 'tool_result', ...section(3), details: { tool_name: 'interview_agents', result: INTERVIEW_RESULT, result_length: INTERVIEW_RESULT.length } },
  { at: 0.41, action: 'llm_response', ...section(3), details: { iteration: 1, has_tool_calls: false, has_final_answer: true, response: `Final Answer:\n\n${SECTIONS[3]}` } },
  { at: 0.44, action: 'section_complete', ...section(3), details: { content: SECTIONS[3] } },

  // Section 4 — Scenario Analysis (quick_search)
  { at: 0.47, action: 'section_start', ...section(4), details: {} },
  { at: 0.49, action: 'tool_call', ...section(4), details: { tool_name: 'quick_search', parameters: { query: 'What reversibility and pause conditions have applied to past YC pilot programs before a full batch-model rollout?' } } },
  { at: 0.51, action: 'tool_result', ...section(4), details: { tool_name: 'quick_search', result: QUICK_SEARCH_RESULT, result_length: QUICK_SEARCH_RESULT.length } },
  { at: 0.53, action: 'llm_response', ...section(4), details: { iteration: 1, has_tool_calls: false, has_final_answer: true, response: `Final Answer:\n\n${SECTIONS[4]}` } },
  { at: 0.56, action: 'section_complete', ...section(4), details: { content: SECTIONS[4] } },

  // Section 5 — The AGI-Era Applicant Profile (get_graph_statistics)
  { at: 0.60, action: 'section_start', ...section(5), details: {} },
  { at: 0.62, action: 'tool_call', ...section(5), details: { tool_name: 'get_graph_statistics', parameters: { graph_id: IDS.graphId } } },
  { at: 0.64, action: 'tool_result', ...section(5), details: { tool_name: 'get_graph_statistics', result: GRAPH_STATS_RESULT, result_length: GRAPH_STATS_RESULT.length } },
  { at: 0.67, action: 'llm_response', ...section(5), details: { iteration: 1, has_tool_calls: false, has_final_answer: true, response: `Final Answer:\n\n${SECTIONS[5]}` } },
  { at: 0.70, action: 'section_complete', ...section(5), details: { content: SECTIONS[5] } },

  // Section 6 — Recommendation & 12-Month Roadmap (get_entities_by_type)
  { at: 0.75, action: 'section_start', ...section(6), details: {} },
  { at: 0.78, action: 'tool_call', ...section(6), details: { tool_name: 'get_entities_by_type', parameters: { entity_type: 'AcceleratorProgram' } } },
  { at: 0.81, action: 'tool_result', ...section(6), details: { tool_name: 'get_entities_by_type', result: ENTITIES_BY_TYPE_RESULT, result_length: ENTITIES_BY_TYPE_RESULT.length } },
  { at: 0.85, action: 'llm_response', ...section(6), details: { iteration: 1, has_tool_calls: false, has_final_answer: true, response: `Final Answer:\n\n${SECTIONS[6]}` } },
  { at: 0.90, action: 'section_complete', ...section(6), details: { content: SECTIONS[6] } },

  { at: 0.98, action: 'report_complete', section_index: null, section_title: null, details: {} }
]

const agentLog = RAW.map((entry, index) => ({
  at: entry.at,
  timestamp: ts(index * 3),
  action: entry.action,
  elapsed_seconds: Math.round(entry.at * REPORT_SECONDS * 10) / 10,
  section_index: entry.section_index,
  section_title: entry.section_title,
  details: entry.details
}))

export default agentLog
