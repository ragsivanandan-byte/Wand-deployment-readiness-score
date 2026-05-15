import { CAPABILITIES, CaseResult, THRESHOLDS, Verdict } from "./types";

export interface ThresholdsT {
  task_success_rate: number;
  hallucination_rate_max: number;
  instruction_follow_min: number;
  p95_latency_ms_max: number;
  cost_per_run_usd_max: number;
}

export interface Aggregate {
  n: number;
  task_success_rate: number;
  hallucination_rate: number;
  instruction_follow_mean: number;
  p95_latency_ms: number;
  mean_cost_usd: number;
  total_cost_usd: number;
}

export function aggregate(results: CaseResult[]): Aggregate {
  if (!results.length) {
    return {
      n: 0, task_success_rate: 0, hallucination_rate: 0,
      instruction_follow_mean: 0, p95_latency_ms: 0,
      mean_cost_usd: 0, total_cost_usd: 0,
    };
  }
  const n = results.length;
  const ts = results.reduce((s, r) => s + r.verdict.task_success, 0) / n;
  const hall = results.filter(r => r.verdict.hallucination_score >= 2).length / n;
  const instr = results.reduce((s, r) => s + r.verdict.instruction_following, 0) / n / 3;
  const latencies = results.map(r => r.response.latency_ms).sort((a, b) => a - b);
  const p95 = latencies[Math.max(0, Math.round(0.95 * (n - 1)))];
  const costs = results.map(r => r.total_cost_usd);
  const totalCost = costs.reduce((s, c) => s + c, 0);
  return {
    n,
    task_success_rate: ts,
    hallucination_rate: hall,
    instruction_follow_mean: instr,
    p95_latency_ms: p95,
    mean_cost_usd: totalCost / n,
    total_cost_usd: totalCost,
  };
}

export interface GateCheck {
  name: string;
  passed: boolean;
  value: string;
}

export function goNoGo(agg: Aggregate, thresholds: ThresholdsT = THRESHOLDS): { verdict: Verdict; checks: GateCheck[] } {
  const checks: GateCheck[] = [
    { name: `Task success rate ≥ ${(thresholds.task_success_rate * 100).toFixed(0)}%`,
      passed: agg.task_success_rate >= thresholds.task_success_rate,
      value: `${(agg.task_success_rate * 100).toFixed(0)}%` },
    { name: `Hallucination rate ≤ ${(thresholds.hallucination_rate_max * 100).toFixed(0)}%`,
      passed: agg.hallucination_rate <= thresholds.hallucination_rate_max,
      value: `${(agg.hallucination_rate * 100).toFixed(0)}%` },
    { name: `Instruction following ≥ ${thresholds.instruction_follow_min.toFixed(2)}`,
      passed: agg.instruction_follow_mean >= thresholds.instruction_follow_min,
      value: agg.instruction_follow_mean.toFixed(2) },
    { name: `p95 latency ≤ ${thresholds.p95_latency_ms_max.toLocaleString()} ms`,
      passed: agg.p95_latency_ms <= thresholds.p95_latency_ms_max,
      value: `${agg.p95_latency_ms.toLocaleString()} ms` },
    { name: `Mean cost ≤ $${thresholds.cost_per_run_usd_max.toFixed(2)}`,
      passed: agg.mean_cost_usd <= thresholds.cost_per_run_usd_max,
      value: `$${agg.mean_cost_usd.toFixed(4)}` },
  ];
  const verdict: Verdict = checks.every(c => c.passed) ? "GO" : "NO-GO";
  return { verdict, checks };
}

export interface HeatmapCell {
  axis: "task_success" | "hallucination" | "instruction" | "latency" | "cost";
  score: number | null;
  raw?: string;
}

export interface HeatmapRow {
  capability: string;
  n: number;
  cells: HeatmapCell[];
}

export function heatmap(results: CaseResult[], thresholds: ThresholdsT = THRESHOLDS): HeatmapRow[] {
  const byCap = new Map<string, CaseResult[]>();
  for (const r of results) {
    const arr = byCap.get(r.case.capability) ?? [];
    arr.push(r);
    byCap.set(r.case.capability, arr);
  }
  return CAPABILITIES.map(cap => {
    const rs = byCap.get(cap) ?? [];
    if (!rs.length) {
      return {
        capability: cap, n: 0,
        cells: (["task_success", "hallucination", "instruction", "latency", "cost"] as const).map(a => ({ axis: a, score: null })),
      };
    }
    const n = rs.length;
    const ts = rs.reduce((s, r) => s + r.verdict.task_success, 0) / n;
    const hallOk = rs.filter(r => r.verdict.hallucination_score < 2).length / n;
    const inst = rs.reduce((s, r) => s + r.verdict.instruction_following, 0) / n / 3;
    const lats = rs.map(r => r.response.latency_ms).sort((a, b) => a - b);
    const p95 = lats[Math.max(0, Math.round(0.95 * (n - 1)))];
    const latScore = Math.max(0, Math.min(1, 1 - (p95 - 2000) / (thresholds.p95_latency_ms_max * 2 - 2000)));
    const meanCost = rs.reduce((s, r) => s + r.total_cost_usd, 0) / n;
    const costScore = Math.max(0, Math.min(1, 1 - meanCost / (thresholds.cost_per_run_usd_max * 2)));
    return {
      capability: cap, n,
      cells: [
        { axis: "task_success", score: ts },
        { axis: "hallucination", score: hallOk },
        { axis: "instruction", score: inst },
        { axis: "latency", score: latScore, raw: `${p95.toLocaleString()} ms` },
        { axis: "cost", score: costScore, raw: `$${meanCost.toFixed(4)}` },
      ],
    };
  });
}

export function scoreColor(score: number | null): string {
  if (score === null) return "#1f2937";
  if (score >= 0.9) return "#10b981";
  if (score >= 0.75) return "#84cc16";
  if (score >= 0.55) return "#f59e0b";
  if (score >= 0.35) return "#f97316";
  return "#ef4444";
}

export function isFailure(r: CaseResult): boolean {
  const v = r.verdict;
  return v.task_success === 0 || v.hallucination_score >= 2 || v.instruction_following <= 1;
}
