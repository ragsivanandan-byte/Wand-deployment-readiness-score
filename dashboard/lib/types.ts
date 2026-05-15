export type Verdict = "GO" | "NO-GO";

export interface Case {
  id: string;
  capability: string;
  category: string;
  prompt: string;
  context: string;
  expected: string;
  must_contain: string[];
  must_not_contain: string[];
}

export interface TraceStep {
  step: string;
  latency_ms: number;
  input_tokens: number;
  output_tokens: number;
  output_preview: string;
}

export interface Response {
  output: string;
  latency_ms: number;
  input_tokens: number;
  output_tokens: number;
  model: string;
  trace: TraceStep[];
  cost_usd: number;
}

export interface VerdictRow {
  task_success: number;
  hallucination_score: number;
  instruction_following: number;
  rationale: string;
  input_tokens: number;
  output_tokens: number;
  latency_ms: number;
}

export interface CaseResult {
  case: Case;
  response: Response;
  verdict: VerdictRow;
  total_cost_usd: number;
}

export interface RunPayload {
  run_id: string;
  generated_at: string;
  mode: string;
  target_model: string;
  judge_model: string;
  rubric_version: string;
  results: CaseResult[];
}

export const CAPABILITIES = ["researcher", "analyst", "writer", "reviewer", "orchestrator"] as const;
export const CATEGORIES = ["golden", "adversarial", "edge_cases"] as const;

export const THRESHOLDS = {
  task_success_rate: 0.80,
  hallucination_rate_max: 0.10,
  instruction_follow_min: 0.85,
  p95_latency_ms_max: 8000,
  cost_per_run_usd_max: 0.05,
} as const;
