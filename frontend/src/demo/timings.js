// Single tuning point for demo-mode job durations and simulated network
// latency. Adjust these to make the scripted demo feel faster/slower without
// touching any handler code.

export const GRAPH_BUILD_SECONDS = 15
export const PREPARE_SECONDS = 12
export const RUN_SECONDS = 30
export const REPORT_SECONDS = 25

export const AI_LATENCY_MS = [2000, 3000] // "AI is thinking" endpoints
export const READ_LATENCY_MS = [150, 400] // plain reads / polls
