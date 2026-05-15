"""Centralised configuration: models, pricing, paths, mode."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEST_CASES_DIR = ROOT / "test_cases"
REPORTS_DIR = ROOT / "reports"
TEMPLATES_DIR = ROOT / "harness" / "templates"

TARGET_MODEL = "claude-haiku-4-5"
JUDGE_MODEL = "claude-sonnet-4-6"

# USD per 1M tokens. Sourced from Anthropic public pricing as of 2026-05.
# Kept in code (not a config file) so the report's cost numbers are reproducible
# from the commit alone.
PRICING = {
    "claude-haiku-4-5":   {"input": 1.00, "output": 5.00},
    "claude-sonnet-4-6":  {"input": 3.00, "output": 15.00},
}

# Pass/fail thresholds. Tweaking these moves the GO/NO-GO line — the report
# surfaces them so a reviewer can see what "ready" means.
THRESHOLDS = {
    "task_success_rate":      0.80,   # ≥ 80% of cases must succeed
    "hallucination_rate_max": 0.10,   # ≤ 10% may contain unsupported claims
    "instruction_follow_min": 0.85,   # mean ≥ 0.85 on a 0–1 scale
    "p95_latency_ms_max":     8000,   # p95 under 8s for an interactive UX
    "cost_per_run_usd_max":   0.05,   # average ≤ $0.05 per interaction
}

# How many parallel API calls we permit. Sequential is fine for a 30-case
# suite; if we grow we can lift this to ~5.
CONCURRENCY = 1


@dataclass(frozen=True)
class Settings:
    mode: str            # "mock" | "live"
    target_model: str
    judge_model: str
    api_key: str | None
    run_id: str

    @classmethod
    def from_env(cls, run_id: str) -> "Settings":
        mode = os.environ.get("HARNESS_MODE", "mock").lower()
        if mode not in {"mock", "live"}:
            raise ValueError(f"HARNESS_MODE must be 'mock' or 'live', got: {mode!r}")
        key = os.environ.get("ANTHROPIC_API_KEY")
        if mode == "live" and not key:
            raise RuntimeError(
                "HARNESS_MODE=live but ANTHROPIC_API_KEY is not set. "
                "Export the key or set HARNESS_MODE=mock."
            )
        return cls(
            mode=mode,
            target_model=TARGET_MODEL,
            judge_model=JUDGE_MODEL,
            api_key=key,
            run_id=run_id,
        )
