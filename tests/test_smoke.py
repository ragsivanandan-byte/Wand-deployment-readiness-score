"""Smoke tests — mock mode end-to-end, fast, no API key needed."""
from __future__ import annotations

import json
import os
import shutil

from harness.config import REPORTS_DIR, Settings
from harness.report import aggregate, go_no_go, render
from harness.runner import load_test_cases, run_suite


def test_load_test_cases():
    cases = load_test_cases()
    assert len(cases) >= 30, f"expected ≥30 cases, got {len(cases)}"
    capabilities = {c.capability for c in cases}
    assert capabilities >= {"researcher", "analyst", "writer", "reviewer", "orchestrator"}
    categories = {c.category for c in cases}
    assert categories == {"golden", "adversarial", "edge_cases"}


def test_end_to_end_mock(tmp_path, monkeypatch):
    monkeypatch.setenv("HARNESS_MODE", "mock")
    # Quarantine report writes so we don't trash the committed reports dir.
    monkeypatch.setattr("harness.runner.REPORTS_DIR", tmp_path)
    monkeypatch.setattr("harness.report.REPORTS_DIR", tmp_path)
    settings = Settings.from_env(run_id="test-smoke")
    payload = run_suite(settings)
    assert len(payload["results"]) >= 30
    out = render(payload)
    html = out.read_text()
    assert "<title>" in html and "Wand Deployment Readiness" in html
    assert "GO" in html or "NO-GO" in html


def test_thresholds_logic():
    """The GO/NO-GO function must fail closed if any check fails."""
    from harness.report import Aggregate
    bad = Aggregate(n=10, task_success_rate=0.7, hallucination_rate=0.0,
                    instruction_follow_mean=1.0, p95_latency_ms=100, mean_cost_usd=0.001,
                    total_cost_usd=0.01)
    verdict, _ = go_no_go(bad)
    assert verdict == "NO-GO"
    good = Aggregate(n=10, task_success_rate=0.95, hallucination_rate=0.05,
                     instruction_follow_mean=0.92, p95_latency_ms=3000, mean_cost_usd=0.01,
                     total_cost_usd=0.1)
    verdict, _ = go_no_go(good)
    assert verdict == "GO"
