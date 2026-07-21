// Phase 4 (report generation) fixture: the scripted agent-log timeline for
// the Northstar Appliances report run. Consumed by
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

const INSIGHT_FORGE_RESULT = `分析问题: How will stakeholders react to an immediate restructuring versus a staged, reversible pilot at Northstar Appliances?
预测场景: ${REQUIREMENT}
相关预测事实: 8条
涉及实体: 6
关系链: 5

### 分析的子问题
1. What is Northstar's liquidity runway and how does it constrain the timeline?
2. Would Meridian Lending Group finance a staged pilot, and under what conditions?
3. What do the burn-reduction benchmarks say about staged versus immediate restructuring?
4. What does the UAW Local 1180 agreement require before any closures?

### 【关键事实】
1. "Northstar Appliances has approximately 11 weeks of liquidity runway at current burn."
2. "Meridian Lending Group will back a staged, reversible pilot if Northstar provides weekly liquidity reporting and supplier payment protection."
3. "Industry benchmark data shows staged restructuring programs cut burn by roughly 18% over 90 days."
4. "Northstar's own supplier survey estimates a more conservative 6% burn reduction over 90 days."
5. "The UAW Local 1180 agreement permits a time-limited pilot but requires consultation before any plant closures."

### 【核心实体】
- **Dana Whitfield** (Person)
  摘要: "CEO of Northstar Appliances, weighing an immediate restructuring against a staged pilot."
  相关事实: 4
- **Meridian Lending Group** (Organization)
  摘要: "Lender offering to back a reversible pilot conditioned on weekly liquidity reporting and supplier payment protection."
  相关事实: 3
- **UAW Local 1180** (Organization)
  摘要: "Union whose agreement requires consultation before any plant closures."
  相关事实: 3

### 【关系链】
- Northstar Appliances --[considers]--> Staged Reversible Pilot
- Meridian Lending Group --[conditions financing on]--> Weekly Liquidity Reporting
- UAW Local 1180 --[requires consultation before]--> Plant Closures`

const PANORAMA_RESULT = `查询: How is public sentiment trending across the two Northstar Appliances restructuring options?
总节点数: 42
总边数: 68
当前有效事实: 9
历史/过期事实: 3

### 【当前有效事实】
1. "Meridian Lending Group has offered to back a staged, reversible pilot if Northstar reports liquidity weekly and protects supplier payments."
2. "UAW Local 1180 has agreed to support a time-limited pilot in exchange for consultation before any closures."
3. "Karlin Components has committed to weekly reporting to help the pilot succeed."
4. "The first weekly liquidity report under the pilot came in within Meridian's target range."

### 【历史/过期事实】
1. "An earlier internal draft considered an immediate companywide restructuring with no pilot phase."
2. "Early supplier survey estimates of a 6% burn reduction were superseded in initial talks by benchmark data suggesting 18% was achievable under a staged program."

### 【涉及实体】
- **Dana Whitfield** (Person)
- **Marcus Lee** (Person)
- **Meridian Lending Group** (Organization)
- **UAW Local 1180** (Organization)
- **Karlin Components** (Organization)`

const INTERVIEW_RESULT = `**采访主题:** How are key Northstar Appliances stakeholders weighing an immediate restructuring against a staged, reversible pilot?
**采访人数:** 3 / 16

### 采访对象选择理由
1. **Dana Whitfield (index=0)**: As CEO, she is the primary decision-maker and can speak directly to the tradeoffs leadership is weighing.
2. **Denise Ruiz (index=6)**: As Chief Shop Steward for UAW Local 1180, she speaks for the workforce most affected by either path.
3. **Tom Reyes (index=8)**: As Karlin Components' CFO, he represents the supplier perspective on burn-reduction benchmarks and payment protection.

---

#### 采访 #1: CEO
**Dana Whitfield** (Chief Executive Officer, Northstar Appliances)
_简介: Leading Northstar through an 11-week liquidity window and deciding between an immediate restructuring and a staged, reversible pilot._

**Q:** 1. Why did you choose to disclose the liquidity runway publicly instead of managing the process privately?
2. What would make you abandon the pilot and move to a full restructuring?

**A:** 【Twitter平台回答】
Transparency builds more trust than a surprise announcement would have. We disclosed the runway because our people and partners deserve the real picture, not a sanitized one. As for abandoning the pilot — if the weekly liquidity targets slip twice in a row, or Meridian pulls financing, we'd have to revisit everything.

【Reddit平台回答】
Honestly, hiding the number felt worse than the number itself. Once employees and the union know the real constraint, they can actually help solve it instead of guessing. We'd only walk away from the pilot if the numbers stopped adding up two weeks running.

**关键引言:**
> "Transparency builds more trust than a surprise announcement would have."
> "We'd only walk away from the pilot if the numbers stopped adding up two weeks running."

---

#### 采访 #2: Union Representative
**Denise Ruiz** (Chief Shop Steward, UAW Local 1180)
_简介: Leads union negotiations for Toledo workers, pushing for a firm sunset date on any pilot plus consultation rights before permanent closures._

**Q:** 1. Does the pilot structure satisfy the union's core demands?
2. What would you do if leadership tried to skip the consultation step?

**A:** 【Twitter平台回答】
It satisfies our floor demand: consultation before closures, in writing. We're still watching the weekly numbers closely, because a pilot can quietly become permanent if nobody's paying attention. If leadership tried to skip consultation, we'd file a grievance immediately and go public with it.

【Reddit平台回答】
This is the version of "restructuring" our agreement was built to produce — one where we get a say before anyone loses a plant. We're not naive about it either; we'll keep tracking every weekly report Meridian gets.

**关键引言:**
> "This is the version of restructuring our agreement was built to produce."
> "A pilot can quietly become permanent if nobody's paying attention."

---

#### 采访 #3: Supplier CFO
**Tom Reyes** (Chief Financial Officer, Karlin Components)
_简介: Warns that delayed approvals and unclear ownership could cut Northstar's expected cash-burn savings from 18% down to as low as 6%._

**Q:** 1. How does the staged pilot change Karlin's own planning?
2. Do you trust the 18% burn-reduction benchmark leadership cited?

**A:** 【Twitter平台回答】
Weekly reporting cuts both ways for us — we get earlier visibility if Northstar's orders are going to shift. That's exactly the certainty we asked for. On the 18% number, I'd put more weight on the 6% our own supplier survey found; 18% assumes a level of cooperation we haven't seen committed to in writing.

【Reddit平台回答】
It lets us plan production runs instead of guessing. I'm skeptical of the 18% figure — it's an industry benchmark, not something specific to Northstar's plants. Six percent is the number I'd actually budget around.

**关键引言:**
> "That's exactly the certainty we asked for."
> "Six percent is the number I'd actually budget around."

### 采访摘要与核心观点
Across all three interviews, a consistent picture emerges: stakeholders prefer the staged, reversible pilot over an immediate full restructuring, provided the financial and consultation safeguards hold. Dana Whitfield frames the choice as a transparency-driven tradeoff bounded by weekly liquidity performance. Denise Ruiz treats the consultation clause as a hard-won floor that UAW Local 1180 will keep enforcing rather than a formality. Tom Reyes is the most skeptical of the optimistic 18% burn-reduction benchmark, favoring the more conservative 6% supplier-survey estimate, but still supports the pilot structure because it gives Karlin earlier visibility into order changes. None of the three interviewees expressed support for skipping straight to an immediate, irreversible restructuring.`

const QUICK_SEARCH_RESULT = `搜索查询: What time-limited pilot terms has the UAW Local 1180 agreement historically allowed?
找到 6 条相关事实。

### 相关事实:
1. "The UAW Local 1180 agreement permits a time-limited pilot program before any closures are finalized."
2. "Consultation with the union is required before Northstar can finalize any plant closure."
3. "Meridian Lending Group's financing offer is conditioned on weekly liquidity reporting."
4. "Karlin Components has agreed to weekly reporting to support supplier payment protection."
5. "Industry benchmark data estimates an 18% burn reduction over 90 days for staged restructuring programs."
6. "Northstar's internal supplier survey estimates a more conservative 6% burn reduction over 90 days."`

const GRAPH_STATS_RESULT = `Graph snapshot for ${IDS.simulationId}: 42 nodes, 68 edges. Entity types: Person (16), Organization (8), Event (12), Fact (6). Most connected entities: Northstar Appliances (24 edges), Meridian Lending Group (9 edges), UAW Local 1180 (8 edges).`

const ENTITIES_BY_TYPE_RESULT = `Entities of type Organization: Northstar Appliances, Meridian Lending Group, UAW Local 1180, Karlin Components, HomePlex Retail Group, Northstar Toledo Plant, Northstar Macon Plant, Northstar Board of Directors.`

const section = (index) => ({ section_index: index, section_title: OUTLINE.sections[index - 1].title })

// [at, action, section_index|null, section_title|null, details]
const RAW = [
  { at: 0.00, action: 'report_start', section_index: null, section_title: null, details: { simulation_id: IDS.simulationId, simulation_requirement: REQUIREMENT } },
  { at: 0.02, action: 'planning_start', section_index: null, section_title: null, details: { message: `Planning report structure for simulation ${IDS.simulationId}...` } },
  { at: 0.05, action: 'planning_complete', section_index: null, section_title: null, details: { message: `Report outline finalized: ${OUTLINE.sections.length} sections.`, outline: OUTLINE } },

  // Section 1 — Executive Summary (insight_forge)
  { at: 0.08, action: 'section_start', ...section(1), details: {} },
  { at: 0.10, action: 'tool_call', ...section(1), details: { tool_name: 'insight_forge', parameters: { query: 'How will stakeholders react to an immediate restructuring versus a staged, reversible pilot at Northstar Appliances?', simulation_requirement: REQUIREMENT } } },
  { at: 0.12, action: 'tool_result', ...section(1), details: { tool_name: 'insight_forge', result: INSIGHT_FORGE_RESULT, result_length: INSIGHT_FORGE_RESULT.length } },
  { at: 0.14, action: 'llm_response', ...section(1), details: { iteration: 1, has_tool_calls: false, has_final_answer: true, response: `Final Answer:\n\n${SECTIONS[1]}` } },
  { at: 0.16, action: 'section_complete', ...section(1), details: { content: SECTIONS[1] } },

  // Section 2 — Public Sentiment Timeline (panorama_search)
  { at: 0.19, action: 'section_start', ...section(2), details: {} },
  { at: 0.21, action: 'tool_call', ...section(2), details: { tool_name: 'panorama_search', parameters: { query: 'How is public sentiment trending across the two Northstar Appliances restructuring options?' } } },
  { at: 0.23, action: 'tool_result', ...section(2), details: { tool_name: 'panorama_search', result: PANORAMA_RESULT, result_length: PANORAMA_RESULT.length } },
  { at: 0.25, action: 'llm_response', ...section(2), details: { iteration: 1, has_tool_calls: false, has_final_answer: true, response: `Final Answer:\n\n${SECTIONS[2]}` } },
  { at: 0.27, action: 'section_complete', ...section(2), details: { content: SECTIONS[2] } },

  // Section 3 — Stakeholder Positions (interview_agents)
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
          { agent_id: 0, prompt: 'How are you weighing the tradeoffs between an immediate restructuring and a staged pilot?' },
          { agent_id: 6, prompt: "Does the pilot structure satisfy the union's core demands?" },
          { agent_id: 8, prompt: 'How does the staged pilot change your planning as a supplier?' }
        ]
      }
    }
  },
  { at: 0.38, action: 'tool_result', ...section(3), details: { tool_name: 'interview_agents', result: INTERVIEW_RESULT, result_length: INTERVIEW_RESULT.length } },
  { at: 0.41, action: 'llm_response', ...section(3), details: { iteration: 1, has_tool_calls: false, has_final_answer: true, response: `Final Answer:\n\n${SECTIONS[3]}` } },
  { at: 0.44, action: 'section_complete', ...section(3), details: { content: SECTIONS[3] } },

  // Section 4 — Risk Scenarios (quick_search)
  { at: 0.47, action: 'section_start', ...section(4), details: {} },
  { at: 0.49, action: 'tool_call', ...section(4), details: { tool_name: 'quick_search', parameters: { query: 'What time-limited pilot terms has the UAW Local 1180 agreement historically allowed?' } } },
  { at: 0.51, action: 'tool_result', ...section(4), details: { tool_name: 'quick_search', result: QUICK_SEARCH_RESULT, result_length: QUICK_SEARCH_RESULT.length } },
  { at: 0.53, action: 'llm_response', ...section(4), details: { iteration: 1, has_tool_calls: false, has_final_answer: true, response: `Final Answer:\n\n${SECTIONS[4]}` } },
  { at: 0.56, action: 'section_complete', ...section(4), details: { content: SECTIONS[4] } },

  // Section 5 — Pilot vs Full Restructuring Comparison (get_graph_statistics)
  { at: 0.60, action: 'section_start', ...section(5), details: {} },
  { at: 0.62, action: 'tool_call', ...section(5), details: { tool_name: 'get_graph_statistics', parameters: { graph_id: IDS.graphId } } },
  { at: 0.64, action: 'tool_result', ...section(5), details: { tool_name: 'get_graph_statistics', result: GRAPH_STATS_RESULT, result_length: GRAPH_STATS_RESULT.length } },
  { at: 0.67, action: 'llm_response', ...section(5), details: { iteration: 1, has_tool_calls: false, has_final_answer: true, response: `Final Answer:\n\n${SECTIONS[5]}` } },
  { at: 0.70, action: 'section_complete', ...section(5), details: { content: SECTIONS[5] } },

  // Section 6 — Recommendation (get_entities_by_type)
  { at: 0.75, action: 'section_start', ...section(6), details: {} },
  { at: 0.78, action: 'tool_call', ...section(6), details: { tool_name: 'get_entities_by_type', parameters: { entity_type: 'Organization' } } },
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
