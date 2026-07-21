// Demo fixture: the fully-generated dual-platform simulation configuration
// for the Y Combinator / AGI-era scenario. Returned by
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
    { agent_id: 0, entity_name: 'Elena Voss', entity_type: 'Partner', stance: 'support',
      active_hours: [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18], posts_per_hour: 0.6, comments_per_hour: 1.5,
      response_delay_min: 15, response_delay_max: 90, activity_level: 0.55, sentiment_bias: 0.3, influence_weight: 2.5 },
    { agent_id: 1, entity_name: 'Marcus Oyelaran', entity_type: 'Partner', stance: 'support',
      active_hours: [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19], posts_per_hour: 0.4, comments_per_hour: 2,
      response_delay_min: 10, response_delay_max: 60, activity_level: 0.6, sentiment_bias: 0.2, influence_weight: 2.2 },
    { agent_id: 2, entity_name: 'Priya Shenoy', entity_type: 'Partner', stance: 'support',
      active_hours: [6, 7, 8, 9, 10, 17, 18, 19, 20], posts_per_hour: 0.8, comments_per_hour: 2.5,
      response_delay_min: 5, response_delay_max: 45, activity_level: 0.65, sentiment_bias: 0.4, influence_weight: 1.6 },
    { agent_id: 3, entity_name: 'Kai Nakamura', entity_type: 'Founder', stance: 'support',
      active_hours: [6, 7, 8, 9, 10, 17, 18, 19, 20], posts_per_hour: 0.8, comments_per_hour: 2.5,
      response_delay_min: 5, response_delay_max: 45, activity_level: 0.6, sentiment_bias: 0.4, influence_weight: 1.5 },
    { agent_id: 4, entity_name: 'Sofia Marek', entity_type: 'Founder', stance: 'neutral',
      active_hours: [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20], posts_per_hour: 1.2, comments_per_hour: 3,
      response_delay_min: 5, response_delay_max: 30, activity_level: 0.7, sentiment_bias: 0.0, influence_weight: 1.8 },
    { agent_id: 5, entity_name: 'Dr. Wen Zhao', entity_type: 'ResearchLab', stance: 'support',
      active_hours: [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18], posts_per_hour: 0.6, comments_per_hour: 2,
      response_delay_min: 10, response_delay_max: 60, activity_level: 0.55, sentiment_bias: 0.3, influence_weight: 1.4 },
    { agent_id: 6, entity_name: 'Tomas Lindqvist', entity_type: 'Founder', stance: 'support',
      active_hours: [6, 7, 8, 17, 18, 19, 20, 21], posts_per_hour: 1.5, comments_per_hour: 4,
      response_delay_min: 5, response_delay_max: 30, activity_level: 0.75, sentiment_bias: 0.1, influence_weight: 1.9 },
    { agent_id: 7, entity_name: 'Rachel Adeyemi', entity_type: 'InvestorLP', stance: 'oppose',
      active_hours: [18, 19, 20, 21, 22, 23, 0, 1], posts_per_hour: 2, comments_per_hour: 5,
      response_delay_min: 2, response_delay_max: 20, activity_level: 0.85, sentiment_bias: -0.6, influence_weight: 1.1 },
    { agent_id: 8, entity_name: 'Dev Kapoor', entity_type: 'AcceleratorProgram', stance: 'oppose',
      active_hours: [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18], posts_per_hour: 0.7, comments_per_hour: 2,
      response_delay_min: 15, response_delay_max: 60, activity_level: 0.5, sentiment_bias: -0.3, influence_weight: 1.3 },
    { agent_id: 9, entity_name: 'Maya Chen', entity_type: 'MediaOutlet', stance: 'neutral',
      active_hours: [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18], posts_per_hour: 0.5, comments_per_hour: 1.5,
      response_delay_min: 20, response_delay_max: 90, activity_level: 0.45, sentiment_bias: 0.5, influence_weight: 1.7 },
    { agent_id: 10, entity_name: 'Jonah Price', entity_type: 'Founder', stance: 'support',
      active_hours: [9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19], posts_per_hour: 0.6, comments_per_hour: 2,
      response_delay_min: 15, response_delay_max: 60, activity_level: 0.5, sentiment_bias: 0.0, influence_weight: 1.2 },
    { agent_id: 11, entity_name: 'Aisha Rahman', entity_type: 'ResearchLab', stance: 'oppose',
      active_hours: [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22], posts_per_hour: 2.5, comments_per_hour: 3,
      response_delay_min: 5, response_delay_max: 30, activity_level: 0.8, sentiment_bias: 0.0, influence_weight: 2.0 },
    { agent_id: 12, entity_name: 'Leo Martins', entity_type: 'Founder', stance: 'support',
      active_hours: [17, 18, 19, 20, 21, 22], posts_per_hour: 1.8, comments_per_hour: 5,
      response_delay_min: 5, response_delay_max: 25, activity_level: 0.7, sentiment_bias: -0.1, influence_weight: 0.9 },
    { agent_id: 13, entity_name: 'Hana Sato', entity_type: 'EnterpriseBuyer', stance: 'neutral',
      active_hours: [12, 13, 18, 19, 20, 21], posts_per_hour: 1.2, comments_per_hour: 3.5,
      response_delay_min: 5, response_delay_max: 30, activity_level: 0.6, sentiment_bias: -0.2, influence_weight: 0.7 },
    { agent_id: 14, entity_name: 'Gabe Torres', entity_type: 'Founder', stance: 'oppose',
      active_hours: [10, 11, 12, 19, 20, 21, 22], posts_per_hour: 1.5, comments_per_hour: 4,
      response_delay_min: 5, response_delay_max: 30, activity_level: 0.65, sentiment_bias: -0.3, influence_weight: 0.8 },
    { agent_id: 15, entity_name: 'Nadia Petrova', entity_type: 'InvestorLP', stance: 'neutral',
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
    narrative_direction: "Y Combinator is weighing a reversible AGI-Native Track pilot after The Batch Report leaked an internal memo describing plans to admit far more agent-augmented solo and tiny-team founders, weighting agent leverage over headcount. Expect an early shock wave and #AGInativeYC to trend, a split between agent-native founders celebrating and traditional teams growing anxious, LP concern over return profiles, and a public clash between Helios Research's 3.2x telemetry study and Cascade AI Lab's conflicting 1.4x post-batch audit -- tempered by cautious convergence toward a staged, reversible track with real oversight guardrails.",
    hot_topics: [
      '#AGInativeYC',
      'agent-leverage ratio',
      'solo founder $2.1M ARR',
      'batch model overhaul',
      'LP letter leak',
      'Winter 2027 applications'
    ],
    initial_posts: [
      { poster_type: 'media', poster_agent_id: 9,
        content: "Scoop: Y Combinator is drafting an AGI-Native Track that would admit far more solo, agent-augmented founders and weight agent leverage over headcount. Internal memo obtained by The Batch Report. #AGInativeYC" },
      { poster_type: 'partner', poster_agent_id: 0,
        content: "To be clear: we're proposing a staged, reversible pilot -- 60 companies, two batch cycles, real guardrails -- not blowing up the batch model overnight." },
      { poster_type: 'founder', poster_agent_id: 3,
        content: "40 agents, $2.1M ARR, team of one. If YC's rubric doesn't have room for this, the rubric is wrong." },
      { poster_type: 'lp', poster_agent_id: 7,
        content: "Before anyone gets excited: admitting more tiny agent-augmented teams changes the return profile our endowment is underwriting. We need to see the numbers, not the vibes." },
      { poster_type: 'accelerator', poster_agent_id: 8,
        content: "Cute pilot. We already run our whole track this way. By the time YC finishes evaluating 60 companies over two batches, we'll have graduated three cohorts." }
    ]
  },

  generation_reasoning: "Weighted partner and agent-native founder agents toward support since the staged pilot with guardrails is the direction the evidence and cast lean | Gave the rival accelerator partner and skeptical LP agents an oppose stance to dramatize the caution-vs-speed tension | Kept researchers split (Wen Zhao support, Aisha Rahman oppose) to mirror the deliberate 3.2x-vs-1.4x evidence conflict"
}
