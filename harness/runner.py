"""Load test cases, run them, persist raw results."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from harness.adapters import FinanceWorkflowAdapter, TargetResponse, TestCase
from harness.config import REPORTS_DIR, TEST_CASES_DIR, Settings
from harness.judge import JudgeVerdict, judge, rubric_hash


@dataclass
class CaseResult:
    case: TestCase
    response: TargetResponse
    verdict: JudgeVerdict

    def total_cost_usd(self) -> float:
        # Cost = target agent cost + judge cost. Judge runs on Sonnet.
        from harness.config import PRICING
        judge_cost = (self.verdict.input_tokens / 1_000_000) * PRICING["claude-sonnet-4-6"]["input"] + (
            self.verdict.output_tokens / 1_000_000
        ) * PRICING["claude-sonnet-4-6"]["output"]
        return self.response.cost_usd() + judge_cost


def load_test_cases() -> list[TestCase]:
    cases: list[TestCase] = []
    for path in sorted(TEST_CASES_DIR.glob("*.yaml")):
        with path.open() as f:
            data = yaml.safe_load(f) or {}
        for raw in data.get("cases", []):
            cases.append(TestCase(
                id=raw["id"],
                capability=raw["capability"],
                category=raw.get("category", path.stem),
                prompt=raw["prompt"],
                context=raw["context"],
                expected=raw["expected"],
                must_contain=raw.get("must_contain", []),
                must_not_contain=raw.get("must_not_contain", []),
            ))
    if not cases:
        raise RuntimeError(f"No test cases found under {TEST_CASES_DIR}")
    return cases


def run_suite(
    settings: Settings,
    *,
    category: str | None = None,
    capability: str | None = None,
    limit: int | None = None,
) -> dict:
    adapter = FinanceWorkflowAdapter(settings)
    cases = load_test_cases()
    if category:
        cases = [c for c in cases if c.category == category]
    if capability:
        cases = [c for c in cases if c.capability == capability]
    if limit:
        cases = cases[:limit]
    if not cases:
        raise RuntimeError("No cases matched the supplied filters")
    results: list[CaseResult] = []
    for i, case in enumerate(cases, 1):
        print(f"  [{i:>2}/{len(cases)}] {case.id} ({case.capability})")
        resp = adapter.run(case)
        verdict = judge(case, resp.output, settings=settings, client=adapter._client)
        results.append(CaseResult(case=case, response=resp, verdict=verdict))

    payload = {
        "run_id": settings.run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": settings.mode,
        "target_model": settings.target_model,
        "judge_model": settings.judge_model,
        "rubric_version": rubric_hash(),
        "results": [_serialise(r) for r in results],
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = REPORTS_DIR / f"{settings.run_id}.json"
    raw_path.write_text(json.dumps(payload, indent=2, default=str))
    print(f"  → raw results: {raw_path.relative_to(REPORTS_DIR.parent)}")
    return payload


def _serialise(r: CaseResult) -> dict:
    d = {
        "case": asdict(r.case),
        "response": {
            **{k: v for k, v in asdict(r.response).items() if k != "trace"},
            "trace": r.response.trace,
            "cost_usd": r.response.cost_usd(),
        },
        "verdict": asdict(r.verdict),
        "total_cost_usd": r.total_cost_usd(),
    }
    return d


def previous_run_path(current_run_id: str) -> Path | None:
    """Find the most recent run JSON that isn't the current one."""
    candidates = sorted(REPORTS_DIR.glob("*.json"))
    candidates = [p for p in candidates if p.stem != current_run_id]
    return candidates[-1] if candidates else None
