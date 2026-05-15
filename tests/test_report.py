"""Tests for the aggregation and reporting logic."""
from __future__ import annotations

from harness.report import Aggregate, aggregate, failures, go_no_go, heatmap, regression


def _case(cid: str, capability: str, *, success: int = 1, halluc: int = 0,
          instr: int = 3, latency_ms: int = 1000, cost: float = 0.001) -> dict:
    return {
        "case": {
            "id": cid, "capability": capability, "category": "golden",
            "prompt": "p", "context": "c", "expected": "e",
            "must_contain": [], "must_not_contain": [],
        },
        "response": {
            "output": "ok", "latency_ms": latency_ms,
            "input_tokens": 100, "output_tokens": 50,
            "model": "claude-haiku-4-5", "trace": [
                {"step": "writer", "input_tokens": 100, "output_tokens": 50, "latency_ms": latency_ms},
            ],
            "cost_usd": cost / 2,
        },
        "verdict": {
            "task_success": success, "hallucination_score": halluc,
            "instruction_following": instr, "rationale": "r",
            "input_tokens": 50, "output_tokens": 20, "latency_ms": 200,
        },
        "total_cost_usd": cost,
    }


def test_aggregate_basic():
    results = [
        _case("a", "writer", success=1, halluc=0, instr=3, latency_ms=1000, cost=0.001),
        _case("b", "writer", success=1, halluc=0, instr=3, latency_ms=2000, cost=0.002),
        _case("c", "writer", success=0, halluc=2, instr=1, latency_ms=8000, cost=0.003),
        _case("d", "writer", success=1, halluc=0, instr=2, latency_ms=1500, cost=0.001),
    ]
    agg = aggregate(results)
    assert agg.n == 4
    assert agg.task_success_rate == 0.75
    assert agg.hallucination_rate == 0.25
    # instruction following: (3+3+1+2)/4 / 3 = 9/12 = 0.75
    assert abs(agg.instruction_follow_mean - 0.75) < 0.01


def test_aggregate_empty():
    agg = aggregate([])
    assert agg.n == 0
    assert agg.task_success_rate == 0


def test_go_no_go_borderline():
    # Exactly at thresholds = pass.
    agg = Aggregate(n=10, task_success_rate=0.80, hallucination_rate=0.10,
                    instruction_follow_mean=0.85, p95_latency_ms=8000,
                    mean_cost_usd=0.05, total_cost_usd=0.5)
    verdict, _ = go_no_go(agg)
    assert verdict == "GO"


def test_heatmap_shape():
    results = [_case("a", "writer"), _case("b", "researcher")]
    grid = heatmap(results)
    # Every shipped capability gets a row, even with zero cases.
    rows = {r["capability"]: r for r in grid}
    assert {"researcher", "analyst", "writer", "reviewer", "orchestrator"} <= set(rows)
    assert rows["writer"]["n"] == 1
    assert rows["analyst"]["n"] == 0
    # Cells exist for every axis.
    assert {c["axis"] for c in rows["writer"]["cells"]} == {
        "task_success", "hallucination", "instruction", "latency", "cost"
    }


def test_failures_filtering():
    results = [
        _case("ok", "writer", success=1, halluc=0, instr=3),
        _case("missed_task", "writer", success=0, halluc=0, instr=3),
        _case("hallucinated", "writer", success=1, halluc=2, instr=3),
        _case("formatting", "writer", success=1, halluc=0, instr=1),
    ]
    fails = failures(results)
    fail_ids = {f["id"] for f in fails}
    assert "ok" not in fail_ids
    assert {"missed_task", "hallucinated", "formatting"} == fail_ids


def test_regression_diff():
    current = [
        _case("a", "writer", success=1, halluc=0),
        _case("b", "writer", success=0, halluc=2),
        _case("c", "writer", success=1, halluc=0),
    ]
    previous = [
        _case("a", "writer", success=0, halluc=2),  # was failing → now passes (win)
        _case("b", "writer", success=1, halluc=0),  # was passing → now fails (loss)
        _case("c", "writer", success=1, halluc=0),  # unchanged
    ]
    diff = regression(current, previous)
    assert diff["available"] is True
    assert diff["wins"] == ["a"]
    assert diff["losses"] == ["b"]
    assert diff["unchanged_count"] == 1


def test_regression_no_previous():
    diff = regression([_case("a", "writer")], None)
    assert diff == {"available": False}
