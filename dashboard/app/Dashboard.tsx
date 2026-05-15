"use client";

import { useMemo, useState } from "react";
import { aggregate, goNoGo, heatmap, isFailure, scoreColor } from "@/lib/metrics";
import { CaseResult, CATEGORIES, RunPayload, THRESHOLDS as DEFAULT_THRESHOLDS } from "@/lib/types";

interface Thresholds {
  task_success_rate: number;
  hallucination_rate_max: number;
  instruction_follow_min: number;
  p95_latency_ms_max: number;
  cost_per_run_usd_max: number;
}

const THRESHOLDS: Thresholds = { ...DEFAULT_THRESHOLDS };

const AXIS_LABELS: Record<string, string> = {
  task_success: "Task success",
  hallucination: "Factuality",
  instruction: "Instruction",
  latency: "Latency p95",
  cost: "Cost",
};

export default function Dashboard({ data }: { data: RunPayload }) {
  const [category, setCategory] = useState<string>("all");
  const [capability, setCapability] = useState<string>("all");
  const [showFailuresOnly, setShowFailuresOnly] = useState(false);
  const [thresholds, setThresholds] = useState<Thresholds>(THRESHOLDS);
  const [selected, setSelected] = useState<CaseResult | null>(null);

  const filtered = useMemo(() => {
    return data.results.filter(r => {
      if (category !== "all" && r.case.category !== category) return false;
      if (capability !== "all" && r.case.capability !== capability) return false;
      if (showFailuresOnly && !isFailure(r)) return false;
      return true;
    });
  }, [data, category, capability, showFailuresOnly]);

  const agg = useMemo(() => aggregate(filtered), [filtered]);
  const { verdict, checks } = useMemo(() => goNoGo(agg, thresholds), [agg, thresholds]);
  const grid = useMemo(() => heatmap(filtered, thresholds), [filtered, thresholds]);
  const failures = useMemo(() => filtered.filter(isFailure), [filtered]);

  return (
    <main className="max-w-7xl mx-auto px-6 py-8 pb-24">
      <Header data={data} n={agg.n} totalCases={data.results.length} />
      <FilterBar
        category={category} setCategory={setCategory}
        capability={capability} setCapability={setCapability}
        showFailuresOnly={showFailuresOnly} setShowFailuresOnly={setShowFailuresOnly}
        thresholds={thresholds} setThresholds={setThresholds}
        defaultThresholds={THRESHOLDS}
      />
      <VerdictBanner verdict={verdict} />
      <Section title="Headline metrics">
        <MetricTiles agg={agg} thresholds={thresholds} />
      </Section>
      <Section title="Readiness gates">
        <GatesTable checks={checks} />
      </Section>
      <Section title="Capability × axis heatmap">
        <Heatmap grid={grid} />
      </Section>
      <Section title={`Failing cases (${failures.length})`}>
        <FailuresList failures={failures} onSelect={setSelected} />
      </Section>
      <Footer data={data} />
      {selected && <CaseDrawer result={selected} onClose={() => setSelected(null)} />}
    </main>
  );
}

function Header({ data, n, totalCases }: { data: RunPayload; n: number; totalCases: number }) {
  return (
    <header className="flex justify-between items-start gap-6 border-b border-line pb-6 mb-8 flex-wrap">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Wand Deployment Readiness Harness</h1>
        <div className="text-muted text-sm">
          Buy-side earnings workflow · showing {n} of {totalCases} cases · {data.generated_at.slice(0, 19)}Z
        </div>
      </div>
      <div className="text-xs text-muted text-right space-y-0.5">
        <div>run <code className="bg-panel px-1 py-0.5 rounded text-ink">{data.run_id}</code></div>
        <div>mode <code className="bg-panel px-1 py-0.5 rounded text-ink">{data.mode}</code> · target <code className="bg-panel px-1 py-0.5 rounded text-ink">{data.target_model}</code></div>
        <div>judge <code className="bg-panel px-1 py-0.5 rounded text-ink">{data.judge_model}</code> · rubric <code className="bg-panel px-1 py-0.5 rounded text-ink">{data.rubric_version}</code></div>
      </div>
    </header>
  );
}

interface FilterBarProps {
  category: string;
  setCategory: (v: string) => void;
  capability: string;
  setCapability: (v: string) => void;
  showFailuresOnly: boolean;
  setShowFailuresOnly: (v: boolean) => void;
  thresholds: Thresholds;
  setThresholds: (t: Thresholds) => void;
  defaultThresholds: Thresholds;
}

function FilterBar({
  category, setCategory, capability, setCapability,
  showFailuresOnly, setShowFailuresOnly,
  thresholds, setThresholds, defaultThresholds,
}: FilterBarProps) {
  const dirty = JSON.stringify(thresholds) !== JSON.stringify(defaultThresholds);
  return (
    <div className="mb-6 flex flex-wrap gap-3 items-center text-sm">
      <Select label="Category" value={category} setValue={setCategory}
        options={[{ v: "all", l: "All" }, ...CATEGORIES.map(c => ({ v: c, l: c }))]} />
      <Select label="Capability" value={capability} setValue={setCapability}
        options={[{ v: "all", l: "All" },
          ...["researcher", "analyst", "writer", "reviewer", "orchestrator"].map(c => ({ v: c, l: c }))]} />
      <label className="flex items-center gap-2 cursor-pointer select-none">
        <input type="checkbox" checked={showFailuresOnly}
          onChange={e => setShowFailuresOnly(e.target.checked)}
          className="accent-accent" />
        <span>Failures only</span>
      </label>
      <details className="ml-auto">
        <summary className="cursor-pointer text-accent hover:text-ink">
          Thresholds {dirty && <span className="text-amber-400">· modified</span>}
        </summary>
        <div className="mt-3 p-4 bg-panel border border-line rounded-lg w-full md:w-[420px] absolute md:static right-6 z-10 space-y-2">
          <ThrSlider label="Task success ≥" suffix="%"
            value={thresholds.task_success_rate * 100} min={0} max={100} step={1}
            onChange={v => setThresholds({ ...thresholds, task_success_rate: v / 100 })} />
          <ThrSlider label="Hallucination ≤" suffix="%"
            value={thresholds.hallucination_rate_max * 100} min={0} max={50} step={1}
            onChange={v => setThresholds({ ...thresholds, hallucination_rate_max: v / 100 })} />
          <ThrSlider label="Instruction ≥" suffix=""
            value={thresholds.instruction_follow_min} min={0} max={1} step={0.01}
            onChange={v => setThresholds({ ...thresholds, instruction_follow_min: v })} />
          <ThrSlider label="p95 latency ≤" suffix=" ms"
            value={thresholds.p95_latency_ms_max} min={1000} max={20000} step={500}
            onChange={v => setThresholds({ ...thresholds, p95_latency_ms_max: v })} />
          <ThrSlider label="Cost/run ≤" suffix=" USD"
            value={thresholds.cost_per_run_usd_max} min={0} max={0.5} step={0.005}
            onChange={v => setThresholds({ ...thresholds, cost_per_run_usd_max: v })} />
          <button onClick={() => setThresholds(defaultThresholds)}
            className="text-xs text-muted hover:text-ink underline">reset</button>
        </div>
      </details>
    </div>
  );
}

function Select({ label, value, setValue, options }: {
  label: string;
  value: string;
  setValue: (v: string) => void;
  options: { v: string; l: string }[];
}) {
  return (
    <label className="flex items-center gap-2">
      <span className="text-muted">{label}:</span>
      <select value={value} onChange={e => setValue(e.target.value)}
        className="bg-panel border border-line rounded px-2 py-1 text-ink">
        {options.map(o => <option key={o.v} value={o.v}>{o.l}</option>)}
      </select>
    </label>
  );
}

function ThrSlider({ label, suffix, value, min, max, step, onChange }: {
  label: string;
  suffix: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
}) {
  return (
    <label className="flex items-center gap-3">
      <span className="text-muted w-32 text-xs">{label}</span>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={e => onChange(Number(e.target.value))}
        className="flex-1 accent-accent" />
      <span className="text-xs text-ink w-20 text-right">
        {step < 1 ? value.toFixed(2) : Math.round(value)}{suffix}
      </span>
    </label>
  );
}

function VerdictBanner({ verdict }: { verdict: string }) {
  const isGo = verdict === "GO";
  return (
    <div className={`flex items-center gap-6 p-7 rounded-xl mb-8 border ${
      isGo
        ? "bg-gradient-to-br from-emerald-950 to-emerald-900 border-emerald-700"
        : "bg-gradient-to-br from-red-950 to-red-900 border-red-700"
    }`}>
      <div className="text-5xl font-bold tracking-wider">{verdict}</div>
      <div>
        <div className="text-[11px] uppercase tracking-widest text-white/70 mb-1">Deployment verdict</div>
        <div className="text-sm">
          {isGo
            ? "All five readiness gates are within threshold. Recommend production rollout with monitoring on hallucination rate and p95 latency."
            : "One or more readiness gates are out of threshold — see the table below. Recommend remediation before go-live."}
        </div>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-10">
      <h2 className="text-[11px] uppercase tracking-widest text-muted font-semibold mb-3">{title}</h2>
      {children}
    </section>
  );
}

function MetricTiles({ agg, thresholds }: { agg: ReturnType<typeof aggregate>; thresholds: Thresholds }) {
  const tiles = [
    { k: "Task success", v: `${(agg.task_success_rate * 100).toFixed(0)}%`,
      pass: agg.task_success_rate >= thresholds.task_success_rate,
      thr: `≥ ${(thresholds.task_success_rate * 100).toFixed(0)}%` },
    { k: "Hallucination", v: `${(agg.hallucination_rate * 100).toFixed(0)}%`,
      pass: agg.hallucination_rate <= thresholds.hallucination_rate_max,
      thr: `≤ ${(thresholds.hallucination_rate_max * 100).toFixed(0)}%` },
    { k: "Instruction follow", v: agg.instruction_follow_mean.toFixed(2),
      pass: agg.instruction_follow_mean >= thresholds.instruction_follow_min,
      thr: `≥ ${thresholds.instruction_follow_min.toFixed(2)}` },
    { k: "p95 latency", v: `${agg.p95_latency_ms.toLocaleString()} ms`,
      pass: agg.p95_latency_ms <= thresholds.p95_latency_ms_max,
      thr: `≤ ${thresholds.p95_latency_ms_max.toLocaleString()} ms` },
    { k: "Cost / run", v: `$${agg.mean_cost_usd.toFixed(4)}`,
      pass: agg.mean_cost_usd <= thresholds.cost_per_run_usd_max,
      thr: `≤ $${thresholds.cost_per_run_usd_max.toFixed(2)} · total $${agg.total_cost_usd.toFixed(4)}` },
  ];
  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
      {tiles.map(t => (
        <div key={t.k} className="bg-panel border border-line rounded-lg p-4">
          <div className="text-[11px] uppercase tracking-wider text-muted">{t.k}</div>
          <div className={`text-2xl font-semibold mt-2 ${t.pass ? "text-emerald-400" : "text-red-400"}`}>{t.v}</div>
          <div className="text-[11px] text-muted mt-1">threshold {t.thr}</div>
        </div>
      ))}
    </div>
  );
}

function GatesTable({ checks }: { checks: ReturnType<typeof goNoGo>["checks"] }) {
  return (
    <div className="bg-panel border border-line rounded-lg overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-panel2 text-muted text-[11px] uppercase tracking-wider">
          <tr><th className="px-4 py-3 text-left">Gate</th><th className="px-4 py-3 text-left">Measured</th><th className="px-4 py-3 text-left">Result</th></tr>
        </thead>
        <tbody>
          {checks.map(c => (
            <tr key={c.name} className="border-t border-line">
              <td className="px-4 py-2.5">{c.name}</td>
              <td className="px-4 py-2.5">{c.value}</td>
              <td className={`px-4 py-2.5 font-semibold ${c.passed ? "text-emerald-400" : "text-red-400"}`}>
                {c.passed ? "PASS" : "FAIL"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Heatmap({ grid }: { grid: ReturnType<typeof heatmap> }) {
  return (
    <div className="bg-panel border border-line rounded-lg p-4 overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="text-muted text-xs">
            <th className="text-left py-2 w-44"></th>
            {Object.keys(AXIS_LABELS).map(a => <th key={a} className="font-medium px-2">{AXIS_LABELS[a]}</th>)}
          </tr>
        </thead>
        <tbody>
          {grid.map(row => (
            <tr key={row.capability}>
              <th className="text-left py-2 capitalize text-ink font-medium">
                {row.capability} <span className="text-muted text-xs font-normal">({row.n})</span>
              </th>
              {row.cells.map((c, i) => (
                <td key={i} className="px-1 py-1">
                  {c.score === null ? (
                    <div className="h-12 rounded flex items-center justify-center bg-gray-700 text-muted">—</div>
                  ) : (
                    <div className="h-12 rounded flex flex-col items-center justify-center text-sm font-semibold text-[#0b1020]"
                      style={{ background: scoreColor(c.score) }}>
                      <span>{(c.score * 100).toFixed(0)}%</span>
                      {c.raw && <span className="text-[10px] font-normal opacity-90">{c.raw}</span>}
                    </div>
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FailuresList({ failures, onSelect }: { failures: CaseResult[]; onSelect: (r: CaseResult) => void }) {
  if (!failures.length) return <p className="text-muted text-sm">No failures in this filter.</p>;
  return (
    <div className="grid gap-3">
      {failures.map(r => (
        <button key={r.case.id} onClick={() => onSelect(r)}
          className="text-left bg-panel border border-line border-l-4 border-l-red-500 rounded-lg p-4 hover:bg-panel2 transition">
          <div className="flex justify-between items-baseline gap-3 mb-2">
            <div>
              <span className="font-mono text-xs text-accent">{r.case.id}</span>
              <span className="capitalize text-sm ml-2">{r.case.capability}</span>
              <span className="text-muted text-xs ml-2">{r.case.category}</span>
            </div>
            <div className="text-[11px] text-muted space-x-3">
              <span>success: <strong className="text-ink">{r.verdict.task_success}</strong></span>
              <span>halluc: <strong className="text-ink">{r.verdict.hallucination_score}/3</strong></span>
              <span>instr: <strong className="text-ink">{r.verdict.instruction_following}/3</strong></span>
            </div>
          </div>
          <div className="text-muted text-sm mb-1"><strong className="text-ink">Prompt:</strong> {r.case.prompt}</div>
          <div className="text-rose-300 text-sm"><strong className="text-ink">Judge:</strong> {r.verdict.rationale}</div>
          <div className="text-xs text-muted mt-2">Click for full trace →</div>
        </button>
      ))}
    </div>
  );
}

function CaseDrawer({ result, onClose }: { result: CaseResult; onClose: () => void }) {
  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex justify-end" onClick={onClose}>
      <aside className="bg-panel border-l border-line w-full max-w-2xl h-full overflow-y-auto p-6"
        onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-start mb-4">
          <div>
            <div className="font-mono text-sm text-accent">{result.case.id}</div>
            <div className="text-muted text-xs mt-1">{result.case.capability} · {result.case.category}</div>
          </div>
          <button onClick={onClose} className="text-muted hover:text-ink text-xl leading-none">×</button>
        </div>

        <DrawerSection title="Prompt">{result.case.prompt}</DrawerSection>
        <DrawerSection title="Source context"><pre className="whitespace-pre-wrap text-xs">{result.case.context}</pre></DrawerSection>
        <DrawerSection title="Expected">{result.case.expected}</DrawerSection>

        <h3 className="text-[11px] uppercase tracking-widest text-muted font-semibold mt-6 mb-2">Per-step trace</h3>
        <div className="space-y-2 mb-6">
          {result.response.trace.map((s, i) => (
            <div key={i} className="bg-panel2 border border-line rounded p-3 text-xs">
              <div className="flex justify-between mb-1.5">
                <span className="capitalize font-medium text-ink">{s.step}</span>
                <span className="text-muted">{s.latency_ms} ms · {s.input_tokens}→{s.output_tokens} tok</span>
              </div>
              <pre className="whitespace-pre-wrap text-muted text-[11px]">{s.output_preview}</pre>
            </div>
          ))}
        </div>

        <DrawerSection title="Final output"><pre className="whitespace-pre-wrap text-xs">{result.response.output}</pre></DrawerSection>

        <h3 className="text-[11px] uppercase tracking-widest text-muted font-semibold mt-6 mb-2">Judge verdict</h3>
        <div className="bg-panel2 border border-line rounded p-3 text-xs space-y-1">
          <div>task_success: <strong>{result.verdict.task_success}/1</strong></div>
          <div>hallucination: <strong>{result.verdict.hallucination_score}/3</strong></div>
          <div>instruction_following: <strong>{result.verdict.instruction_following}/3</strong></div>
          <div className="text-rose-300 mt-2">{result.verdict.rationale}</div>
        </div>
      </aside>
    </div>
  );
}

function DrawerSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <h3 className="text-[11px] uppercase tracking-widest text-muted font-semibold mb-1.5">{title}</h3>
      <div className="text-sm text-ink">{children}</div>
    </div>
  );
}

function Footer({ data }: { data: RunPayload }) {
  return (
    <footer className="mt-16 pt-6 border-t border-line text-muted text-xs leading-relaxed">
      Generated by the Wand Deployment Readiness Harness.
      Rubric hash <code className="bg-panel px-1 rounded text-ink">{data.rubric_version}</code> —
      change the judge prompt and this hash moves, signalling that results are no longer
      comparable to prior runs. Target <code className="bg-panel px-1 rounded text-ink">{data.target_model}</code>,
      judge <code className="bg-panel px-1 rounded text-ink">{data.judge_model}</code>,
      mode <code className="bg-panel px-1 rounded text-ink">{data.mode}</code>.
    </footer>
  );
}
