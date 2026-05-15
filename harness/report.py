"""Aggregate run results into a single HTML report.

Outputs:
  reports/<run_id>.html     (full report)
  reports/latest/index.html (for GitHub Pages)
  reports/latest/run.json   (machine-readable copy)
"""
from __future__ import annotations

import json
import shutil
import statistics
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from harness.config import REPORTS_DIR, TEMPLATES_DIR, THRESHOLDS
from harness.runner import previous_run_path

CAPABILITIES = ["researcher", "analyst", "writer", "reviewer", "orchestrator"]
AXES = ["task_success", "hallucination", "instruction", "latency", "cost"]
AXIS_LABELS = {
    "task_success": "Task success",
    "hallucination": "Factuality",
    "instruction": "Instruction following",
    "latency": "Latency p95",
    "cost": "Cost / interaction",
}


@dataclass
class Aggregate:
    n: int
    task_success_rate: float
    hallucination_rate: float
    instruction_follow_mean: float
    p95_latency_ms: int
    mean_cost_usd: float
    total_cost_usd: float


def aggregate(results: list[dict]) -> Aggregate:
    if not results:
        return Aggregate(0, 0, 0, 0, 0, 0, 0)
    n = len(results)
    ts = sum(r["verdict"]["task_success"] for r in results) / n
    hall = sum(1 for r in results if r["verdict"]["hallucination_score"] >= 2) / n
    inst = statistics.mean(r["verdict"]["instruction_following"] for r in results) / 3.0
    latencies = sorted(r["response"]["latency_ms"] for r in results)
    p95 = latencies[max(0, int(round(0.95 * (n - 1))))]
    costs = [r["total_cost_usd"] for r in results]
    return Aggregate(
        n=n,
        task_success_rate=ts,
        hallucination_rate=hall,
        instruction_follow_mean=inst,
        p95_latency_ms=p95,
        mean_cost_usd=statistics.mean(costs),
        total_cost_usd=sum(costs),
    )


def go_no_go(agg: Aggregate) -> tuple[str, list[dict]]:
    checks = [
        ("Task success rate ≥ 80%",
         agg.task_success_rate >= THRESHOLDS["task_success_rate"],
         f"{agg.task_success_rate:.0%}"),
        ("Hallucination rate ≤ 10%",
         agg.hallucination_rate <= THRESHOLDS["hallucination_rate_max"],
         f"{agg.hallucination_rate:.0%}"),
        ("Instruction following ≥ 0.85",
         agg.instruction_follow_mean >= THRESHOLDS["instruction_follow_min"],
         f"{agg.instruction_follow_mean:.2f}"),
        ("p95 latency ≤ 8,000 ms",
         agg.p95_latency_ms <= THRESHOLDS["p95_latency_ms_max"],
         f"{agg.p95_latency_ms} ms"),
        ("Mean cost per run ≤ $0.05",
         agg.mean_cost_usd <= THRESHOLDS["cost_per_run_usd_max"],
         f"${agg.mean_cost_usd:.4f}"),
    ]
    rows = [{"name": n, "passed": ok, "value": v} for n, ok, v in checks]
    verdict = "GO" if all(c[1] for c in checks) else "NO-GO"
    return verdict, rows


def heatmap(results: list[dict]) -> list[dict]:
    """Build a capability × axis matrix.

    Each cell is the share of cases for that capability that passed the axis.
    """
    by_cap: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        by_cap[r["case"]["capability"]].append(r)

    rows = []
    for cap in CAPABILITIES:
        rs = by_cap.get(cap, [])
        if not rs:
            rows.append({"capability": cap, "n": 0, "cells": [{"axis": a, "score": None} for a in AXES]})
            continue
        n = len(rs)
        cells = []
        ts = sum(r["verdict"]["task_success"] for r in rs) / n
        cells.append({"axis": "task_success", "score": ts})
        hall_ok = sum(1 for r in rs if r["verdict"]["hallucination_score"] < 2) / n
        cells.append({"axis": "hallucination", "score": hall_ok})
        inst = statistics.mean(r["verdict"]["instruction_following"] for r in rs) / 3.0
        cells.append({"axis": "instruction", "score": inst})
        lats = sorted(r["response"]["latency_ms"] for r in rs)
        p95 = lats[max(0, int(round(0.95 * (n - 1))))]
        # Latency "score" = 1 if comfortably under threshold, 0 if double it.
        lat_score = max(0.0, min(1.0, 1.0 - (p95 - 2000) / (THRESHOLDS["p95_latency_ms_max"] * 2 - 2000)))
        cells.append({"axis": "latency", "score": lat_score, "raw": f"{p95} ms"})
        mean_cost = statistics.mean(r["total_cost_usd"] for r in rs)
        cost_score = max(0.0, min(1.0, 1.0 - mean_cost / (THRESHOLDS["cost_per_run_usd_max"] * 2)))
        cells.append({"axis": "cost", "score": cost_score, "raw": f"${mean_cost:.4f}"})
        rows.append({"capability": cap, "n": n, "cells": cells})
    return rows


def regression(current: list[dict], previous: list[dict] | None) -> dict:
    if not previous:
        return {"available": False}
    prev_map = {r["case"]["id"]: r for r in previous}
    wins, losses, unchanged = [], [], []
    for r in current:
        cid = r["case"]["id"]
        p = prev_map.get(cid)
        if not p:
            continue
        cur_pass = r["verdict"]["task_success"] == 1 and r["verdict"]["hallucination_score"] < 2
        prev_pass = p["verdict"]["task_success"] == 1 and p["verdict"]["hallucination_score"] < 2
        if cur_pass and not prev_pass:
            wins.append(cid)
        elif prev_pass and not cur_pass:
            losses.append(cid)
        else:
            unchanged.append(cid)
    return {
        "available": True,
        "wins": wins,
        "losses": losses,
        "unchanged_count": len(unchanged),
    }


def failures(results: list[dict], limit: int = 8) -> list[dict]:
    fails = []
    for r in results:
        v = r["verdict"]
        if v["task_success"] == 0 or v["hallucination_score"] >= 2 or v["instruction_following"] <= 1:
            fails.append({
                "id": r["case"]["id"],
                "capability": r["case"]["capability"],
                "category": r["case"]["category"],
                "prompt": r["case"]["prompt"],
                "task_success": v["task_success"],
                "hallucination_score": v["hallucination_score"],
                "instruction_following": v["instruction_following"],
                "rationale": v["rationale"],
                "output_preview": r["response"]["output"][:600],
            })
    return fails[:limit]


def axis_breakdown(results: list[dict]) -> list[dict]:
    """Per-axis cost contribution. Useful to spot a runaway sub-agent."""
    step_costs: dict[str, float] = defaultdict(float)
    step_lat: dict[str, list[int]] = defaultdict(list)
    from harness.config import PRICING
    rate = PRICING["claude-haiku-4-5"]
    for r in results:
        for s in r["response"]["trace"]:
            step_costs[s["step"]] += (s["input_tokens"] / 1_000_000) * rate["input"] + (
                s["output_tokens"] / 1_000_000) * rate["output"]
            step_lat[s["step"]].append(s["latency_ms"])
    rows = []
    for step, cost in step_costs.items():
        lats = step_lat[step]
        rows.append({
            "step": step,
            "cost_usd": cost,
            "mean_latency_ms": int(statistics.mean(lats)) if lats else 0,
        })
    rows.sort(key=lambda r: -r["cost_usd"])
    return rows


def render(payload: dict, *, commit_sha: str | None = None) -> Path:
    results = payload["results"]
    agg = aggregate(results)
    verdict, checks = go_no_go(agg)
    grid = heatmap(results)

    prev_path = previous_run_path(payload["run_id"])
    prev = json.loads(prev_path.read_text())["results"] if prev_path else None
    reg = regression(results, prev)

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["pct"] = lambda x: f"{x:.0%}"
    env.filters["money"] = lambda x: f"${x:.4f}"
    env.filters["score_color"] = _score_color
    env.filters["score_label"] = _score_label
    tmpl = env.get_template("report.html.j2")

    html = tmpl.render(
        run_id=payload["run_id"],
        generated_at=payload["generated_at"],
        mode=payload["mode"],
        target_model=payload["target_model"],
        judge_model=payload["judge_model"],
        rubric_version=payload["rubric_version"],
        commit_sha=commit_sha,
        agg=agg,
        verdict=verdict,
        checks=checks,
        capabilities=CAPABILITIES,
        axes=AXES,
        axis_labels=AXIS_LABELS,
        grid=grid,
        regression=reg,
        failures=failures(results),
        axis_breakdown=axis_breakdown(results),
        thresholds=THRESHOLDS,
    )

    out = REPORTS_DIR / f"{payload['run_id']}.html"
    out.write_text(html)

    latest = REPORTS_DIR / "latest"
    latest.mkdir(parents=True, exist_ok=True)
    (latest / "index.html").write_text(html)
    shutil.copyfile(
        REPORTS_DIR / f"{payload['run_id']}.json",
        latest / "run.json",
    )
    return out


def _score_color(score: float | None) -> str:
    if score is None:
        return "#1f2937"
    # Red → amber → green gradient. We blend HSL for smooth bands.
    if score >= 0.9:
        return "#10b981"  # emerald-500
    if score >= 0.75:
        return "#84cc16"  # lime-500
    if score >= 0.55:
        return "#f59e0b"  # amber-500
    if score >= 0.35:
        return "#f97316"  # orange-500
    return "#ef4444"      # red-500


def _score_label(score: float | None) -> str:
    if score is None:
        return "—"
    return f"{score:.0%}"
