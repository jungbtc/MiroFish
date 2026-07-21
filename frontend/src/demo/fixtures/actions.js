// Phase 3 (simulation run) fixture: the 16-agent cast for the Northstar
// Appliances scenario and the ~80 scripted social actions they take across
// 10 simulated rounds (both platforms). Consumed by
// src/demo/handlers/phase345.js to derive /run-status, /run-status/detail,
// and by src/demo/fixtures/chat.js for interview personas.
//
// Narrative arc:
//   Rounds 1-3  — announcement shock (liquidity runway disclosed)
//   Rounds 4-6  — union/supplier reactions, Meridian lender letter leaks
//   Rounds 7-10 — pilot-vs-full debate settles around the staged pilot
//
// IMPORTANT: this cast (id/name/username) is index-aligned with
// src/demo/fixtures/profiles.js (the phase12 fixture Step2EnvSetup.vue and
// Step5Interaction.vue's agent picker read from). Keep the two in sync —
// `name` here mirrors profiles.js's `username` field (display name) and
// `username` here mirrors profiles.js's `name` field (handle/slug), so a
// persona picked in Step5 by agent_id matches the voice used in the Step3
// timeline and the Step4/5 interview replies.

import { ts } from './scenario.js'

export const AGENTS = [
  { id: 0, name: 'Dana Whitfield', username: 'dana_whitfield_ceo', role: 'Chief Executive Officer, Northstar Appliances' },
  { id: 1, name: 'Marcus Lee', username: 'marcus_lee_cfo', role: 'Chief Financial Officer, Northstar Appliances' },
  { id: 2, name: 'Priya Nandakumar', username: 'priya_toledo_ops', role: 'Plant Manager, Toledo Assembly Plant' },
  { id: 3, name: 'Robert Hayes', username: 'robert_macon_ops', role: 'Plant Manager, Macon Assembly Plant' },
  { id: 4, name: 'Grace Liu', username: 'grace_liu_comms', role: 'VP Corporate Communications, Northstar Appliances' },
  { id: 5, name: 'Elena Cho', username: 'elena_cho_supply', role: 'VP Supply Chain, Northstar Appliances' },
  { id: 6, name: 'Denise Ruiz', username: 'denise_ruiz_uaw', role: 'Chief Shop Steward, UAW Local 1180' },
  { id: 7, name: 'Jordan Ellis', username: 'jordan_ellis_eng', role: 'Former Process Engineer, Toledo Plant (laid off)' },
  { id: 8, name: 'Tom Reyes', username: 'tom_reyes_karlin', role: 'Chief Financial Officer, Karlin Components (supplier)' },
  { id: 9, name: 'Sarah Kwan', username: 'sarah_kwan_meridian', role: 'Senior Credit Analyst, Meridian Lending Group' },
  { id: 10, name: 'Alicia Brooks', username: 'alicia_brooks_homeplex', role: 'VP Merchandising, HomePlex Retail Corp' },
  { id: 11, name: 'Sam Okafor', username: 'sam_okafor_reports', role: 'Industry Journalist, Midwest Business Journal' },
  { id: 12, name: 'Northstar Loyalists Community', username: 'northstar_loyalists_mod', role: 'Community Moderator, Northstar Loyalists' },
  { id: 13, name: 'Renee Castillo', username: 'budget_conscious_renee', role: 'Consumer Advocate, Price-Sensitive Households' },
  { id: 14, name: 'Marcus Ito', username: 'fixit_marcus', role: 'Independent Appliance Repair Technician' },
  { id: 15, name: 'Toledo Community Advocates', username: 'toledo_civic_voice', role: 'Civic Organizer, Toledo Community Advocates' }
]

const byId = id => AGENTS[id]

// Each row: [agentId, platform, action_type, action_args]. Rounds are
// implicit — every 8 rows completes a round (4 twitter + 4 reddit).
// Twitter carries the executive/institutional voices (CEO, CFO, comms,
// supply chain, supplier, lender, retailer, journalist); Reddit carries the
// plant, labor, and community voices — mirroring profiles.js's entity_type
// groupings (Executive/Supplier/Lender/RetailPartner/MediaOutlet vs.
// LaborUnion/CustomerSegment).
const RAW = [
  // Round 1 — announcement shock
  [0, 'twitter', 'CREATE_POST', {
    content: "This morning we told employees that Northstar is evaluating two paths forward: an immediate companywide restructuring, or a staged, reversible pilot at a single site first. No final decision has been made. We owe our people clarity and we'll move responsibly."
  }],
  [11, 'twitter', 'CREATE_COMMENT', {
    content: 'Does "staged pilot" mean Toledo and Macon stay open for now, or is a single-site closure still on the table under that option?',
    post_id: 'post_2001',
    post_author_name: 'Dana Whitfield',
    post_content: "This morning we told employees that Northstar is evaluating two paths forward: an immediate companywide restructuring, or a staged, reversible pilot at a single site first."
  }],
  [4, 'twitter', 'CREATE_POST', {
    content: "We know today's announcement raised more questions than it answered. An FAQ for employees, retail partners, and press goes out tomorrow morning. In the meantime, no site has been designated for anything yet."
  }],
  [10, 'twitter', 'LIKE_POST', {
    post_author_name: 'Dana Whitfield',
    post_content: "This morning we told employees that Northstar is evaluating two paths forward: an immediate companywide restructuring, or a staged, reversible pilot at a single site first."
  }],
  [2, 'reddit', 'CREATE_POST', {
    content: 'Toledo floor heard about the restructuring announcement about an hour before the press release went out. Morale is rattled after two rounds of layoff rumors already this year. We build good appliances here.'
  }],
  [3, 'reddit', 'CREATE_COMMENT', {
    content: "Macon's hearing the same thing today. We've held onto our most skilled line workers through worse; hoping leadership remembers that before deciding anything.",
    post_id: 'post_2005',
    post_author_name: 'Priya Nandakumar',
    post_content: 'Toledo floor heard about the restructuring announcement about an hour before the press release went out.'
  }],
  [6, 'reddit', 'CREATE_POST', {
    content: "UAW Local 1180 is aware of Northstar's announcement. Our position going in: any pilot needs a firm sunset date, and full consultation rights before any permanent closure. We'll be at the table starting tomorrow."
  }],
  [13, 'reddit', 'UPVOTE_POST', {
    post_author_name: 'Denise Ruiz',
    post_content: "UAW Local 1180 is aware of Northstar's announcement. Our position going in: any pilot needs a firm sunset date, and full consultation rights before any permanent closure."
  }],

  // Round 2 — liquidity runway disclosed
  [1, 'twitter', 'CREATE_POST', {
    content: "To be direct with everyone asking: Northstar has roughly 11 weeks of liquidity runway at current burn. That's the real reason we're moving now, not next quarter. We're weighing options that protect jobs and cash at the same time."
  }],
  [9, 'twitter', 'QUOTE_POST', {
    quote_content: 'Encouraging that a CFO is naming the runway number this early — most companies wait until it leaks.',
    original_content: "To be direct with everyone asking: Northstar has roughly 11 weeks of liquidity runway at current burn.",
    original_author_name: 'Marcus Lee'
  }],
  [11, 'twitter', 'SEARCH_POSTS', { query: 'Northstar Appliances 11 weeks runway' }],
  [8, 'twitter', 'CREATE_COMMENT', {
    content: '11 weeks is tight. From where we sit, the real constraint is whether Northstar can keep approvals moving fast enough that our own numbers don\'t slip too.',
    post_id: 'post_2009',
    post_author_name: 'Marcus Lee',
    post_content: 'To be direct with everyone asking: Northstar has roughly 11 weeks of liquidity runway at current burn.'
  }],
  [7, 'reddit', 'CREATE_POST', {
    content: "Watched this exact script play out when I was let go in the last cost round. \"Evaluating options\" usually means the decision's already made. Hope Northstar communicates more clearly with the floor this time."
  }],
  [15, 'reddit', 'CREATE_COMMENT', {
    content: "We're organizing a public comment session in Toledo this week regardless of which way this goes. Workers deserve a say before any closure decision, not after.",
    post_id: 'post_2013',
    post_author_name: 'Jordan Ellis',
    post_content: 'Watched this exact script play out when I was let go in the last cost round.'
  }],
  [14, 'reddit', 'CREATE_POST', {
    content: 'Longtime member of the Appliance Repair Community Forum here. Selfishly I just want parts availability to keep working no matter what Northstar decides internally.'
  }],
  [12, 'reddit', 'CREATE_COMMENT', {
    content: "Moderating the Loyalists community, we're already getting warranty and service-continuity questions flooding in. Members want a straight answer, not corporate language.",
    post_id: 'post_2015',
    post_author_name: 'Marcus Ito',
    post_content: 'Longtime member of the Appliance Repair Community Forum here. Selfishly I just want parts availability to keep working.'
  }],

  // Round 3 — benchmark vs supplier survey numbers surface
  [0, 'twitter', 'CREATE_POST', {
    content: "One more data point behind our thinking: staged, reversible programs at comparable manufacturers have cut burn by about 18% over 90 days. We're testing whether that holds here before committing to anything irreversible."
  }],
  [11, 'twitter', 'CREATE_COMMENT', {
    content: 'Our own reporting on the supplier survey put the realistic number closer to 6%, not 18%. Which benchmark is Northstar actually planning around?',
    post_id: 'post_2017',
    post_author_name: 'Dana Whitfield',
    post_content: 'One more data point behind our thinking: staged, reversible programs at comparable manufacturers have cut burn by about 18% over 90 days.'
  }],
  [8, 'twitter', 'QUOTE_POST', {
    quote_content: "6% is closer to what we've modeled from our side too. An 18% burn cut assumes a level of cooperation and fast approvals we haven't seen committed to in writing yet.",
    original_content: 'Our own reporting on the supplier survey put the realistic number closer to 6%, not 18%.',
    original_author_name: 'Sam Okafor'
  }],
  [5, 'twitter', 'CREATE_COMMENT', {
    content: "Fair concern — we're working directly with Karlin on payment-term protection so approvals don't become the bottleneck you're describing.",
    post_id: 'post_2019',
    post_author_name: 'Tom Reyes',
    post_content: "6% is closer to what we've modeled from our side too. An 18% burn cut assumes a level of cooperation and fast approvals we haven't seen committed to in writing yet."
  }],
  [6, 'reddit', 'CREATE_POST', {
    content: 'Reminder to members: our position requires a firm sunset date on any pilot and full consultation before permanent closures. That\'s non-negotiable regardless of which benchmark leadership ends up citing.'
  }],
  [2, 'reddit', 'UPVOTE_POST', {
    post_author_name: 'Denise Ruiz',
    post_content: 'Reminder to members: our position requires a firm sunset date on any pilot and full consultation before permanent closures.'
  }],
  [7, 'reddit', 'CREATE_COMMENT', {
    content: "Glad someone's holding the line on consultation. That step got skipped entirely when I was laid off, and it made everything worse.",
    post_id: 'post_2023',
    post_author_name: 'Denise Ruiz',
    post_content: 'Reminder to members: our position requires a firm sunset date on any pilot and full consultation before permanent closures.'
  }],
  [13, 'reddit', 'CREATE_POST', {
    content: "From the price-sensitive household side: whatever this costs, please don't pass all of it onto appliance prices. We're watching this as closely as anyone."
  }],

  // Round 4 — union/supplier reactions intensify, lender letter starts to leak
  [9, 'twitter', 'CREATE_POST', {
    content: 'Speaking only for myself, not officially for Meridian: a reversible pilot backed by weekly liquidity reporting and supplier payment protection is a very different risk profile than an unstructured full restructuring.'
  }],
  [11, 'twitter', 'CREATE_COMMENT', {
    content: 'Are you confirming Meridian would actually finance a pilot under those terms, or speaking hypothetically?',
    post_id: 'post_2025',
    post_author_name: 'Sarah Kwan',
    post_content: 'Speaking only for myself, not officially for Meridian: a reversible pilot backed by weekly liquidity reporting and supplier payment protection is a very different risk profile.'
  }],
  [1, 'twitter', 'SEARCH_POSTS', { query: 'Meridian Lending Northstar pilot terms' }],
  [10, 'twitter', 'LIKE_POST', {
    post_author_name: 'Sarah Kwan',
    post_content: 'Speaking only for myself, not officially for Meridian: a reversible pilot backed by weekly liquidity reporting and supplier payment protection is a very different risk profile.'
  }],
  [15, 'reddit', 'CREATE_POST', {
    content: 'Hearing secondhand that Meridian sent Northstar a letter about backing a pilot if they report liquidity weekly and protect supplier payments. If true, that changes our public-comment strategy completely.'
  }],
  [3, 'reddit', 'CREATE_COMMENT', {
    content: "Macon heard the same secondhand version. If the lender is actually offering that, the case for an immediate full restructuring gets a lot weaker.",
    post_id: 'post_2029',
    post_author_name: 'Toledo Community Advocates',
    post_content: 'Hearing secondhand that Meridian sent Northstar a letter about backing a pilot if they report liquidity weekly and protect supplier payments.'
  }],
  [6, 'reddit', 'FOLLOW', { target_user: 'sarah_kwan_meridian' }],
  [14, 'reddit', 'DOWNVOTE_POST', {
    post_content: 'Just shut the whole thing down now and stop dragging this out for three months.'
  }],

  // Round 5 — lender letter leak confirmed, debate escalates
  [0, 'twitter', 'CREATE_POST', {
    content: "Confirming: Meridian Lending Group has offered to back a staged, reversible pilot conditioned on weekly liquidity reporting and supplier payment protection. We're taking that seriously."
  }],
  [4, 'twitter', 'QUOTE_POST', {
    quote_content: "This is the detail our FAQ tomorrow will lead with. A lender-backed reversible pilot with real conditions is a very different story than an unstructured restructuring.",
    original_content: "Confirming: Meridian Lending Group has offered to back a staged, reversible pilot conditioned on weekly liquidity reporting and supplier payment protection.",
    original_author_name: 'Dana Whitfield'
  }],
  [8, 'twitter', 'CREATE_COMMENT', {
    content: "Karlin can commit to weekly reporting on our end if that's part of what Meridian is asking for. We'd rather help a pilot succeed than absorb a sudden full stop.",
    post_id: 'post_2033',
    post_author_name: 'Dana Whitfield',
    post_content: 'Confirming: Meridian Lending Group has offered to back a staged, reversible pilot conditioned on weekly liquidity reporting and supplier payment protection.'
  }],
  [11, 'twitter', 'REPOST', {
    original_author_name: 'Dana Whitfield',
    original_content: 'Confirming: Meridian Lending Group has offered to back a staged, reversible pilot conditioned on weekly liquidity reporting and supplier payment protection.'
  }],
  [6, 'reddit', 'CREATE_POST', {
    content: 'This lender letter is exactly the leverage our members need. A reversible pilot with a real financial backstop, plus a sunset date and consultation rights, is something UAW Local 1180 can actually engage with.'
  }],
  [2, 'reddit', 'UPVOTE_POST', {
    post_author_name: 'Denise Ruiz',
    post_content: 'This lender letter is exactly the leverage our members need. A reversible pilot with a real financial backstop, plus a sunset date and consultation rights.'
  }],
  [12, 'reddit', 'CREATE_COMMENT', {
    content: "As moderators, honestly relieved to hear there's a version of this where the plants stay running while they figure it out. Passing this along to the community.",
    post_id: 'post_2037',
    post_author_name: 'Denise Ruiz',
    post_content: 'This lender letter is exactly the leverage our members need.'
  }],
  [15, 'reddit', 'DO_NOTHING', {}],

  // Round 6 — reporting deadlines get concrete, plant-level counter-numbers
  [11, 'twitter', 'CREATE_POST', {
    content: "New reporting: Meridian's term sheet reportedly requires Northstar to hit weekly liquidity targets or the pilot financing gets pulled. That's a real deadline, not just a press-release commitment."
  }],
  [1, 'twitter', 'CREATE_COMMENT', {
    content: "That's an accurate read. The reporting cadence is strict by design — it's what makes the covenant work instead of triggering default.",
    post_id: 'post_2041',
    post_author_name: 'Sam Okafor',
    post_content: "New reporting: Meridian's term sheet reportedly requires Northstar to hit weekly liquidity targets or the pilot financing gets pulled."
  }],
  [10, 'twitter', 'LIKE_POST', {
    post_author_name: 'Sam Okafor',
    post_content: "New reporting: Meridian's term sheet reportedly requires Northstar to hit weekly liquidity targets or the pilot financing gets pulled."
  }],
  [5, 'twitter', 'SEARCH_POSTS', { query: 'supplier payment protection Northstar pilot' }],
  [3, 'reddit', 'CREATE_POST', {
    content: "Macon ran our own numbers against the 18% benchmark leadership cited. We land closer to 10-12% burn reduction realistically — still meaningfully better than the 6% floor Karlin's been citing."
  }],
  [2, 'reddit', 'UPVOTE_POST', {
    post_author_name: 'Robert Hayes',
    post_content: 'Macon ran our own numbers against the 18% benchmark leadership cited. We land closer to 10-12% burn reduction realistically.'
  }],
  [7, 'reddit', 'CREATE_COMMENT', {
    content: 'Realistic numbers like this are more useful than the press release framing. Wish someone had run this analysis before my old plant got the axe.',
    post_id: 'post_2045',
    post_author_name: 'Robert Hayes',
    post_content: 'Macon ran our own numbers against the 18% benchmark leadership cited.'
  }],
  [14, 'reddit', 'FOLLOW', { target_user: 'priya_toledo_ops' }],

  // Round 7 — Northstar confirms the staged pilot structure
  [0, 'twitter', 'CREATE_POST', {
    content: "Where we've landed after this week: a staged, reversible pilot at one facility first, with weekly liquidity reporting to Meridian and formal consultation with UAW Local 1180 before any closure decision. Full restructuring stays off the table unless the pilot fails its own targets."
  }],
  [9, 'twitter', 'CREATE_COMMENT', {
    content: "That structure matches what we'd need to see to keep credit access available. Weekly reporting starting immediately is the right call.",
    post_id: 'post_2049',
    post_author_name: 'Dana Whitfield',
    post_content: "Where we've landed after this week: a staged, reversible pilot at one facility first, with weekly liquidity reporting to Meridian."
  }],
  [4, 'twitter', 'QUOTE_POST', {
    quote_content: "This is what today's FAQ confirms in writing, for anyone who missed it here first.",
    original_content: "Where we've landed after this week: a staged, reversible pilot at one facility first, with weekly liquidity reporting to Meridian.",
    original_author_name: 'Dana Whitfield'
  }],
  [11, 'twitter', 'LIKE_POST', {
    post_author_name: 'Dana Whitfield',
    post_content: "Where we've landed after this week: a staged, reversible pilot at one facility first, with weekly liquidity reporting to Meridian."
  }],
  [6, 'reddit', 'CREATE_POST', {
    content: "UAW Local 1180 can support this pilot structure. Consultation before closures was our floor demand, and it's in writing now. We'll be watching the weekly numbers as closely as Meridian is."
  }],
  [2, 'reddit', 'UPVOTE_POST', {
    post_author_name: 'Denise Ruiz',
    post_content: "UAW Local 1180 can support this pilot structure. Consultation before closures was our floor demand, and it's in writing now."
  }],
  [15, 'reddit', 'CREATE_COMMENT', {
    content: "Cautiously relieved is the honest way to describe where our members are. We've seen a \"temporary\" pilot quietly become permanent before.",
    post_id: 'post_2053',
    post_author_name: 'Denise Ruiz',
    post_content: 'UAW Local 1180 can support this pilot structure. Consultation before closures was our floor demand.'
  }],
  [3, 'reddit', 'DO_NOTHING', {}],

  // Round 8 — supplier and retail partner sign-off
  [8, 'twitter', 'CREATE_POST', {
    content: "Karlin Components is on board with the pilot structure. Weekly reporting cuts both ways — it also gives us earlier visibility if Northstar's orders are going to shift, which is exactly the certainty we asked for."
  }],
  [10, 'twitter', 'CREATE_COMMENT', {
    content: "HomePlex's read is the same. A pilot with real reporting and a written supply-continuity plan is easier to plan shelf space around than an abrupt full restructuring would have been.",
    post_id: 'post_2057',
    post_author_name: 'Tom Reyes',
    post_content: 'Karlin Components is on board with the pilot structure. Weekly reporting cuts both ways.'
  }],
  [11, 'twitter', 'REPOST', {
    original_author_name: 'Tom Reyes',
    original_content: 'Karlin Components is on board with the pilot structure. Weekly reporting cuts both ways.'
  }],
  [5, 'twitter', 'LIKE_POST', {
    post_author_name: 'Tom Reyes',
    post_content: 'Karlin Components is on board with the pilot structure. Weekly reporting cuts both ways.'
  }],
  [13, 'reddit', 'CREATE_POST', {
    content: "As someone who's been worried about prices this whole time: glad this didn't end in a headline about plants closing overnight. Hoping the pilot numbers hold up so it never has to."
  }],
  [14, 'reddit', 'UPVOTE_POST', {
    post_author_name: 'Renee Castillo',
    post_content: "As someone who's been worried about prices this whole time: glad this didn't end in a headline about plants closing overnight."
  }],
  [7, 'reddit', 'CREATE_COMMENT', {
    content: 'Appreciate people outside the plants paying attention to this instead of just the price tag. Keeps leadership honest too.',
    post_id: 'post_2061',
    post_author_name: 'Renee Castillo',
    post_content: "As someone who's been worried about prices this whole time: glad this didn't end in a headline about plants closing overnight."
  }],
  [12, 'reddit', 'SEARCH_POSTS', { query: 'Northstar pilot weekly liquidity reporting results' }],

  // Round 9 — first pilot results, press follow-up
  [11, 'twitter', 'CREATE_POST', {
    content: 'Follow-up piece going out this week comparing what an immediate full restructuring would have cost Northstar in supplier and union goodwill versus the staged pilot they actually chose. Early read: the staged path was the only one with real optionality.'
  }],
  [1, 'twitter', 'QUOTE_POST', {
    quote_content: 'Appreciate the scrutiny — optionality was exactly the word the board kept coming back to.',
    original_content: 'Follow-up piece going out this week comparing what an immediate full restructuring would have cost Northstar in supplier and union goodwill.',
    original_author_name: 'Sam Okafor'
  }],
  [9, 'twitter', 'LIKE_POST', {
    post_author_name: 'Sam Okafor',
    post_content: 'Follow-up piece going out this week comparing what an immediate full restructuring would have cost Northstar in supplier and union goodwill.'
  }],
  [0, 'twitter', 'DO_NOTHING', {}],
  [6, 'reddit', 'CREATE_POST', {
    content: "First weekly liquidity report under the pilot came in on schedule and inside the target range Meridian set. Small milestone, but it's the kind UAW Local 1180 will keep tracking closely."
  }],
  [2, 'reddit', 'UPVOTE_POST', {
    post_author_name: 'Denise Ruiz',
    post_content: 'First weekly liquidity report under the pilot came in on schedule and inside the target range Meridian set.'
  }],
  [3, 'reddit', 'CREATE_COMMENT', {
    content: "Macon's contribution to that report came in ahead of target, for what it's worth. Floor's taking this seriously.",
    post_id: 'post_2069',
    post_author_name: 'Denise Ruiz',
    post_content: 'First weekly liquidity report under the pilot came in on schedule and inside the target range Meridian set.'
  }],
  [15, 'reddit', 'FOLLOW', { target_user: 'denise_ruiz_uaw' }],

  // Round 10 — settling
  [0, 'twitter', 'CREATE_POST', {
    content: "One month into the staged pilot: liquidity reporting is on track, supplier payments are protected under the terms we agreed with Karlin and others, and UAW Local 1180 has been at the table every step. This is the version of \"restructuring\" I can stand behind."
  }],
  [8, 'twitter', 'CREATE_COMMENT', {
    content: "Karlin's view from the outside: predictable is underrated. This has been the calmest quarter we've had with Northstar in a year.",
    post_id: 'post_2073',
    post_author_name: 'Dana Whitfield',
    post_content: 'One month into the staged pilot: liquidity reporting is on track, supplier payments are protected under the terms we agreed with Karlin and others.'
  }],
  [4, 'twitter', 'QUOTE_POST', {
    quote_content: 'Worth remembering this could have gone the other way. The reversible option only worked because the lender terms and the union agreement both allowed it.',
    original_content: 'One month into the staged pilot: liquidity reporting is on track, supplier payments are protected under the terms we agreed with Karlin and others.',
    original_author_name: 'Dana Whitfield'
  }],
  [10, 'twitter', 'LIKE_POST', {
    post_author_name: 'Dana Whitfield',
    post_content: 'One month into the staged pilot: liquidity reporting is on track, supplier payments are protected under the terms we agreed with Karlin and others.'
  }],
  [6, 'reddit', 'CREATE_POST', {
    content: "Closing thought from UAW Local 1180: the consultation clause did what it was supposed to do here. Members kept their jobs during the period where a worse decision could have cost them."
  }],
  [2, 'reddit', 'UPVOTE_POST', {
    post_author_name: 'Denise Ruiz',
    post_content: 'Closing thought from UAW Local 1180: the consultation clause did what it was supposed to do here.'
  }],
  [7, 'reddit', 'CREATE_COMMENT', {
    content: 'Wish this had been the playbook when I was laid off. Glad it worked out differently for Toledo and Macon this time.',
    post_id: 'post_2077',
    post_author_name: 'Denise Ruiz',
    post_content: 'Closing thought from UAW Local 1180: the consultation clause did what it was supposed to do here.'
  }],
  [14, 'reddit', 'DO_NOTHING', {}]
]

const ACTIONS_PER_ROUND = 8

const actions = RAW.map((row, index) => {
  const [agentId, platform, actionType, actionArgs] = row
  const roundNum = Math.floor(index / ACTIONS_PER_ROUND) + 1
  const agent = byId(agentId)

  return {
    id: `act_${index + 1}`,
    timestamp: ts(index * 8),
    platform,
    agent_id: agentId,
    agent_name: agent.name,
    action_type: actionType,
    round_num: roundNum,
    action_args: actionArgs
  }
})

export default actions
