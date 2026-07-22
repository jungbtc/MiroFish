// 3-choice answer sets for the decision workspace's internal questions.
// The demo state machine advances the same way whichever option is picked;
// the choices exist to show HOW the workflow consumes internal facts.
//
// Array order matters: findAnswerOptions tests each set's `match` regex in
// array order and returns the options for the first one that matches. The
// four real internal-question strings (src/demo/fixtures/v2/state0.js
// through state3.js, internal_questions) share overlapping vocabulary — the
// budget question also contains the word "downside", and the downside/
// regret question also contains the word "outcome" — so 'budget' and
// 'downside' are ordered ahead of 'outcome' below to make sure each real
// question routes to its intended set. See tests/demo-answer-options.test.mjs
// for the routing proof against the actual fixture questions.
const ANSWER_OPTION_SETS = [
  {
    id: 'constraints',
    match: /legal|policy|procurement|contractual|constraint/i,
    options: [
      {
        title: 'No blocker — pilot expressly permitted',
        text: "There is no non-negotiable legal or policy blocker. YC's equal-access admissions policy requires the AGI-Native Track to remain open to every applicant profile, and two LP side letters require 60-day notice before any permanent batch-model change, but a time-limited reversible track pilot is expressly permitted.",
        submitted_by: 'Marcus Oyelaran (Managing Partner)',
        confidence: 0.9
      },
      {
        title: '90-day consultation required first',
        text: 'Two LP side letters block any change without 90-day consultation, so only a fully reversible pilot inside the current batch envelope is permissible.',
        submitted_by: 'General Counsel',
        confidence: 0.8
      },
      {
        title: 'Accreditation notice required before pilot',
        text: 'Internal policy allows the pilot, but requires the accreditation partner to receive 30-day advance notice before any differentiated curriculum track launches, plus a guaranteed opt-out path for admitted founders who prefer the classic track.',
        submitted_by: 'Deputy General Counsel',
        confidence: 0.75
      }
    ]
  },
  {
    id: 'budget',
    match: /budget|payback|approved|capacity/i,
    options: [
      {
        title: '$25M binding tranche + named owner',
        text: 'The partnership approved a binding $25 million pilot allocation from the standard fund for the first AGI-Native Track cohort, with a dedicated staff of 6 partners and program managers covering both pilot cohorts through 2027-06-30. Elena Voss (Group Partner) is the named full-time track owner accountable for the pilot, and Marcus Oyelaran (Managing Partner) is the approver for expansion gates.',
        submitted_by: 'Marcus Oyelaran (Managing Partner)',
        confidence: 0.9
      },
      {
        title: '$8M discretionary only, no dedicated staff',
        text: "Only $8M of discretionary budget is available this cycle, and no dedicated staff has been approved; the pilot would have to run on partners' existing bandwidth through the first cohort.",
        submitted_by: 'CFO Office',
        confidence: 0.8
      },
      {
        title: '$40M expansion ask pending board sign-off',
        text: 'Finance has modeled a $40 million two-cohort ask that would fund a larger 90-company pilot and two additional program managers, but the incremental $15 million above the base tranche has not yet cleared board approval.',
        submitted_by: 'Program Finance Office',
        confidence: 0.75
      }
    ]
  },
  {
    id: 'downside',
    match: /regret|downside|exposure|tolerance/i,
    options: [
      {
        title: 'Brand + LP alignment set the limit',
        text: 'Leadership would regret the decision if it damaged the YC brand or LP alignment: the approved downside limit is the $25 million pilot exposure, an incident rate no higher than 1.5 times baseline, and zero breaches of the equal-access policy. Roughly 40% of expected pilot value depends on avoiding those outcomes.',
        submitted_by: 'Marcus Oyelaran (Managing Partner)',
        confidence: 0.9
      },
      {
        title: 'Founder outcomes are the real downside',
        text: 'Leadership would regret the decision most if admitted agent-native founders underperformed classic-track peers on follow-on funding; up to 2 times baseline incident rate is an acceptable trade as long as founder outcomes hold.',
        submitted_by: 'Elena Voss (Group Partner, Track Lead)',
        confidence: 0.8
      },
      {
        title: 'Any LP defection is zero-tolerance',
        text: "The only downside leadership will not tolerate is a single LP exercising its side-letter exit rights; incident rate and brand exposure are secondary concerns as long as no LP walks away from the fund.",
        submitted_by: 'Rachel Adeyemi (LP, Crestline University Endowment)',
        confidence: 0.75
      }
    ]
  },
  {
    id: 'outcome',
    match: /measurable|outcome|minimum acceptable|success/i,
    options: [
      {
        title: '1.6× velocity, ≤1.2× incidents, 60 slots',
        text: "The pilot must show AGI-native track companies reaching at least 1.6 times the classic batch's median week-12 release velocity with an incident rate no higher than 1.2 times baseline, and all 60 pilot slots filled by qualified applicants; minimum acceptable outcome is quality parity with the classic batch.",
        submitted_by: 'Elena Voss (Group Partner, Track Lead)',
        confidence: 0.9
      },
      {
        title: '2× velocity bar, zero-incident tolerance',
        text: "The pilot must show AGI-native track companies reaching at least 2 times the classic batch's median week-12 release velocity with zero critical incidents tolerated; anything less triggers an automatic wind-down before cohort 2.",
        submitted_by: 'Priya Shenoy (Visiting Partner)',
        confidence: 0.8
      },
      {
        title: 'Parity on outcomes, not velocity',
        text: 'Success is defined by founder-reported satisfaction and follow-on funding rate reaching parity with the classic batch within two cohorts; raw release-velocity multiples are treated as a secondary signal, not the bar.',
        submitted_by: 'Rachel Adeyemi (LP, Crestline University Endowment)',
        confidence: 0.75
      }
    ]
  },
  {
    id: 'generic',
    match: /.*/,
    options: [
      {
        title: 'No additional constraint identified',
        text: 'No further non-public constraint, budget limit, or risk threshold beyond what has already been confirmed applies to this question.',
        submitted_by: 'Elena Voss (Group Partner, Track Lead)',
        confidence: 0.7
      },
      {
        title: 'Owner has not yet weighed in',
        text: 'The relevant internal owner has not yet provided a definitive answer; the working assumption is to proceed with the current default until clarified.',
        submitted_by: 'Marcus Oyelaran (Managing Partner)',
        confidence: 0.65
      },
      {
        title: 'Treat as open pending review',
        text: 'This question remains open pending partnership review; no binding internal fact should be assumed until it is formally answered.',
        submitted_by: 'Priya Shenoy (Visiting Partner)',
        confidence: 0.6
      }
    ]
  }
]

export const findAnswerOptions = question =>
  (ANSWER_OPTION_SETS.find(set => set.match.test(String(question || ''))) || ANSWER_OPTION_SETS[ANSWER_OPTION_SETS.length - 1]).options

export default ANSWER_OPTION_SETS
