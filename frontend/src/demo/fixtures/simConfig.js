// Demo fixture: the fully-generated dual-platform simulation configuration
// for the Northstar Appliances scenario. Returned by
// GET /api/simulation/:id/config (SimulationRunView.vue:210 reads
// data.time_config.minutes_per_round directly) and embedded under `config`
// once GET /api/simulation/:id/config/realtime reports config_generated:true.
//
// agent_configs is index-aligned with src/demo/fixtures/profiles.js by
// agent_id (0..15): agent.entity_name mirrors profiles[i].username and
// agent.entity_type mirrors profiles[i].entity_type, so the two fixtures
// describe the same 16 personas from complementary angles.

export default {
  time_config: {
    total_simulation_hours: 20,
    minutes_per_round: 30,
    agents_per_hour_min: 3,
    agents_per_hour_max: 8,
    peak_hours: [19, 20, 21, 22],
    peak_activity_multiplier: 1.8,
    work_hours: [9, 10, 11, 12, 13, 14, 15, 16, 17],
    work_activity_multiplier: 1.2,
    morning_hours: [7, 8],
    morning_activity_multiplier: 0.9,
    off_peak_hours: [0, 1, 2, 3, 4, 5, 6, 23],
    off_peak_activity_multiplier: 0.4
  },

  agent_configs: [
    { agent_id: 0, entity_name: 'Dana Whitfield', entity_type: 'Executive', stance: 'support',
      active_hours: [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18], posts_per_hour: 0.6, comments_per_hour: 1.5,
      response_delay_min: 15, response_delay_max: 90, activity_level: 0.55, sentiment_bias: 0.3, influence_weight: 2.5 },
    { agent_id: 1, entity_name: 'Marcus Lee', entity_type: 'Executive', stance: 'support',
      active_hours: [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19], posts_per_hour: 0.4, comments_per_hour: 2,
      response_delay_min: 10, response_delay_max: 60, activity_level: 0.6, sentiment_bias: 0.2, influence_weight: 2.2 },
    { agent_id: 2, entity_name: 'Priya Nandakumar', entity_type: 'Executive', stance: 'support',
      active_hours: [6, 7, 8, 9, 10, 17, 18, 19, 20], posts_per_hour: 0.8, comments_per_hour: 2.5,
      response_delay_min: 5, response_delay_max: 45, activity_level: 0.65, sentiment_bias: 0.4, influence_weight: 1.6 },
    { agent_id: 3, entity_name: 'Robert Hayes', entity_type: 'Executive', stance: 'support',
      active_hours: [6, 7, 8, 9, 10, 17, 18, 19, 20], posts_per_hour: 0.8, comments_per_hour: 2.5,
      response_delay_min: 5, response_delay_max: 45, activity_level: 0.6, sentiment_bias: 0.4, influence_weight: 1.5 },
    { agent_id: 4, entity_name: 'Grace Liu', entity_type: 'Executive', stance: 'neutral',
      active_hours: [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20], posts_per_hour: 1.2, comments_per_hour: 3,
      response_delay_min: 5, response_delay_max: 30, activity_level: 0.7, sentiment_bias: 0.0, influence_weight: 1.8 },
    { agent_id: 5, entity_name: 'Elena Cho', entity_type: 'Executive', stance: 'support',
      active_hours: [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18], posts_per_hour: 0.6, comments_per_hour: 2,
      response_delay_min: 10, response_delay_max: 60, activity_level: 0.55, sentiment_bias: 0.3, influence_weight: 1.4 },
    { agent_id: 6, entity_name: 'Denise Ruiz', entity_type: 'LaborUnion', stance: 'support',
      active_hours: [6, 7, 8, 17, 18, 19, 20, 21], posts_per_hour: 1.5, comments_per_hour: 4,
      response_delay_min: 5, response_delay_max: 30, activity_level: 0.75, sentiment_bias: 0.1, influence_weight: 1.9 },
    { agent_id: 7, entity_name: 'Jordan Ellis', entity_type: 'LaborUnion', stance: 'oppose',
      active_hours: [18, 19, 20, 21, 22, 23, 0, 1], posts_per_hour: 2, comments_per_hour: 5,
      response_delay_min: 2, response_delay_max: 20, activity_level: 0.85, sentiment_bias: -0.6, influence_weight: 1.1 },
    { agent_id: 8, entity_name: 'Tom Reyes', entity_type: 'Supplier', stance: 'oppose',
      active_hours: [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18], posts_per_hour: 0.7, comments_per_hour: 2,
      response_delay_min: 15, response_delay_max: 60, activity_level: 0.5, sentiment_bias: -0.3, influence_weight: 1.3 },
    { agent_id: 9, entity_name: 'Sarah Kwan', entity_type: 'Lender', stance: 'support',
      active_hours: [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18], posts_per_hour: 0.5, comments_per_hour: 1.5,
      response_delay_min: 20, response_delay_max: 90, activity_level: 0.45, sentiment_bias: 0.5, influence_weight: 1.7 },
    { agent_id: 10, entity_name: 'Alicia Brooks', entity_type: 'RetailPartner', stance: 'neutral',
      active_hours: [9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19], posts_per_hour: 0.6, comments_per_hour: 2,
      response_delay_min: 15, response_delay_max: 60, activity_level: 0.5, sentiment_bias: 0.0, influence_weight: 1.2 },
    { agent_id: 11, entity_name: 'Sam Okafor', entity_type: 'MediaOutlet', stance: 'neutral',
      active_hours: [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22], posts_per_hour: 2.5, comments_per_hour: 3,
      response_delay_min: 5, response_delay_max: 30, activity_level: 0.8, sentiment_bias: 0.0, influence_weight: 2.0 },
    { agent_id: 12, entity_name: 'Northstar Loyalists Community', entity_type: 'CustomerSegment', stance: 'neutral',
      active_hours: [17, 18, 19, 20, 21, 22], posts_per_hour: 1.8, comments_per_hour: 5,
      response_delay_min: 5, response_delay_max: 25, activity_level: 0.7, sentiment_bias: -0.1, influence_weight: 0.9 },
    { agent_id: 13, entity_name: 'Renee Castillo', entity_type: 'CustomerSegment', stance: 'oppose',
      active_hours: [12, 13, 18, 19, 20, 21], posts_per_hour: 1.2, comments_per_hour: 3.5,
      response_delay_min: 5, response_delay_max: 30, activity_level: 0.6, sentiment_bias: -0.2, influence_weight: 0.7 },
    { agent_id: 14, entity_name: 'Marcus Ito', entity_type: 'CustomerSegment', stance: 'oppose',
      active_hours: [10, 11, 12, 19, 20, 21, 22], posts_per_hour: 1.5, comments_per_hour: 4,
      response_delay_min: 5, response_delay_max: 30, activity_level: 0.65, sentiment_bias: -0.3, influence_weight: 0.8 },
    { agent_id: 15, entity_name: 'Toledo Community Advocates', entity_type: 'CustomerSegment', stance: 'oppose',
      active_hours: [17, 18, 19, 20, 21], posts_per_hour: 1.0, comments_per_hour: 3,
      response_delay_min: 10, response_delay_max: 40, activity_level: 0.55, sentiment_bias: -0.4, influence_weight: 0.9 }
  ],

  twitter_config: {
    recency_weight: 0.4,
    popularity_weight: 0.35,
    relevance_weight: 0.25,
    viral_threshold: 0.7,
    echo_chamber_strength: 0.5
  },

  reddit_config: {
    recency_weight: 0.3,
    popularity_weight: 0.45,
    relevance_weight: 0.25,
    viral_threshold: 0.65,
    echo_chamber_strength: 0.4
  },

  event_config: {
    narrative_direction: "Northstar Appliances has roughly 11 weeks of operating cash left and must choose between an immediate company-wide restructuring and a staged, reversible pilot backed by Meridian Lending Group. Expect early skepticism from suppliers and laid-off workers citing the gap between the 18% industry benchmark and the 6% the supplier survey found, tempered by cautious support from lenders and plant leadership if weekly reporting and consultation commitments hold.",
    hot_topics: [
      '11-week liquidity runway',
      'Meridian covenant conditions',
      'staged pilot vs. immediate restructuring',
      'critical-supplier payment protection',
      'union consultation rights',
      '18% vs. 6% cash-burn benchmark gap'
    ],
    initial_posts: [
      { poster_type: 'company', poster_agent_id: 0,
        content: "Northstar Appliances is proposing a staged, reversible pilot program rather than an immediate company-wide restructuring. We're committed to weekly transparency with our lenders and workforce throughout this process." },
      { poster_type: 'lender', poster_agent_id: 9,
        content: "Meridian Lending Group will support Northstar's reversible pilot on the condition of weekly liquidity reporting and protected payment terms for critical suppliers." },
      { poster_type: 'union', poster_agent_id: 6,
        content: 'UAW Local 1180 will accept a time-limited pilot only if it comes with a firm sunset date and real consultation before any permanent plant decisions.' },
      { poster_type: 'supplier', poster_agent_id: 8,
        content: 'Industry benchmarks point to an 18% cash-burn reduction from staged programs, but our own survey found only 6% -- the difference comes down to delayed approvals and unclear ownership.' },
      { poster_type: 'media', poster_agent_id: 11,
        content: 'Northstar Appliances has roughly 11 weeks of operating cash left. The company now faces a choice: an immediate restructuring, or a reversible pilot backed by its lender group.' }
    ]
  },

  generation_reasoning: "Selected staged-pilot framing over blanket restructuring language to mirror Northstar's actual proposal | Weighted lender and union agents toward conditional support since both groups gain from a reversible pilot with clear terms | Gave supplier and laid-off-worker agents higher skepticism given the 18%-vs-6% cash-burn gap and past communication breakdowns"
}
